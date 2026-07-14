# HSK Cake

Streamlit flashcards and quizzes for the official 11,000-word HSK syllabus.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

Without Streamlit secrets, progress uses local runtime storage. For shared
History and Leaderboard, copy `secrets.toml.example` into Streamlit Community
Cloud App settings > Secrets, replace every placeholder with a newly created
Google service-account key, and share the target Sheet with its `client_email`.
The app creates/uses worksheet `hsk_progress` automatically.

Leaderboard ranking uses total correct answers, then accuracy and attempts as
tie-breakers. Guest is never listed. Named users may hide their own name and
score from everyone else.

## Security

Never commit `.streamlit/secrets.toml`, JSON service-account keys, or private
keys. If a key was committed previously, delete/disable it in Google Cloud and
create a new key; removing it from the latest Git commit is not sufficient.

## Vocabulary audit

See `VOCAB_AUDIT.md`. To compare the CSV source fields with the official PDF:

```bash
python tools/audit_vocab_against_pdf.py \
  hsk_vocabnew_fixed.csv \
  '../新版HSK考试大纲（词汇、汉字、语法）.pdf'
```
