# Pokedle Optimal Solver

## Goal

Build a solver that finds the **optimal guesses** for [Pokedle Classic](https://pokedle.com/classic), a Pokémon guessing game.

## How Pokedle Classic Works

- You guess a Pokémon and get feedback across **7 categories** (need to confirm exact categories by inspecting the game — likely some combination of: Type 1, Type 2, Generation, Color, Habitat, Evolution Stage, Height, Weight, etc.)
- Feedback per category: **green** (exact match), **yellow** (partial match), **red** (no match). Numeric fields (height/weight) use **arrows** (up/down) to indicate direction.
- The goal is to identify the hidden Pokémon in as few guesses as possible.

## IMPORTANT: Confirm the game mechanics first

The exact 7 categories and feedback rules MUST be confirmed by inspecting the actual game at https://pokedle.com/classic. Play a round or inspect the page source/network requests to determine:
1. The exact 7 category column headers
2. The exact feedback rules for each category (what counts as green/yellow/red)
3. The full pool of Pokémon the game uses (which generations, any exclusions)

## Approach: Information-Theoretic Solver

### Algorithm

1. **Data**: Get all Pokémon with their 7 attributes (use PokeAPI or similar)
2. **Feedback function**: `feedback(guess, answer) → 7-tuple` that exactly replicates the game's behavior
3. **Greedy entropy maximization**: For each possible guess, compute feedback patterns against all remaining candidates, score by Shannon entropy. Pick the highest-entropy guess. This is O(N²) per turn — very feasible for ~1000 Pokémon.
4. **Optional: Full minimax tree search**: Brute-force search all guesses at each node, pruned with alpha-beta style cutoffs. Minimizes worst-case guess count. Use entropy ordering to try best guesses first for aggressive pruning.

### Key formulas

- **Entropy**: `−Σ (bucket_size / total) × log₂(bucket_size / total)` — higher = better
- **Expected remaining**: `Σ (bucket_size / total) × bucket_size` — lower = better

### Implementation plan

1. Scrape/fetch Pokémon data with all 7 attributes
2. Implement the feedback function (must match the game exactly)
3. Implement greedy entropy solver — find optimal first guess
4. Build interactive solver that takes real game feedback and suggests next guess
5. (Stretch) Full minimax tree for provably optimal play

## Tech

- Python 3.12
- No heavy frameworks needed — just data processing and math
