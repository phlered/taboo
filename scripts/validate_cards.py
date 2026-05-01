#!/usr/bin/env python3
"""Quality audit for generated Taboo cards."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List

from generate_cards import contains_accent, normalize, validate_card


def load_cards(path: Path) -> List[Dict]:
    if not path.exists():
        raise FileNotFoundError(f"Cards file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("Cards file must be a JSON array")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a cards.json file")
    parser.add_argument("--cards", default="cards.json", help="Path to cards JSON")
    parser.add_argument("--show-samples", type=int, default=10, help="Max invalid samples to print")
    args = parser.parse_args()

    cards_path = Path(args.cards)
    cards = load_cards(cards_path)

    invalid = []
    level_counter = Counter()
    target_counter = Counter()
    accented_targets = 0
    accented_forbidden = 0
    forbidden_total = 0

    for card in cards:
        ok, reason = validate_card(card)
        if not ok:
            invalid.append({"reason": reason, "card": card})
            continue

        target = card["mot_a_deviner"]
        target_key = normalize(target)
        target_counter[target_key] += 1
        level_counter[card["niveau"]] += 1

        if contains_accent(target):
            accented_targets += 1

        for word in card["mots_interdits"]:
            forbidden_total += 1
            if contains_accent(word):
                accented_forbidden += 1

    duplicate_targets = {k: v for k, v in target_counter.items() if v > 1}

    print(f"File: {cards_path}")
    print(f"Total cards: {len(cards)}")
    print(f"Valid cards: {len(cards) - len(invalid)}")
    print(f"Invalid cards: {len(invalid)}")
    print(f"Duplicate targets: {len(duplicate_targets)}")
    print(f"Levels: {dict(level_counter)}")

    target_ratio = (accented_targets / len(cards) * 100) if cards else 0.0
    forbidden_ratio = (accented_forbidden / forbidden_total * 100) if forbidden_total else 0.0
    print(f"Targets with accents: {accented_targets}/{len(cards)} ({target_ratio:.1f}%)")
    print(
        f"Forbidden words with accents: {accented_forbidden}/{forbidden_total} "
        f"({forbidden_ratio:.1f}%)"
    )

    if duplicate_targets:
        print("\nTop duplicate targets:")
        for target_key, count in sorted(duplicate_targets.items(), key=lambda x: x[1], reverse=True)[: args.show_samples]:
            print(f"- {target_key}: {count}")

    if invalid:
        print("\nInvalid samples:")
        for sample in invalid[: args.show_samples]:
            print(f"- reason={sample['reason']} card={sample['card']}")


if __name__ == "__main__":
    main()
