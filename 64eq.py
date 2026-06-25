import random
import json
from itertools import combinations


# =========================
# Settings
# =========================

RESULT_FILE = "quad64_example_hands_binary_9_each.json"

DECK_SIZE = 64
K_MIN = 1
K_MAX = 14

BATCH_TRIALS = 10000000
EXAMPLES_PER_QUAD_COUNT = 9


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
# Load and save results
# =========================

def normalize_examples(raw_examples):
    """
    Convert old format to new format if needed.

    Old format:
        "3": {"hand": [...], "quads": [...]}

    New format:
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


def load_results():
    """
    Load previous examples from JSON file.
    If the file does not exist, start fresh.
    """
    try:
        with open(RESULT_FILE, "r") as f:
            data = json.load(f)

    except FileNotFoundError:
        data = {}

    results = {}

    for k in range(K_MIN, K_MAX + 1):
        k_str = str(k)

        if k_str in data:
            raw_examples = data[k_str].get("examples", {})
            examples = normalize_examples(raw_examples)

            results[k] = {
                "trials": data[k_str].get("trials", 0),
                "examples": examples,
            }

        else:
            results[k] = {
                "trials": 0,
                "examples": {},
            }

    return results


def save_results(results):
    """
    Save examples to JSON file.
    Quad counts are sorted from small to large.
    Only observed quad counts are saved.
    """
    data = {}

    for k in range(K_MIN, K_MAX + 1):
        examples = results[k]["examples"]

        sorted_examples = {}

        for q in sorted(examples.keys()):
            sorted_examples[str(q)] = examples[q]

        data[str(k)] = {
            "trials": results[k]["trials"],
            "examples": sorted_examples,
        }

    with open(RESULT_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# Duplicate checking
# =========================

def hand_signature(binary_hand):
    """
    Use tuple of binary strings as a unique signature.
    """
    return tuple(binary_hand)


def already_have_hand(example_list, binary_hand):
    """
    Check whether this exact hand is already saved.
    """
    sig = hand_signature(binary_hand)

    for example in example_list:
        old_sig = hand_signature(example["hand"])
        if old_sig == sig:
            return True

    return False


def need_more_examples(results, k, q):
    """
    Return True if this k and quad count q has fewer than 9 examples.
    """
    if q not in results[k]["examples"]:
        return True

    return len(results[k]["examples"][q]) < EXAMPLES_PER_QUAD_COUNT


# =========================
# Search for example hands
# =========================

def search_more_examples(results, batch_trials=BATCH_TRIALS):
    """
    For every k, randomly generate hands.

    For each possible quad count q that appears, save up to
    EXAMPLES_PER_QUAD_COUNT different example hands.
    """
    deck = list(range(DECK_SIZE))

    for k in range(K_MIN, K_MAX + 1):
        print()
        print("Searching k =", k)

        new_found_for_k = 0

        for _ in range(batch_trials):
            hand = sorted(random.sample(deck, k))
            q = count_quads(hand)

            if need_more_examples(results, k, q):
                quads = list_quads(hand)

                binary_hand = hand_to_binary(hand, DECK_SIZE)
                binary_quads = quads_to_binary(quads, DECK_SIZE)

                if q not in results[k]["examples"]:
                    results[k]["examples"][q] = []

                if not already_have_hand(results[k]["examples"][q], binary_hand):
                    example = {
                        "hand": binary_hand,
                        "quads": binary_quads,
                    }

                    results[k]["examples"][q].append(example)
                    new_found_for_k += 1

                    print("New example found!")
                    print("k =", k)
                    print("quad count =", q)
                    print(
                        "example number for this quad count =",
                        len(results[k]["examples"][q]),
                        "/",
                        EXAMPLES_PER_QUAD_COUNT,
                    )
                    print("hand =", binary_hand)
                    print("quads =", binary_quads)
                    print()

        results[k]["trials"] += batch_trials

        print("Finished k =", k)
        print("New examples found for this k:", new_found_for_k)

    return results


# =========================
# Print summary
# =========================

def print_summary(results):
    print()
    print("SUMMARY")
    print("=======")

    for k in range(K_MIN, K_MAX + 1):
        examples = results[k]["examples"]

        print()
        print("k =", k)
        print("total trials =", results[k]["trials"])
        print("quad counts found:", sorted(examples.keys()))

        for q in sorted(examples.keys()):
            example_list = examples[q]

            print(
                "  ",
                q,
                "quads:",
                len(example_list),
                "/",
                EXAMPLES_PER_QUAD_COUNT,
                "examples",
            )

            for i, example in enumerate(example_list, start=1):
                print("      example", i, ":", example["hand"])


# =========================
# Main program
# =========================

results = load_results()

results = search_more_examples(results, batch_trials=BATCH_TRIALS)

save_results(results)

print_summary(results)