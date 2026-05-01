#!/usr/bin/env python3
"""Generate taboo cards from a source list using OpenAI gpt-4o-mini."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
import unicodedata
from pathlib import Path
from typing import Dict, List, Set, Tuple

from openai import OpenAI

GENERIC_FORBIDDEN = {
    "truc",
    "chose",
    "machin",
    "bidule",
    "faire",
    "etre",
    "avoir",
    "aller",
}


def normalize(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def contains_accent(text: str) -> bool:
    decomposed = unicodedata.normalize("NFD", text)
    return any(unicodedata.category(ch) == "Mn" for ch in decomposed)


def rough_stem(word: str) -> str:
    word = normalize(word)
    for suffix in ("es", "s", "e", "ent", "er", "ir", "re"):
        if word.endswith(suffix) and len(word) >= 6:
            return word[: -len(suffix)]
    return word


def is_forbidden_valid(target: str, forbidden: str) -> bool:
    t = normalize(target)
    f = normalize(forbidden)
    if not f:
        return False
    if f in GENERIC_FORBIDDEN:
        return False
    if t == f:
        return False
    # Block direct lexical derivatives like "chat" / "chaton" while allowing
    # useful in-word hints like "pluie" for "parapluie".
    if t.startswith(f) or f.startswith(t):
        return False
    if rough_stem(t) == rough_stem(f):
        return False
    return True


def validate_card(card: Dict) -> Tuple[bool, str]:
    if not isinstance(card, dict):
        return False, "card_not_object"

    target = card.get("mot_a_deviner")
    forbidden = card.get("mots_interdits")
    level = card.get("niveau")

    if not isinstance(target, str) or not target.strip():
        return False, "invalid_target"
    if level not in {"facile", "moyen", "difficile"}:
        return False, "invalid_level"
    if not isinstance(forbidden, list) or len(forbidden) != 5:
        return False, "forbidden_not_5"

    normalized = []
    for word in forbidden:
        if not isinstance(word, str):
            return False, "forbidden_not_string"
        if not is_forbidden_valid(target, word):
            return False, "forbidden_conflict"
        normalized.append(normalize(word))

    if len(set(normalized)) != 5:
        return False, "forbidden_duplicates"

    return True, "ok"


def validate_card_against_batch(
    card: Dict,
    expected_by_normalized_target: Dict[str, Dict[str, str]],
    strict_accents: bool,
) -> Tuple[bool, str]:
    target = card.get("mot_a_deviner") if isinstance(card, dict) else None
    level = card.get("niveau") if isinstance(card, dict) else None

    if not isinstance(target, str):
        return False, "invalid_target"

    target_key = normalize(target)
    expected = expected_by_normalized_target.get(target_key)
    if expected is None:
        return False, "unexpected_target"

    expected_target = expected["mot"]
    expected_level = expected["niveau"]

    # The model must keep the exact target string provided by source words.
    if target != expected_target:
        return False, "target_not_exact"

    if level != expected_level:
        return False, "level_mismatch"

    if strict_accents and contains_accent(expected_target) and not contains_accent(target):
        return False, "target_accent_lost"

    return True, "ok"


def build_prompt(batch: List[Dict]) -> str:
    payload = [{"mot": item["mot"], "niveau": item["niveau"]} for item in batch]
    return (
        "Génère des cartes de Taboo en français. "
        "Réponds avec UN JSON strict uniquement, au format : "
        '{"cards":[{"mot_a_deviner":"...","mots_interdits":["...","...","...","...","..."],"niveau":"facile|moyen|difficile"}]}. '\
        "Aucune phrase hors JSON. "
        "Règles : 5 mots interdits exacts, pas de doublons, pas de mot cible ou variante, "
        "pas de mots ultra génériques (truc, chose, faire, être, avoir). "
        "Conserve les accents français dans les mots (exemples : école, élève, théâtre). "
        "N'utilise pas d'encodage échappé, renvoie des chaînes UTF-8 lisibles. "
        "Respecte exactement le mot cible et le niveau fournis. "
        f"Liste: {json.dumps(payload, ensure_ascii=False)}"
    )


def call_model(client: OpenAI, model: str, prompt: str) -> Dict:
    completion = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Tu renvoies uniquement du JSON valide."},
            {"role": "user", "content": prompt},
        ],
    )
    content = completion.choices[0].message.content
    return json.loads(content)


def dry_run_batch(batch: List[Dict]) -> Dict:
    common = [
        "objet",
        "idee",
        "usage",
        "quotidien",
        "notion",
        "action",
        "forme",
        "couleur",
        "taille",
        "matiere",
    ]
    cards = []
    for item in batch:
        rnd = random.sample(common, 5)
        cards.append(
            {
                "mot_a_deviner": item["mot"],
                "mots_interdits": rnd,
                "niveau": item["niveau"],
            }
        )
    return {"cards": cards}


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue

        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate taboo cards in batches")
    parser.add_argument("--source", default="data/mots_sources.json")
    parser.add_argument("--output", default="cards.json")
    parser.add_argument("--rejected", default="data/rejected_cards.json")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--env-file", default=".env", help="Path to dotenv file")
    parser.add_argument("--start", type=int, default=0, help="Start index in source list")
    parser.add_argument("--count", type=int, default=0, help="How many words to process (0 = all)")
    parser.add_argument(
        "--no-strict-accents",
        action="store_true",
        help="Allow unaccented targets even when source word contains accents",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_path = Path(args.source)
    output_path = Path(args.output)
    rejected_path = Path(args.rejected)
    env_file_path = Path(args.env_file)

    load_env_file(env_file_path)

    source = load_json(source_path, [])
    if not source:
        raise RuntimeError(f"Source list is empty: {source_path}")

    subset = source[args.start :]
    if args.count > 0:
        subset = subset[: args.count]

    existing_cards = load_json(output_path, [])
    rejected_cards = load_json(rejected_path, [])
    strict_accents = not args.no_strict_accents

    existing_targets = {normalize(item.get("mot_a_deviner", "")) for item in existing_cards}
    pending = [item for item in subset if normalize(item["mot"]) not in existing_targets]

    print(f"Pending words: {len(pending)}")
    if not pending:
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not args.dry_run and not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Set it in environment or in .env file."
        )

    client = None if args.dry_run else OpenAI(api_key=api_key)

    for offset in range(0, len(pending), args.batch_size):
        batch = pending[offset : offset + args.batch_size]
        expected_by_target = {normalize(item["mot"]): {"mot": item["mot"], "niveau": item["niveau"]} for item in batch}
        expected_keys = set(expected_by_target.keys())
        prompt = build_prompt(batch)

        attempt = 0
        payload = None
        while attempt < args.max_retries:
            attempt += 1
            try:
                if args.dry_run:
                    payload = dry_run_batch(batch)
                else:
                    payload = call_model(client, args.model, prompt)
                break
            except Exception as exc:  # noqa: BLE001
                print(f"Batch {offset // args.batch_size + 1} attempt {attempt} failed: {exc}")
                time.sleep(1.2 * attempt)

        if payload is None:
            print("Skipping batch after retries.")
            continue

        cards = payload.get("cards", [])
        if not isinstance(cards, list):
            print("Invalid payload format: no cards array")
            continue

        valid_count = 0
        accepted_in_batch: Set[str] = set()
        for card in cards:
            ok, reason = validate_card(card)
            target_key = normalize(card.get("mot_a_deviner", "")) if isinstance(card, dict) else ""

            if ok:
                ok, reason = validate_card_against_batch(
                    card,
                    expected_by_normalized_target=expected_by_target,
                    strict_accents=strict_accents,
                )

            if not ok or not target_key or target_key in existing_targets:
                rejected_cards.append({"reason": reason if not ok else "duplicate_target", "card": card})
                continue

            if target_key in accepted_in_batch:
                rejected_cards.append({"reason": "duplicate_in_batch_response", "card": card})
                continue

            existing_cards.append(card)
            existing_targets.add(target_key)
            accepted_in_batch.add(target_key)
            valid_count += 1

        # Ensure missing cards are explicitly marked for regeneration.
        missing_targets = sorted(expected_keys - accepted_in_batch)
        for missing_target in missing_targets:
            missing_meta = expected_by_target[missing_target]
            rejected_cards.append(
                {
                    "reason": "missing_from_response",
                    "card": {
                        "mot_a_deviner": missing_meta["mot"],
                        "mots_interdits": [],
                        "niveau": missing_meta["niveau"],
                    },
                }
            )

        output_path.write_text(json.dumps(existing_cards, ensure_ascii=False, indent=2), encoding="utf-8")
        rejected_path.parent.mkdir(parents=True, exist_ok=True)
        rejected_path.write_text(json.dumps(rejected_cards, ensure_ascii=False, indent=2), encoding="utf-8")

        batch_no = offset // args.batch_size + 1
        print(f"Batch {batch_no}: {valid_count}/{len(batch)} valid cards")

    print(f"Done. cards={len(existing_cards)} rejected={len(rejected_cards)}")


if __name__ == "__main__":
    main()
