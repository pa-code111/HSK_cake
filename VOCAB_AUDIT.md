# HSK vocabulary audit

Checked on 2026-07-14 against `新版HSK考试大纲（词汇、汉字、语法）.pdf`
(2025-11 release, effective 2026-07).

## Verified

- CSV rows: 11,000
- Official PDF vocabulary rows extracted: 11,000
- IDs: complete sequence 1-11,000; no duplicates
- Official `id`, HSK level, Chinese word, and pinyin mismatches: 0
- Non-empty official Chinese part-of-speech mismatches: 0
- Empty cells in the 12 CSV columns: 0
- Thai translations/examples containing Chinese characters: 0

Corrections applied during this audit:

- IDs 45-46: repaired a PDF line-wrap error that split the part-of-speech text
- ID 327: restored official sense marker `打1`
- IDs 1 and 5438-5442: corrected clear Thai/English meaning or example errors

## Important limitation

The PDF is authoritative only for ID, level, Chinese word, pinyin, and Chinese
part of speech. It does not provide Thai/English translations or examples.
Therefore, structural agreement with the PDF does not prove translation quality.

- 374 official rows have no part of speech in the PDF; the CSV contains inferred
  categories for these rows.
- 58 Chinese spellings repeat because the official syllabus separates different
  readings or senses. These are not duplicate IDs.
- 81 Chinese examples still use the pattern `请给我一...`; some are valid, but
  many need contextual rewriting.
- 20 rows use the generic example `这个词是语法词。` and should receive real
  usage examples.
- 138 rows share a Chinese example with another row. Shared sentences are not
  automatically wrong, but they need a semantic review.

## Recommended translation workflow

1. Keep the five official source fields locked: ID, level, word, pinyin, POS.
2. Add `translation_status`, `reviewer`, and `reviewed_at` columns.
3. Review HSK 1-3 first, then words that appear in Quiz, then HSK 4-6 and 7-9.
4. Require each example to contain the target word naturally and match both
   Thai and English translations.
5. Run `tools/audit_vocab_against_pdf.py` after every batch to prevent source
   fields from drifting.

Example:

```bash
python tools/audit_vocab_against_pdf.py \
  hsk_vocabnew_fixed.csv \
  '../新版HSK考试大纲（词汇、汉字、语法）.pdf'
```
