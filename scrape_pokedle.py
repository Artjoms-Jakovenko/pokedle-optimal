"""Scrape real Pokemon data from Pokedle using the daily game API."""

import json
import asyncio
from playwright.async_api import async_playwright


async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # Login
        print("Logging in...")
        login_resp = await context.request.post(
            "https://pokedle.com/api/authentication/login",
            data={
                "usernameOrEmail": "",  # fill in your email
                "password": "",  # fill in your password
            },
        )
        if login_resp.status != 200:
            print(f"Login failed: {login_resp.status} {await login_resp.text()}")
            await browser.close()
            return
        print("Logged in!")

        # Get pokemon list
        resp = await context.request.get(
            "https://pokedle.com/api/pokemon?language=english&generations=1"
        )
        pokemon_list = await resp.json()
        print(f"Found {len(pokemon_list)} Gen 1 pokemon")

        # Start daily classic (all gens so we can guess any pokemon)
        print("Starting daily classic game...")
        start_resp = await context.request.put(
            "https://pokedle.com/api/daily-games/Classic/start?language=English",
            data={"selectedGenerations": [1, 2, 3, 4, 5, 6, 7, 8, 9]},
        )
        start_data = await start_resp.json()
        session_id = start_data["id"]
        print(f"Session: {session_id}")

        # Track already guessed from existing session
        already_guessed = {g["pokemonNumber"] for g in start_data.get("guesses", [])}
        print(f"Already guessed: {len(already_guessed)} pokemon")

        all_data = []

        # Process existing guesses first
        for guess in start_data.get("guesses", []):
            entry = extract_entry(guess)
            if entry:
                all_data.append(entry)

        # Guess remaining Gen 1 pokemon
        for i, poke in enumerate(pokemon_list):
            if poke["number"] in already_guessed:
                print(f"  [{i+1}/{len(pokemon_list)}] {poke['name']}... already guessed")
                continue

            print(f"  [{i+1}/{len(pokemon_list)}] {poke['name']}...", end=" ", flush=True)
            try:
                resp = await context.request.put(
                    "https://pokedle.com/api/daily-games/Classic/guesses?language=English",
                    data={"sessionId": session_id, "pokemonNumber": poke["number"]},
                )
                result = await resp.json()

                if resp.status != 200:
                    print(f"HTTP {resp.status}")
                    all_data.append({"number": poke["number"], "name": poke["name"],
                                     "error": result})
                    continue

                # The response contains ALL guesses, get the latest one
                guesses = result.get("guesses", [])
                our_guess = next((g for g in guesses
                                  if g["pokemonNumber"] == poke["number"]), None)
                if our_guess:
                    entry = extract_entry(our_guess)
                    if entry:
                        all_data.append(entry)
                        print("OK")
                    else:
                        print("no fields")
                else:
                    print("guess not found in response")

                # If we accidentally won, note it
                if result.get("isWon"):
                    print(f"    ^ We found today's answer!")

                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"ERROR: {e}")
                all_data.append({"number": poke["number"], "name": poke["name"],
                                 "error": str(e)})

        # Save raw data
        with open("data/pokedle_raw.json", "w") as f:
            json.dump(all_data, f, indent=2)
        print(f"\nSaved {len(all_data)} entries to data/pokedle_raw.json")

        # Convert to clean format
        clean = []
        for entry in all_data:
            if "error" in entry:
                continue
            color_str = entry.get("color", "")
            habitat_str = entry.get("habitat", "")
            clean.append({
                "number": entry["number"],
                "name": entry["name"],
                "type1": entry.get("type1", ""),
                "type2": entry.get("type2", ""),
                "evolution_stage": int(entry.get("evolutionLevel", "0")),
                "is_fully_evolved": entry.get("isFullyEvolved", "") == "Yes",
                "color": [c.strip() for c in color_str.split(",")] if color_str else [],
                "habitat": [h.strip() for h in habitat_str.split(",")] if habitat_str else [],
                "generation": int(entry.get("generation", "0")),
            })

        with open("data/gen1_pokemon.json", "w") as f:
            json.dump(clean, f, indent=2)
        print(f"Saved {len(clean)} clean entries to data/gen1_pokemon.json")

        await browser.close()


def extract_entry(guess: dict) -> dict | None:
    result = guess.get("result", {})
    fields = result.get("fields", {})
    if not fields:
        return None

    entry = {
        "number": guess["pokemonNumber"],
        "name": guess["pokemonName"],
    }
    for key, field in fields.items():
        if "habitats" in field:
            entry[key] = field["habitats"]
        if "text" in field:
            entry[key] = field["text"]
    return entry


if __name__ == "__main__":
    asyncio.run(scrape())
