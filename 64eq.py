import random
import json
import os
from itertools import combinations


# =========================
# Settings
# =========================

RESULT_FILE = "quad64_discovery_examples_30_each.json"

DECK_SIZE = 64
K_MIN = 1
K_MAX = 14

BATCH_TRIALS_PER_K = 1000000
EXAMPLES_PER_QUAD_COUNT = 30

# None means keep running forever until you stop it with Ctrl+C.
# If you want to test first, set MAX_BATCHES = 1 or 2.
MAX_BATCHES = None


# =========================
# Binary formatting
# =========================

def bit_width(deck_size):
    """
    Quad-64  -> 6 bits
    Quad-128 -> 7 bits
    Quad-256 -> 8 bits
    """
    return deck_size.bit_length() - 1


def to_binary(card, deck_size):
    width = bit_width(deck_size)
    return format(card, "0{}b".format(width))


def hand_to_binary(hand, deck_size):
    return [to_binary(card, deck_size) for card in hand]


def quads_to_binary(quads, deck_size):
    binary_quads = []

    for quad in quads:
        binary_quad = [to_binary(card, deck_size) for card in quad]
        binary_quads.append(binary_quad)

    return binary_quads


def binary_hand_signature(binary_hand):
    return tuple(binary_hand)


# =========================
# Quad counting
# =========================

def count_quads(hand):
    """
    Count how many quads are in a hand.

    Cards are represented as integers.
    XOR is addition over F_2.
    A quad satisfies a ^ b ^ c ^ d == 0.
    """
    hand_set = set(hand)
    count = 0

    for a, b, c in combinations(hand, 3):
        d = a ^ b ^ c

        if d in hand_set:
            count += 1

    # Each quad is counted 4 times, once for each choice of 3 cards.
    return count // 4


def list_quads(hand):
    """
    Return the actual quads inside a hand.
    Each quad is stored once as a sorted tuple.
    """
    hand_set = set(hand)
    quads = set()

    for a, b, c in combinations(hand, 3):
        d = a ^ b ^ c

        if d in hand_set:
            quad = tuple(sorted([a, b, c, d]))
            quads.add(quad)

    return sorted(quads)


# =========================
# Results structure
# =========================

def fresh_results():
    results = {}

    for k in range(K_MIN, K_MAX + 1):
        results[k] = {
            "trials": 0,
            "distribution": {},
            "examples": {},
        }

    return results


def normalize_examples(raw_examples):
    """
    Convert old example format to new format if needed.

    Old:
        "3": {"hand": [...], "quads": [...]}

    New:
        "3": [
            {"hand": [...], "quads": [...]},
            {"hand": [...], "quads": [...]}
        ]
    """
    examples = {}

    for q_str, value in raw_examples.items():
        q = int(q_str)

        if isinstance(value, list):
            examples[q] = value
        elif isinstance(value, dict):
            examples[q] = [value]
        else:
            examples[q] = []

    return examples


def normalize_loaded_results(data):
    """
    Normalize old or partial JSON files into the current structure.
    This allows you to continue from older files.
    """
    results = fresh_results()

    for k in range(K_MIN, K_MAX + 1):
        k_str = str(k)

        if k_str not in data:
            continue

        old = data[k_str]

        trials = old.get("trials", 0)
        raw_distribution = old.get("distribution", {})
        raw_examples = old.get("examples", {})

        distribution = {}
        for q_str, count in raw_distribution.items():
            distribution[int(q_str)] = count

        examples = normalize_examples(raw_examples)

        # If an old file had examples but no distribution,
        # at least make sure those q values are recognized.
        for q in examples.keys():
            if q not in distribution:
                distribution[q] = 0

        results[k] = {
            "trials": trials,
            "distribution": distribution,
            "examples": examples,
        }

    return results


def load_results():
    """
    Load previous results from JSON file.
    If the file does not exist, start fresh.
    """
    if not os.path.exists(RESULT_FILE):
        return fresh_results()

    with open(RESULT_FILE, "r") as f:
        data = json.load(f)

    return normalize_loaded_results(data)


