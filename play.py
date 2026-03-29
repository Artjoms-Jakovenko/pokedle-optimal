"""Interactive Pokedle solver — tells you what to guess, you input the feedback."""

import json
from solver import (
    load_pokemon, compute_feedback, pick_best_guess, Status, Feedback, ALL_CORRECT,
)

CATEGORIES = ["type1", "type2", "evolution_stage", "is_fully_evolved", "color", "habitat", "generation"]
LABELS = ["Type 1", "Type 2", "Evo Stage", "Fully Evolved", "Color", "Habitat", "Generation"]

STATUS_MAP = {
    "g": Status.CORRECT,
    "y": Status.PARTIAL,
    "r": Status.WRONG,
    "u": Status.WRONG_HIGHER,   # answer is higher (up arrow)
    "d": Status.WRONG_LOWER,    # answer is lower (down arrow)
}

HELP_TEXT = """
Enter feedback for each category as a single string of 7 characters:
  g = green (correct)
  y = yellow (partial match — types only)
  r = red (wrong)
  u = up arrow (answer is higher — Evo Stage & Generation)
  d = down arrow (answer is lower — Evo Stage & Generation)

  Category order: Type1  Type2  EvoStage  FullyEvolved  Color  Habitat  Gen
  Example:        g      r      u         g             r      g        g
  You'd type:     grugrgr

Type 'quit' to exit, 'help' for this message, 'list' to see remaining candidates.
"""


def parse_feedback(s: str) -> Feedback | None:
    s = s.strip().lower()
    if len(s) != 7:
        return None
    try:
        statuses = [STATUS_MAP[c] for c in s]
        return Feedback(*statuses)
    except KeyError:
        return None


def main():
    pokemon = load_pokemon()
    candidates = list(pokemon)

    print("=" * 50)
    print("  POKEDLE OPTIMAL SOLVER")
    print("=" * 50)
    print(f"\n{len(candidates)} Pokemon in pool")
    print(HELP_TEXT)

    turn = 1
    while True:
        print(f"\n--- Turn {turn} ({len(candidates)} candidates remaining) ---")

        if len(candidates) == 0:
            print("No candidates remaining! Something went wrong with the feedback.")
            break

        if len(candidates) == 1:
            print(f"  >> It must be: {candidates[0]['name']} (#{candidates[0]['number']})")
            print("  Guess it and you win!")
            break

        # Check for indistinguishable groups
        guess, dist = pick_best_guess(candidates, pokemon, use_full_pool=True)
        print(f"  >> Guess: {guess['name']} (#{guess['number']})")

        # Show what we know
        print(f"     Type: {guess['type1']}/{guess['type2']}  "
              f"Evo: {guess['evolution_stage']}  "
              f"Evolved: {'Yes' if guess['is_fully_evolved'] else 'No'}  "
              f"Color: {guess['color']}  "
              f"Habitat: {guess['habitat']}  "
              f"Gen: {guess['generation']}")

        while True:
            raw = input("\n  Feedback (7 chars, or 'help'): ").strip()

            if raw.lower() == "quit":
                print("Bye!")
                return
            if raw.lower() == "help":
                print(HELP_TEXT)
                continue
            if raw.lower() == "list":
                for c in candidates:
                    print(f"    #{c['number']:3d} {c['name']}")
                continue

            if raw.lower() == "ggggggg":
                print(f"\n  Solved in {turn} guesses! The answer was {guess['name']}!")
                return

            fb = parse_feedback(raw)
            if fb is None:
                print("  Invalid input. Use exactly 7 characters: g/y/r/u/d")
                continue

            # Filter candidates
            new_candidates = [c for c in candidates if compute_feedback(guess, c) == fb]

            if len(new_candidates) == 0:
                print(f"  Warning: no candidates match that feedback!")
                print(f"  Double-check your input. The feedback you entered:")
                for label, status in zip(LABELS, fb):
                    print(f"    {label:14s} = {status.value}")
                retry = input("  Try again? (y/n): ").strip().lower()
                if retry == "y":
                    continue
                else:
                    print("  Keeping current candidates and continuing...")
                    break
            else:
                candidates = new_candidates
                eliminated = len(pokemon) - len(candidates)
                print(f"  Narrowed to {len(candidates)} candidates (eliminated {eliminated} total)")
                break

        turn += 1

    print("\nDone!")


if __name__ == "__main__":
    main()
