// Paste this entire script into the browser console on pokedle.com while logged in.
// It will start an infinite classic game, guess all 151 Gen 1 pokemon,
// and extract their real attribute data from the responses.

(async () => {
  const BASE = "https://pokedle.com";
  const api = (url, opts = {}) => fetch(BASE + url, {
    credentials: "include",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    ...opts,
  }).then(r => r.json());

  console.log("Starting infinite classic game...");

  // Start an infinite game with gen 1
  try {
    await fetch(BASE + "/api/infinite-games/Classic/start", {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ generations: [1] }),
    });
  } catch(e) {
    console.log("Start game response (might error if already started, that's ok):", e);
  }

  // Get the list of Gen 1 pokemon
  const pokemonList = await api("/api/pokemon?language=english&generations=1");
  console.log(`Found ${pokemonList.length} Gen 1 pokemon`);

  const allData = [];

  for (let i = 0; i < pokemonList.length; i++) {
    const pokemon = pokemonList[i];
    console.log(`Guessing ${i + 1}/${pokemonList.length}: ${pokemon.name} (#${pokemon.number})`);

    try {
      const response = await fetch(BASE + "/api/infinite-games/Classic/guesses", {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pokemonNumber: pokemon.number, language: "english" }),
      });

      const result = await response.json();

      if (result && result.fields) {
        const entry = { number: pokemon.number, name: pokemon.name };
        for (const [key, field] of Object.entries(result.fields)) {
          if (field.habitats) {
            entry[key] = field.habitats;
          } else if (field.text !== undefined) {
            entry[key] = field.text;
          } else if (field.isLargerThan !== undefined) {
            entry[key] = { text: field.text, isLargerThan: field.isLargerThan };
          }
          entry[key + "_state"] = field.guessState || field.habitatStates;
        }
        allData.push(entry);
      } else {
        // Maybe the response is wrapped differently
        allData.push({ number: pokemon.number, name: pokemon.name, raw: result });
      }

      // Small delay to be nice to the server
      await new Promise(r => setTimeout(r, 200));

      // If we found the answer, start a new game
      if (result?.isCorrectGuess) {
        console.log(`  Found the answer! Starting new game...`);
        await new Promise(r => setTimeout(r, 500));
        await fetch(BASE + "/api/infinite-games/Classic/start", {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ generations: [1] }),
        });
      }
    } catch(e) {
      console.error(`  Error guessing ${pokemon.name}:`, e);
      allData.push({ number: pokemon.number, name: pokemon.name, error: e.message });
    }
  }

  // Output the data
  console.log("\n=== DONE! Copy the JSON below ===\n");
  const json = JSON.stringify(allData, null, 2);
  console.log(json);

  // Also copy to clipboard
  try {
    await navigator.clipboard.writeText(json);
    console.log("\n(Also copied to clipboard!)");
  } catch(e) {
    console.log("\n(Could not copy to clipboard. Please select and copy the JSON above.)");
  }

  // And save as downloadable file
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "pokedle_gen1_data.json";
  a.click();
  console.log("Download triggered as pokedle_gen1_data.json");
})();
