"""Scrape Gen 1 Pokémon data from PokeAPI for the Pokedle solver."""

import json
import time
import requests

BASE = "https://pokeapi.co/api/v2"
SESSION = requests.Session()


def get_json(url: str) -> dict:
    """Fetch JSON with retry logic."""
    for attempt in range(3):
        try:
            r = SESSION.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, requests.Timeout):
            if attempt < 2:
                time.sleep(1)
            else:
                raise


def get_evolution_stage(chain: dict, target_id: int) -> tuple[int, bool]:
    """Walk evolution chain to find stage (1/2/3) and whether fully evolved."""
    # BFS through the chain
    queue = [(chain["chain"], 1)]
    while queue:
        node, stage = queue.pop(0)
        species_url = node["species"]["url"]
        species_id = int(species_url.rstrip("/").split("/")[-1])
        is_fully_evolved = len(node["evolves_to"]) == 0
        if species_id == target_id:
            return stage, is_fully_evolved
        for child in node["evolves_to"]:
            queue.append((child, stage + 1))
    return 1, True  # fallback


def scrape_gen1():
    pokemon_list = []
    # Cache evolution chains to avoid redundant fetches
    evo_chain_cache: dict[str, dict] = {}

    for pokemon_id in range(1, 152):
        print(f"Fetching #{pokemon_id}...", end=" ", flush=True)

        # Get basic pokemon data (types)
        poke = get_json(f"{BASE}/pokemon/{pokemon_id}")
        types = sorted(poke["types"], key=lambda t: t["slot"])
        type1 = types[0]["type"]["name"].capitalize()
        type2 = types[1]["type"]["name"].capitalize() if len(types) > 1 else "None"

        # Get species data (color, habitat, generation)
        species = get_json(f"{BASE}/pokemon-species/{pokemon_id}")
        color = species["color"]["name"].capitalize()
        habitat = species["habitat"]["name"].capitalize() if species["habitat"] else "Unknown"
        generation = int(species["generation"]["url"].rstrip("/").split("/")[-1])

        # Get evolution chain (cached)
        evo_url = species["evolution_chain"]["url"]
        if evo_url not in evo_chain_cache:
            evo_chain_cache[evo_url] = get_json(evo_url)
        chain = evo_chain_cache[evo_url]
        evolution_stage, is_fully_evolved = get_evolution_stage(chain, pokemon_id)

        entry = {
            "number": pokemon_id,
            "name": poke["name"].capitalize(),
            "type1": type1,
            "type2": type2,
            "evolution_stage": evolution_stage,
            "is_fully_evolved": is_fully_evolved,
            "color": color,
            "habitat": habitat,
            "generation": generation,
        }
        pokemon_list.append(entry)
        print(f"{entry['name']} - {type1}/{type2}, Stage {evolution_stage}, "
              f"Evolved={is_fully_evolved}, {color}, {habitat}, Gen {generation}")

    with open("data/gen1_pokemon.json", "w") as f:
        json.dump(pokemon_list, f, indent=2)

    print(f"\nDone! Saved {len(pokemon_list)} Pokémon to data/gen1_pokemon.json")


if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    scrape_gen1()
