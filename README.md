### 🧠 Knowledge Agent (KA)

## An AI-Driven Learning Curriculum Generator (WIP)

A modular Python-based pipeline that transforms raw topic data into structured, multi-day learning curriculums and practice questions using the **Google Gemini (new SDK)** — with **SQLite persistence**, **daily email delivery**, and a **Flask endpoint** for answering questions.

#### 🚀 Project overview

This project automates the creation + delivery of educational content:

- A corpus (research) agent produces a topic-specific learning corpus.
- A question-generation agent produces a structured, multi-day curriculum of MCQ-style questions.
- Outputs are persisted in **SQLite** so every question set can be traced back to the exact corpus version it came from.
- A daily delivery script fetches the next “Day N” question from the DB (no LLM call) and emails it to the user.
- Users answer via email links that hit a Flask `/check` endpoint, which validates + stores responses.

#### 🌟 Key Features

- **Structured Output**: Uses Gemini’s response schema to ensure the model returns valid, parsable JSON matching the project schema.
- **Resilient API Calls**: Implements a “Safe Call” wrapper with exponential backoff to handle timeouts and server-side spikes.
- **Relational Persistence**: Data is normalized into SQLite (traceability via `corpus_id`).
- **Daily Delivery (No LLM)**: Daily send selects the appropriate “Day N” question from the database.
- **Answer Tracking**: A Flask endpoint records answers and prevents duplicate attempts per user per question.

#### 🛠️ Tech stack

- **Python**
- **Google Gemini** via the new SDK (`from google import genai`)
- **SQLite** for persistence (`ka_data.db`)
- **Flask** (answer submission + result page)
- **SMTP (Gmail)** for sending daily questions
- **Structured output** using typed schemas (e.g., `TypedDict`) and JSON

#### 📂 Repository layout

- `main.py` — Orchestrates the workflow:
  - init DB
  - generate corpus + questions (if needed)
  - register users
  - run daily delivery loop (send to active users)
- `agents.py` — Agent calls to Gemini + reliability logic (retry/backoff)
- `sqlite_database.py` — SQLite schema + DB helpers (users, curriculum, “Day N” fetching)
- `gmail_sender.py` — Builds + sends daily question emails (fetch → send → increment day)
- `app.py` — Flask app: `/check?q_id=...&ans=...&user=...` validates answer and saves response
- `templates/` — HTML templates (e.g. `result.html`)
- `ka_data.db` — Local SQLite database (generated; should be gitignored)

#### 📊 Data model (high-level)

Primary tables:

- `corpus`
  - `id` (PK)
  - `topic` (UNIQUE)
  - `corpus_text`
  - `created_at`

- `questions`
  - `id` (PK)
  - `corpus_id` (FK → `corpus.id`)
  - `topic`
  - `day_number`
  - `difficulty`
  - `subtopic`
  - `question_text`
  - `options` (JSON string)
  - `correct_answer`
  - `explanation`
  - UNIQUE constraint to avoid duplicates per corpus/day/question

- `curriculums`
  - `id` (PK)
  - `topic` (UNIQUE)
  - `corpus_id`
  - `total_days`

- `users`
  - `id` (PK)
  - `email` (UNIQUE)
  - `curriculum_id`
  - `start_date`
  - `current_day`
  - `is_active`

- `user_responses`
  - `id` (PK)
  - `question_id` (FK → `questions.id`)
  - `user_email`
  - `selected_option`
  - `is_correct`
  - UNIQUE `(question_id, user_email)` to prevent duplicate attempts

This design supports:
- traceable question sets (via `corpus_id`)
- user progress tracking (via `current_day`)
- answer tracking + analytics readiness

#### ⚙️ How it works (end-to-end)

1. **Generate curriculum (LLM call)**
   - `research_agent(topic)` → corpus text
   - `question_agent(topic, corpus)` → structured multi-day questions
   - Both are saved into SQLite (linked by `corpus_id`).

2. **Register user**
   - User is linked to a curriculum (`users.curriculum_id`) and starts at `current_day = 1`.

3. **Daily delivery (no LLM call)**
   - For each active user, fetch the question for their `current_day`
   - Email it with A/B/C/D links

4. **User answers via email link**
   - Link hits Flask `/check`
   - App checks correctness, stores attempt, and renders result + explanation

#### 🔐 Environment variables

Create a `.env` file (do **not** commit secrets):

- `GEMINI_API_KEY` — Gemini API key
- `SENDER_EMAIL` — Gmail address used to send emails
- `GMAIL_PASSWORD` — Gmail **App Password** (recommended), not your normal password
- `BASE_URL` — Base URL for answer links (should include `/check`), e.g. `http://127.0.0.1:5000/check`
- `DB_NAME` — SQLite DB filename/path (e.g. `ka_data.db`)

Example:

```bash
GEMINI_API_KEY=your_key_here
SENDER_EMAIL=you@gmail.com
GMAIL_PASSWORD=your_app_password
BASE_URL=http://127.0.0.1:5000/check
DB_NAME=ka_data.db 

```

#### Running locally (typical)

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

2. Install dependencies:

```bash
pip install google-genai pydantic flask python-dotenv
```

3. Set environment variables in `.env`.

4. Generate curriculum + register a user  
   In `main.py`, uncomment `creation_pipeline(topic, email)` and run:

```bash
python main.py
```

5. Run the Flask app (answer endpoint):

```bash
python app.py
```

6. Run the daily send  
   In `main.py`, comment out `creation_pipeline` and ensure `daily_sending()` is active, then:

```bash
python main.py
```

#### ✅ MVP behavior / constraints

- **One user per topic/curriculum**: If a user email is already registered, the generation/register flow stops early — preventing accidental re-generation and unnecessary LLM usage.
- Users are automatically marked inactive once they reach the end of their curriculum (`total_days`).

#### 🧹 Cleanup utilities (DB)

Helper functions are available in `sqlite_database.py` to delete a user and their response history, allowing re-registration with a new topic during testing.

#### Roadmap

- Production deployment (Render/Railway) + scheduler automation
- Better html formatting (responsive design)
- User learning analytics
- Admin UI to manage users/topics and resend days
- Multiple questions per day + spaced repetition

#### Status

Work in progress. Core generation + persistence + traceability are in place; daily delivery and answer tracking are implemented and working locally. Deployment + automation are next.