def save_results(results):
    """
    Save distribution and examples to JSON.
    Quad counts are sorted from small to large.
    """
    data = {}

    for k in range(K_MIN, K_MAX + 1):
        distribution = results[k]["distribution"]
        examples = results[k]["examples"]

        sorted_distribution = {}
        for q in sorted(distribution.keys()):
            sorted_distribution[str(q)] = distribution[q]

        sorted_examples = {}
        for q in sorted(examples.keys()):
            sorted_examples[str(q)] = examples[q]

        data[str(k)] = {
            "trials": results[k]["trials"],
            "distribution": sorted_distribution,
            "examples": sorted_examples,
        }

    with open(RESULT_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# Example saving
# =========================

def already_have_hand(example_list, binary_hand):
    """
    Check whether this exact binary hand is already saved.
    """
    sig = binary_hand_signature(binary_hand)

    for example in example_list:
        old_sig = binary_hand_signature(example["hand"])
        if old_sig == sig:
            return True

    return False


def save_example_if_needed(results, k, q, hand):
    """
    Save this hand as an example if this k and q has fewer than 30 examples.
    Return True if saved.
    """
    if q not in results[k]["examples"]:
        results[k]["examples"][q] = []

    example_list = results[k]["examples"][q]

    if len(example_list) >= EXAMPLES_PER_QUAD_COUNT:
        return False

    binary_hand = hand_to_binary(hand, DECK_SIZE)

    if already_have_hand(example_list, binary_hand):
        return False

    quads = list_quads(hand)
    binary_quads = quads_to_binary(quads, DECK_SIZE)

    example = {
        "hand": binary_hand,
        "quads": binary_quads,
    }

    example_list.append(example)
    return True


# =========================
# Discovery search
# =========================

def run_one_batch(results, batch_number):
    """
    Run one discovery batch.

    For each k:
    - randomly sample hands
    - update distribution
    - save up to 30 examples for every observed quad count
    """
    deck = list(range(DECK_SIZE))

    print()
    print("=" * 60)
    print("BATCH", batch_number)
    print("=" * 60)

    total_new_quad_counts = 0
    total_new_examples = 0

    for k in range(K_MIN, K_MAX + 1):
        print()
        print("Searching k =", k)

        new_quad_counts_for_k = []
        new_examples_for_k = 0

        for trial in range(1, BATCH_TRIALS_PER_K + 1):
            hand = sorted(random.sample(deck, k))
            q = count_quads(hand)

            # Update distribution
            if q not in results[k]["distribution"]:
                results[k]["distribution"][q] = 0
                new_quad_counts_for_k.append(q)
                total_new_quad_counts += 1

                print()
                print("NEW QUAD COUNT DISCOVERED!")
                print("k =", k)
                print("quad count =", q)
                print("hand =", hand_to_binary(hand, DECK_SIZE))
                print()

            results[k]["distribution"][q] += 1

            # Save example if needed
            saved = save_example_if_needed(results, k, q, hand)

            if saved:
                new_examples_for_k += 1
                total_new_examples += 1

                current_count = len(results[k]["examples"][q])

                print("New example saved!")
                print("k =", k)
                print("quad count =", q)
                print("example number =", current_count, "/", EXAMPLES_PER_QUAD_COUNT)
                print("hand =", hand_to_binary(hand, DECK_SIZE))
                print()

            if trial % 20000 == 0:
                print(
                    "  progress:",
                    trial,
                    "/",
                    BATCH_TRIALS_PER_K,
                    "for k =",
                    k,
                )

        results[k]["trials"] += BATCH_TRIALS_PER_K

        print("Finished k =", k)
        print("total trials for k =", results[k]["trials"])
        print("quad counts found so far =", sorted(results[k]["distribution"].keys()))

        if new_quad_counts_for_k:
            print("new quad counts this batch =", sorted(new_quad_counts_for_k))
        else:
            print("no new quad counts this batch")

        print("new examples saved for this k =", new_examples_for_k)

    print()
    print("BATCH SUMMARY")
    print("new quad counts discovered =", total_new_quad_counts)
    print("new examples saved =", total_new_examples)

    return results


# =========================
# Summary
# =========================

def print_summary(results):
    print()
    print("=" * 60)
    print("CURRENT SUMMARY")
    print("=" * 60)

    for k in range(K_MIN, K_MAX + 1):
        distribution = results[k]["distribution"]
        examples = results[k]["examples"]

        print()
        print("k =", k)
        print("trials =", results[k]["trials"])
        print("quad counts found =", sorted(distribution.keys()))

        print("distribution:")
        for q in sorted(distribution.keys()):
            print("  ", q, ":", distribution[q])

        print("examples saved:")
        for q in sorted(distribution.keys()):
            current = len(examples.get(q, []))
            print(
                "  ",
                q,
                "quads:",
                current,
                "/",
                EXAMPLES_PER_QUAD_COUNT,
                "examples",
            )


def print_missing_example_counts(results):
    """
    Show observed quad counts that still have fewer than 30 examples.
    """
    print()
    print("=" * 60)
    print("OBSERVED COUNTS THAT STILL NEED MORE EXAMPLES")
    print("=" * 60)

    any_missing = False

    for k in range(K_MIN, K_MAX + 1):
        missing = []

        for q in sorted(results[k]["distribution"].keys()):
            current = len(results[k]["examples"].get(q, []))

            if current < EXAMPLES_PER_QUAD_COUNT:
                missing.append((q, current))

        if missing:
            any_missing = True
            print()
            print("k =", k)

            for q, current in missing:
                print(
                    "  q =",
                    q,
                    ":",
                    current,
                    "/",
                    EXAMPLES_PER_QUAD_COUNT,
                )

    if not any_missing:
        print("Every observed quad count already has 30 examples.")


# =========================
# Main program
# =========================

def main():
    results = load_results()
    batch_number = 1

    try:
        while True:
            if MAX_BATCHES is not None and batch_number > MAX_BATCHES:
                break

            results = run_one_batch(results, batch_number)

            save_results(results)
            print_summary(results)
            print_missing_example_counts(results)

            print()
            print("Saved to:", RESULT_FILE)
            print("You can stop with Ctrl+C, or let it keep running.")

            batch_number += 1

    except KeyboardInterrupt:
        print()
        print("Stopped by user. Saving current results...")

    save_results(results)
    print_summary(results)
    print_missing_example_counts(results)

    print()
    print("Final saved file:", RESULT_FILE)


main()