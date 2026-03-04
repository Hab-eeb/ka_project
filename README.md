### AI-Driven Learning Curriculum Generator (WIP)

A modular Python-based pipeline that transforms raw topic data into structured, multi-day learning curriculums and practice questions using the **Google Gemini (new SDK)**.

#### Project overview
This project automates the creation of educational content:

- A corpus (research) step produces a topic-specific learning corpus (Markdown).
- A question-generation step produces a structured, multi-day curriculum of MCQ-style questions.
- Outputs are persisted in **SQLite** so every generated question set can be traced back to the exact corpus version it came from.

#### Tech stack
- **Python**
- **Google Gemini** via the new SDK (`from google import genai`)
- **SQLite** for persistence (`ka_data.db`)
- **Structured output** using typed schemas (e.g., `TypedDict`) and JSON

#### Repository layout
- `main.py` — Orchestrates the workflow (init DB → run agents → save results)
- `agents.py` — Agent calls to Gemini + reliability logic (e.g., retry/backoff on 503 high-demand errors)
- `sq_database.py` — SQLite schema + insert helpers
- `ka_data.db` — Local SQLite database (generated; should be gitignored)
- `ka_data_prev.db` — Previous DB snapshot (generated; should be gitignored)
- `corpus_output_*.md` — Generated corpus versions (generated artifacts)
- `course_output*.json` — Sample structured outputs from the question agent (generated artifacts)

#### Data model (high-level)
Two primary tables:

- `corpus`
  - `id` (PK)
  - `topic`
  - `content`
  - `created_at`

- `questions`
  - `id` (PK)
  - `corpus_id` (FK → `corpus.id`)
  - `topic`
  - `day_number`
  - `difficulty`
  - `subtopic`
  - `question_text`
  - `options` (stored as JSON string)
  - `correct_answer`
  - `explanation`

This design supports multiple corpora over time (even for the same topic) while keeping question sets traceable via `corpus_id`.

#### Running locally (typical)
1. Install dependencies (example):

```bash
pip install google-genai pydantic
```

2. Configure your Gemini API key (do not commit secrets).
3. Run the pipeline:

```bash
python main.py
```

#### Notes on generated artifacts / gitignore
`.gitignore` applies only to **untracked** files. If you already committed artifacts (DBs, outputs, `__pycache__`), remove them from tracking with:

```bash
git rm -r --cached __pycache__
git rm --cached *.db
git rm --cached course_output*.json corpus_output_*.md
```

Then commit and push.

#### Roadmap
- Store user/respondent answers and scoring
- Add analytics on question quality, topic coverage, and difficulty progression
- Add email sending / daily delivery logic

#### Status
Work in progress. Core generation + persistence + traceability are in place; evaluation and delivery features are planned.
