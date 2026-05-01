#!/usr/bin/env python3
"""Prepare a ranked source list from a lexical CSV file.

Expected output format:
[
  {"mot": "chien", "rang": 1, "niveau": "facile", "pos": "NOM", "frequence": 12345.6},
  ...
]
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List

ALLOWED_POS = {"NOM", "VER", "ADJ"}
COLUMN_ALIASES = {
    "word": ["word", "mot", "lemme", "lemma", "ortho", "forme"],
    "pos": ["pos", "cgram", "catgram", "gram", "categorie", "category"],
    "frequency": [
        "frequency",
        "freq",
        "frequence",
        "freqfilms2",
        "freqlivres",
        "freqlivres2",
        "freqlemfilms2",
        "freqlemlivres",
    ],
}


def detect_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample).delimiter
    except csv.Error:
        return ","


def normalize_word(word: str) -> str:
    cleaned = word.strip().lower()
    cleaned = " ".join(cleaned.split())
    return cleaned


def is_valid_word(word: str) -> bool:
    if len(word) < 3:
        return False

    for ch in word:
        if ch in {"'", "-"}:
            continue
        if not ch.isalpha():
            return False

    return True


def normalize_pos(value: str) -> str:
    value = value.strip().upper()
    if value.startswith("N"):
        return "NOM"
    if value.startswith("V"):
        return "VER"
    if value == "ADJ":  # qualificatif uniquement — exclut ADJ:pos, ADJ:int, ADJ:dem, ADJ:num, ADJ:ind
        return "ADJ"
    return value


def assign_level(index: int, total: int) -> str:
    if total >= 3000:
        if index <= 1000:
            return "facile"
        if index <= 2000:
            return "moyen"
        return "difficile"

    third = max(1, total // 3)
    if index <= third:
        return "facile"
    if index <= third * 2:
        return "moyen"
    return "difficile"


def read_rows(path: Path) -> Iterable[Dict[str, str]]:
    head = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    delimiter = detect_delimiter(head)
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            yield row


def pick_column(fieldnames: List[str], requested: str, kind: str) -> str:
    if requested in fieldnames:
        return requested

    normalized = {name.strip().lower(): name for name in fieldnames}
    for candidate in COLUMN_ALIASES.get(kind, []):
        if candidate in normalized:
            return normalized[candidate]

    raise RuntimeError(
        f"Unable to detect '{kind}' column. Available columns: {fieldnames}. "
        f"Please pass --{kind.replace('frequency', 'freq')}-col explicitly."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare source words from a lexical CSV")
    parser.add_argument("--input", required=True, help="Input CSV path")
    parser.add_argument("--output", default="data/mots_sources.json", help="Output JSON path")
    parser.add_argument("--word-col", default="word", help="Column containing the word")
    parser.add_argument("--pos-col", default="pos", help="Column containing POS tag")
    parser.add_argument("--freq-col", default="frequency", help="Column containing frequency")
    parser.add_argument("--top", type=int, default=3000, help="How many words to keep")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    head = input_path.read_text(encoding="utf-8", errors="ignore")[:4096]
    delimiter = detect_delimiter(head)
    with input_path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        probe_reader = csv.DictReader(handle, delimiter=delimiter)
        fieldnames = probe_reader.fieldnames or []

    if not fieldnames:
        raise RuntimeError("Input CSV has no header row.")

    word_col = pick_column(fieldnames, args.word_col, "word")
    pos_col = pick_column(fieldnames, args.pos_col, "pos")
    freq_col = pick_column(fieldnames, args.freq_col, "frequency")

    print(f"Detected columns -> word: '{word_col}', pos: '{pos_col}', frequency: '{freq_col}'")

    rows: List[Dict[str, str]] = []
    seen = set()

    for row in read_rows(input_path):
        raw_word = row.get(word_col, "")
        raw_pos = row.get(pos_col, "")
        raw_freq = row.get(freq_col, "")

        word = normalize_word(raw_word)
        pos = normalize_pos(raw_pos)

        if pos not in ALLOWED_POS:
            continue
        if not is_valid_word(word):
            continue
        if word in seen:
            continue

        try:
            frequency = float(str(raw_freq).replace(",", "."))
        except ValueError:
            continue

        seen.add(word)
        rows.append({"mot": word, "pos": pos, "frequence": frequency})

    rows.sort(key=lambda item: item["frequence"], reverse=True)
    rows = rows[: args.top]

    output = []
    for idx, item in enumerate(rows, start=1):
        output.append(
            {
                "mot": item["mot"],
                "rang": idx,
                "niveau": assign_level(idx, len(rows)),
                "pos": item["pos"],
                "frequence": item["frequence"],
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = {"facile": 0, "moyen": 0, "difficile": 0}
    for item in output:
        counts[item["niveau"]] += 1

    print(f"Saved {len(output)} words to {output_path}")
    print(f"Distribution: {counts}")


if __name__ == "__main__":
    main()
