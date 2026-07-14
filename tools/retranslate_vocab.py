#!/usr/bin/env python3
"""Rebuild Thai/English meanings and examples from the official Chinese CSV fields.

Uses Google Translate's public endpoint only as a translation draft. The script
keeps all official source fields unchanged and preserves the old value if a
request fails. Review the generated CSV with the audit script before replacing
the app data file.
"""

import argparse
import csv
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ENDPOINT = "https://translate.googleapis.com/translate_a/single"
SENSE_MARKER = re.compile(r"(?<=[\u3400-\u9fff])[12]$")
HAN = re.compile(r"[\u3400-\u9fff]")


def spoken_word(word):
    return SENSE_MARKER.sub("", str(word).strip())


def chunks(values, max_chars):
    current = []
    size = 0
    for value in values:
        extra = len(value) + (1 if current else 0)
        if current and size + extra > max_chars:
            yield current
            current = []
            size = 0
        current.append(value)
        size += extra
    if current:
        yield current


def translate_request(text, target, retries=4):
    params = urlencode(
        {
            "client": "gtx",
            "sl": "zh-CN",
            "tl": target,
            "dt": "t",
            "q": text,
        }
    )
    request = Request(
        f"{ENDPOINT}?{params}",
        headers={"User-Agent": "HSK-Cake-vocabulary-audit/1.0"},
    )
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            segments = payload[0] or []
            return "".join(segment[0] for segment in segments if segment and segment[0])
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(2**attempt)
    return None


def translate_values(values, target, cache, max_chars=2800, workers=2):
    unique = list(dict.fromkeys(values))
    results = {}
    pending = [
        value
        for value in unique
        if not cache.get(f"{target}|{value}")
        or HAN.search(cache.get(f"{target}|{value}", ""))
    ]

    def do_batch(batch):
        text = "\n".join(batch)
        translated = translate_request(text, target)
        if translated is None:
            return batch, None
        parts = translated.splitlines()
        if len(parts) != len(batch):
            # Some long inputs lose line boundaries. Retry one-by-one.
            parts = [translate_request(item, target) for item in batch]
        return batch, parts

    batches = list(chunks(pending, max_chars))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(do_batch, batch) for batch in batches]
        for index, future in enumerate(as_completed(futures), start=1):
            batch, translated = future.result()
            if translated is None:
                continue
            for source, value in zip(batch, translated):
                if value:
                    cache[f"{target}|{source}"] = value.strip()
            if index % 10 == 0 or index == len(futures):
                print(f"{target}: {index}/{len(futures)} batches", flush=True)

    for value in unique:
        results[value] = cache.get(f"{target}|{value}")
    return results


MANUAL_OVERRIDES = {
    "1": {"trans_th": "รัก / ชอบ"},
    "45": {"pos_zh": "形、代、（动、数、副）"},
    "46": {"pos_zh": "代", "pos_en": "pron.", "pos_th": "คำสรรพนาม"},
    "5438": {
        "trans_th": "จุดอ่อน / หลักฐานที่ใช้เล่นงานผู้อื่น",
        "example_zh": "他抓住了我的把柄。",
        "example_th": "เขาได้หลักฐานที่สามารถใช้เล่นงานฉัน",
        "example_en": "He found something he could use against me.",
    },
    "5439": {
        "trans_th": "อยาก...ใจจะขาด / ปรารถนาอย่างยิ่ง",
        "example_zh": "我巴不得马上见到他。",
        "example_th": "ฉันอยากเจอเขาเดี๋ยวนี้ใจจะขาด",
        "example_en": "I cannot wait to see him.",
    },
    "5440": {
        "trans_th": "แปดส่วนในสิบ / มีแนวโน้มสูงว่า",
        "example_zh": "这件事八成能办成。",
        "example_th": "เรื่องนี้มีแนวโน้มสูงว่าจะสำเร็จ",
        "example_en": "This will most likely succeed.",
    },
    "5441": {"trans_th": "เอาแต่ใจ / ใช้อำนาจบาตรใหญ่"},
    "5442": {
        "trans_th": "นัดหยุดงาน",
        "example_zh": "工人决定罢工。",
        "example_th": "คนงานตัดสินใจนัดหยุดงาน",
        "example_en": "The workers decided to go on strike.",
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cache", type=Path, default=Path("tmp/translation_cache.json"))
    args = parser.parse_args()

    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    cache = {}
    if args.cache.exists():
        cache = json.loads(args.cache.read_text(encoding="utf-8"))

    words = [spoken_word(row["word"]) for row in rows]
    examples = [row["example_zh"] for row in rows]
    thai_words = translate_values(words, "th", cache, max_chars=2800)
    english_words = translate_values(words, "en", cache, max_chars=2800)
    thai_examples = translate_values(examples, "th", cache, max_chars=2600)
    english_examples = translate_values(examples, "en", cache, max_chars=2600)

    for row in rows:
        source_word = spoken_word(row["word"])
        row["trans_th"] = thai_words.get(source_word) or row["trans_th"]
        row["trans_en"] = english_words.get(source_word) or row["trans_en"]
        row["example_th"] = thai_examples.get(row["example_zh"]) or row["example_th"]
        row["example_en"] = english_examples.get(row["example_zh"]) or row["example_en"]
        for key, value in MANUAL_OVERRIDES.get(str(row["id"]), {}).items():
            row[key] = value

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    args.cache.parent.mkdir(parents=True, exist_ok=True)
    args.cache.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
