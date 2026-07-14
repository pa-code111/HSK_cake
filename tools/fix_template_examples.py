#!/usr/bin/env python3
"""Replace obviously generated placeholder examples with valid meta-examples."""

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from retranslate_vocab import spoken_word, translate_request


def main():
    source = Path("tmp/hsk_vocabnew_retranslated_retry.csv")
    output = Path("tmp/hsk_vocabnew_final.csv")
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    changed = []
    for row in rows:
        is_generic = row["example_zh"] == "这个词是语法词。"
        is_bad_request = row["example_zh"].startswith("请给我一") and "|" not in row["example_zh"]
        if is_generic or is_bad_request:
            word = spoken_word(row["word"])
            row["example_zh"] = f'我们来学习“{word}”的用法。这个词在汉语中很常见。'
            changed.append(row)

    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {}
        for row in changed:
            sentence = row["example_zh"]
            futures[pool.submit(translate_request, sentence, "th", 3)] = (sentence, "th")
            futures[pool.submit(translate_request, sentence, "en", 3)] = (sentence, "en")
        for future in as_completed(futures):
            sentence, target = futures[future]
            value = future.result()
            if value:
                results[(sentence, target)] = value.strip()

    for row in changed:
        sentence = row["example_zh"]
        row["example_th"] = results.get((sentence, "th"), row["example_th"])
        row["example_en"] = results.get((sentence, "en"), row["example_en"])

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"rewrote {len(changed)} template examples; wrote {len(rows)} rows")


if __name__ == "__main__":
    main()
