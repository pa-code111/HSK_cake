#!/usr/bin/env python3
"""Apply hand-reviewed fixes to machine-translated edge cases."""

import csv
from pathlib import Path


OVERRIDES = {
    "506": {
        "trans_th": "(บุพบทนำกรรมมาก่อนกริยา) / (ลักษณนามสำหรับของที่ถือได้)",
        "trans_en": "object-fronting particle; measure word for objects with a handle",
    },
    "586": {
        "trans_th": "ถ้า / ในกรณีที่",
        "trans_en": "if; in the case that",
    },
    "749": {
        "trans_th": "(ลักษณนามสำหรับยานพาหนะ)",
        "trans_en": "measure word for vehicles",
    },
    "990": {
        "trans_th": "คำเติมท้ายคำนาม / ลูกชาย (ในบางคำ)",
        "trans_en": "noun suffix; son (in some words)",
    },
    "1926": {
        "trans_th": "ผู้ที่... / ผู้กระทำ",
        "trans_en": "person who; one who",
    },
    "3750": {
        "trans_th": "กลายเป็น / สำเร็จ / เปอร์เซ็นต์ (ตามบริบท)",
        "trans_en": "to become; to succeed; percent (depending on context)",
    },
    "8080": {
        "trans_th": "เส้นบาง ๆ / ปอย",
        "trans_en": "strand; wisp",
    },
    "10209": {
        "trans_th": "แล้ว / อนุภาคลงท้ายประโยคแบบวรรณคดี",
        "trans_en": "Classical Chinese sentence-final particle indicating completion",
    },
    "10443": {
        "trans_th": "ความพากเพียรเอาชนะอุปสรรค",
        "trans_en": "the Foolish Old Man Who Moves Mountains; perseverance",
        "example_zh": "他发扬愚公移山的精神，终于完成了这项工程。",
        "example_th": "เขานำจิตวิญญาณแห่งความพากเพียรมาปรับใช้ จนทำงานนี้สำเร็จในที่สุด",
        "example_en": "He persevered with the spirit of the Foolish Old Man and finally completed the project.",
    },
}


def main():
    source = Path("tmp/hsk_vocabnew_final.csv")
    output = Path("tmp/hsk_vocabnew_ready.csv")
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        if row["example_zh"].startswith("我们来学习“"):
            row["example_th"] = "มาเรียนรู้วิธีใช้คำนี้กันเถอะ คำนี้ใช้บ่อยในภาษาจีน"
            row["example_en"] = "Let's learn how to use this word. This word is common in Chinese."
        for key, value in OVERRIDES.get(row["id"], {}).items():
            row[key] = value

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"applied reviewed overrides; wrote {len(rows)} rows")


if __name__ == "__main__":
    main()
