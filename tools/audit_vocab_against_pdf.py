#!/usr/bin/env python3
"""Audit HSK CSV structure against the official 2025 syllabus PDF."""

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from pypdf import PdfReader


ROW_START = re.compile(
    r"(?<!\d)(\d{1,5})\s+(?=(?:[1-6]|7-9)(?:（(?:[1-6]|7-9)）)*)"
)
THAI = re.compile(r"[ก-๙]")
HAN = re.compile(r"[\u3400-\u9fff]")


def normalize(value):
    text = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"[\s、,，.\-]", "", text)


def extract_official_rows(pdf_path):
    reader = PdfReader(str(pdf_path))
    source_rows = {}

    # Vocabulary occupies PDF pages 4-265 (zero-based slice 3:265).
    for page in reader.pages[3:265]:
        lines = []
        for line in (page.extract_text() or "").splitlines():
            line = " ".join(line.split())
            if (
                not line
                or line == "序号 等级 词语 拼音 词性"
                or line == "汉考国际"
                or re.fullmatch(r"\d{1,3}", line)
            ):
                continue
            lines.append(line)

        page_text = " ".join(lines)
        starts = list(ROW_START.finditer(page_text))
        for index, match in enumerate(starts):
            row_id = int(match.group(1))
            end = starts[index + 1].start() if index + 1 < len(starts) else len(page_text)
            if 1 <= row_id <= 11000:
                source_rows[row_id] = page_text[match.start():end].strip()

    return source_rows


def audit(csv_path, pdf_path):
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    source_rows = extract_official_rows(pdf_path)
    expected_ids = set(range(1, 11001))
    structural_mismatches = []
    official_pos_mismatches = []
    source_blank_pos = []

    for row in rows:
        row_id = int(row["id"])
        source = normalize(source_rows.get(row_id, ""))
        prefix = normalize(
            " ".join(
                [row["id"], row["hsk_level"], row["word"], row["pinyin"]]
            )
        )
        if not source.startswith(prefix):
            structural_mismatches.append(row_id)
            continue

        source_pos = source[len(prefix):]
        csv_pos = normalize(row["pos_zh"])
        if source_pos and source_pos != csv_pos:
            official_pos_mismatches.append(row_id)
        elif not source_pos and csv_pos not in ("", "-"):
            source_blank_pos.append(row_id)

    duplicate_words = {
        word: count for word, count in Counter(row["word"] for row in rows).items() if count > 1
    }
    required_columns = rows[0].keys() if rows else []
    empty_by_column = {
        column: sum(not str(row.get(column, "")).strip() for row in rows)
        for column in required_columns
    }

    return {
        "csv_rows": len(rows),
        "pdf_vocab_rows": len(source_rows),
        "csv_missing_ids": sorted(expected_ids - {int(row["id"]) for row in rows}),
        "pdf_missing_ids": sorted(expected_ids - set(source_rows)),
        "duplicate_ids": len(rows) - len({row["id"] for row in rows}),
        "empty_by_column": empty_by_column,
        "structural_mismatch_ids": structural_mismatches,
        "official_nonblank_pos_mismatch_ids": official_pos_mismatches,
        "source_blank_pos_count": len(source_blank_pos),
        "source_blank_pos_ids_sample": source_blank_pos[:30],
        "duplicate_word_spellings": len(duplicate_words),
        "thai_translation_without_thai_count": sum(
            not THAI.search(row["trans_th"]) for row in rows
        ),
        "thai_translation_with_han_count": sum(
            bool(HAN.search(row["trans_th"])) for row in rows
        ),
        "thai_example_without_thai_count": sum(
            not THAI.search(row["example_th"]) for row in rows
        ),
        "thai_example_with_han_count": sum(
            bool(HAN.search(row["example_th"])) for row in rows
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.csv, args.pdf), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
