"""Optimal Pokedle Classic solver using entropy-based decision tree."""

import json
import math
from collections import Counter
from enum import Enum
from typing import NamedTuple


# --- Feedback types ---

class Status(Enum):
    CORRECT = "correct"
    PARTIAL = "partial"
    WRONG = "wrong"
    WRONG_HIGHER = "wrong_higher"  # answer is higher
    WRONG_LOWER = "wrong_lower"    # answer is lower


class Feedback(NamedTuple):
    type1: Status
    type2: Status
    evolution_stage: Status
    is_fully_evolved: Status
    color: Status
    habitat: Status
    generation: Status


ALL_CORRECT = Feedback(*([Status.CORRECT] * 7))


# --- Data loading ---

def load_pokemon(path: str = "data/gen1_pokemon.json") -> list[dict]:
    with open(path) as f:
        return json.load(f)


# --- Feedback function ---

def type_feedback(guess_t1: str, guess_t2: str, answer_t1: str, answer_t2: str) -> tuple[Status, Status]:
    """Compute feedback for type1 and type2.

    Rules (from JS analysis):
    - Correct: type matches in same slot
    - Partial: type exists in the other slot
    - Wrong: type doesn't match either slot
    """
    guess_types = {guess_t1, guess_t2}
    answer_types = {answer_t1, answer_t2}

    def single_type_fb(guess_val: str, answer_same_slot: str, answer_other_slot: str) -> Status:
        if guess_val == answer_same_slot:
            return Status.CORRECT
        if guess_val != "None" and guess_val in answer_types:
            return Status.PARTIAL
        return Status.WRONG

    fb1 = single_type_fb(guess_t1, answer_t1, answer_t2)
    fb2 = single_type_fb(guess_t2, answer_t2, answer_t1)
    return fb1, fb2


def number_feedback(guess_val: int, answer_val: int) -> Status:
    """Feedback for numeric fields (evolution_stage, generation)."""
    if guess_val == answer_val:
        return Status.CORRECT
    if guess_val < answer_val:
        return Status.WRONG_HIGHER
    return Status.WRONG_LOWER


def exact_feedback(guess_val, answer_val) -> Status:
    """Feedback for exact match fields (is_fully_evolved)."""
    return Status.CORRECT if guess_val == answer_val else Status.WRONG


def multi_value_feedback(guess_vals: list, answer_vals: list) -> Status:
    """Feedback for multi-value fields (color, habitat).

    Per-element: green if same position, yellow if exists but wrong position, red if not in answer.
    Overall (from Pokedle JS): all green → correct, any green/yellow → partial, all red → wrong.
    """
    answer_set = set(answer_vals)
    per_element = []
    for i, gv in enumerate(guess_vals):
        if i < len(answer_vals) and gv == answer_vals[i]:
            per_element.append("correct")
        elif gv in answer_set:
            per_element.append("partial")
        else:
            per_element.append("wrong")

    if all(s == "correct" for s in per_element) and len(guess_vals) == len(answer_vals):
        return Status.CORRECT
    if any(s in ("correct", "partial") for s in per_element):
        return Status.PARTIAL
    return Status.WRONG


def compute_feedback(guess: dict, answer: dict) -> Feedback:
    """Compute the full 7-category feedback tuple."""
    t1_fb, t2_fb = type_feedback(
        guess["type1"], guess["type2"],
        answer["type1"], answer["type2"],
    )
    return Feedback(
        type1=t1_fb,
        type2=t2_fb,
        evolution_stage=exact_feedback(guess["evolution_stage"], answer["evolution_stage"]),
        is_fully_evolved=exact_feedback(guess["is_fully_evolved"], answer["is_fully_evolved"]),
        color=multi_value_feedback(guess["color"], answer["color"]),
        habitat=multi_value_feedback(guess["habitat"], answer["habitat"]),
        generation=number_feedback(guess["generation"], answer["generation"]),
    )


# --- Entropy computation ---

def feedback_distribution(guess: dict, candidates: list[dict]) -> Counter:
    """Count how many candidates produce each feedback pattern."""
    dist = Counter()
    for answer in candidates:
        fb = compute_feedback(guess, answer)
        dist[fb] += 1
    return dist


def entropy(dist: Counter, total: int) -> float:
    """Shannon entropy of a feedback distribution."""
    h = 0.0
    for count in dist.values():
        if count > 0:
            p = count / total
            h -= p * math.log2(p)
    return h


def expected_remaining(dist: Counter, total: int) -> float:
    """Expected number of remaining candidates after guess."""
    return sum(count * count for count in dist.values()) / total


# --- Solver: build the full decision tree ---

