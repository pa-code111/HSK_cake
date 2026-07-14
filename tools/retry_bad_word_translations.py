#!/usr/bin/env python3
"""Retry only word translations that still contain Chinese source text."""

import csv
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from retranslate_vocab import spoken_word, translate_request


HAN = re.compile(r"[\u3400-\u9fff]")
THAI = re.compile(r"[ก-๙]")


def invalid(value, target):
    if not value or HAN.search(value):
        return True
    return target == "th" and not THAI.search(value)


def main():
    source = Path("tmp/hsk_vocabnew_retranslated.csv")
    output = Path("tmp/hsk_vocabnew_retranslated_retry.csv")
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    tasks = set()
    for row in rows:
        word = spoken_word(row["word"])
        if invalid(row["trans_th"], "th"):
            tasks.add(("th", word))
        if invalid(row["trans_en"], "en"):
            tasks.add(("en", word))

    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(translate_request, word, target, 3): (target, word)
            for target, word in sorted(tasks)
        }
        for index, future in enumerate(as_completed(futures), start=1):
            target, word = futures[future]
            value = future.result()
            if value and not invalid(value, target):
                results[(target, word)] = value.strip()
            if index % 50 == 0 or index == len(futures):
                print(f"retry: {index}/{len(futures)}", flush=True)

    unresolved = []
    for row in rows:
        word = spoken_word(row["word"])
        for target, column in (("th", "trans_th"), ("en", "trans_en")):
            value = results.get((target, word))
            if value:
                row[column] = value
            if invalid(row[column], target):
                unresolved.append((row["id"], column, row["word"], row[column]))

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows; unresolved word translations: {len(unresolved)}")
    if unresolved:
        print("sample unresolved:", unresolved[:20])


if __name__ == "__main__":
    main()