class TreeNode:
    """A node in the decision tree."""
    def __init__(self, guess: dict, children: dict = None, depth: int = 1,
                 indistinguishable: list[dict] = None):
        self.guess = guess          # the pokemon to guess
        self.children = children or {}  # feedback -> TreeNode
        self.depth = depth          # depth at this node
        # Group of pokemon that all produce ALL_CORRECT feedback for each other.
        # Must guess them one by one. None if this is a normal node.
        self.indistinguishable = indistinguishable

    def total_guesses(self) -> int:
        """Sum of guesses across all possible answers."""
        if self.indistinguishable:
            # For N indistinguishable pokemon starting at depth d,
            # guesses needed: d, d+1, d+2, ..., d+N-1
            n = len(self.indistinguishable)
            return sum(self.depth + i for i in range(n))
        if not self.children:
            return self.depth
        return sum(child.total_guesses() for child in self.children.values())

    def worst_case(self) -> int:
        if self.indistinguishable:
            return self.depth + len(self.indistinguishable) - 1
        if not self.children:
            return self.depth
        return max(child.worst_case() for child in self.children.values())

    def count_answers(self) -> int:
        """Count total number of distinct answers reachable."""
        if self.indistinguishable:
            return len(self.indistinguishable)
        if not self.children:
            return 1
        return sum(child.count_answers() for child in self.children.values())

    def collect_depths(self, counts: Counter):
        """Collect depth distribution across all answers."""
        if self.indistinguishable:
            for i in range(len(self.indistinguishable)):
                counts[self.depth + i] += 1
            return
        if not self.children:
            counts[self.depth] += 1
            return
        for child in self.children.values():
            child.collect_depths(counts)


def pick_best_guess(candidates: list[dict], all_pokemon: list[dict], use_full_pool: bool = True) -> tuple[dict, Counter]:
    """Pick the guess that maximizes entropy over candidates.

    If use_full_pool, consider all pokemon as possible guesses (not just remaining candidates).
    This can sometimes be better even though the guess itself can't be correct.
    """
    pool = all_pokemon if use_full_pool else candidates
    n = len(candidates)

    if n <= 2:
        # Just guess the first candidate
        return candidates[0], feedback_distribution(candidates[0], candidates)

    best_guess = None
    best_entropy = -1.0
    best_dist = None

    for guess in pool:
        dist = feedback_distribution(guess, candidates)
        h = entropy(dist, n)

        # Tiebreak: prefer guesses that are themselves candidates
        is_candidate = any(c["number"] == guess["number"] for c in candidates)

        if (h > best_entropy + 1e-12) or (
            abs(h - best_entropy) < 1e-12 and is_candidate and best_guess and
            not any(c["number"] == best_guess["number"] for c in candidates)
        ):
            best_entropy = h
            best_guess = guess
            best_dist = dist

    return best_guess, best_dist


def build_tree(candidates: list[dict], all_pokemon: list[dict],
               depth: int = 1, max_depth: int = 20, use_full_pool: bool = True) -> TreeNode:
    """Recursively build the greedy entropy decision tree."""
    if len(candidates) == 1:
        return TreeNode(candidates[0], depth=depth)

    # Check if all candidates are indistinguishable (identical attributes)
    first = candidates[0]
    if all(compute_feedback(first, c) == ALL_CORRECT for c in candidates):
        return TreeNode(first, depth=depth, indistinguishable=candidates)

    if depth >= max_depth:
        return TreeNode(candidates[0], depth=depth)

    guess, dist = pick_best_guess(candidates, all_pokemon, use_full_pool)
    node = TreeNode(guess, depth=depth)

    for fb, count in dist.items():
        remaining = [c for c in candidates if compute_feedback(guess, c) == fb]
        if not remaining:
            continue
        if fb == ALL_CORRECT:
            # All remaining here are indistinguishable from the guess
            if len(remaining) == 1:
                node.children[fb] = TreeNode(remaining[0], depth=depth)
            else:
                node.children[fb] = TreeNode(remaining[0], depth=depth,
                                             indistinguishable=remaining)
        else:
            node.children[fb] = build_tree(remaining, all_pokemon, depth + 1, max_depth, use_full_pool)

    return node


def print_tree_stats(tree: TreeNode, n_pokemon: int):
    """Print summary statistics for the decision tree."""
    total = tree.total_guesses()
    worst = tree.worst_case()
    answers = tree.count_answers()
    avg = total / n_pokemon

    print(f"  Optimal first guess: {tree.guess['name']}")
    print(f"  Average guesses:     {avg:.3f}")
    print(f"  Worst case:          {worst} guesses")
    print(f"  Total guesses:       {total} (across {answers} pokemon)")

    depth_counts = Counter()
    tree.collect_depths(depth_counts)
    print(f"  Distribution:")
    for d in sorted(depth_counts):
        pct = depth_counts[d] / n_pokemon * 100
        bar = "█" * int(pct / 2)
        print(f"    {d} guesses: {depth_counts[d]:3d} ({pct:5.1f}%) {bar}")


def serialize_tree(node: TreeNode) -> dict:
    """Serialize tree to JSON-compatible dict."""
    result = {
        "guess": node.guess["name"],
        "number": node.guess["number"],
        "depth": node.depth,
    }
    if node.indistinguishable:
        result["indistinguishable"] = [p["name"] for p in node.indistinguishable]
    if node.children:
        result["children"] = {}
        for fb, child in node.children.items():
            key = "|".join(s.value for s in fb)
            result["children"][key] = serialize_tree(child)
    return result


# --- Main ---

def main():
    print("Loading Pokemon data...")
    pokemon = load_pokemon()
    n = len(pokemon)
    print(f"Loaded {n} Gen 1 Pokemon\n")

    print("Building greedy entropy decision tree...")
    print("(considering all 151 pokemon as guesses at each step)\n")

    tree = build_tree(pokemon, pokemon, use_full_pool=True)

    print("=== RESULTS ===")
    print_tree_stats(tree, n)

    # Save tree
    tree_data = serialize_tree(tree)
    with open("data/decision_tree.json", "w") as f:
        json.dump(tree_data, f, indent=2)
    print(f"\nDecision tree saved to data/decision_tree.json")


if __name__ == "__main__":
    main()
