### 🧠 Knowledge Agent (KA)

## An AI-Driven Learning Curriculum Generator

A modular Python-based pipeline that transforms raw topic data into structured, multi-day learning curriculums and practice questions using **Google Gemini (new SDK)** — with **Google Search grounding** for up-to-date content, **SQLite persistence**, **daily email delivery**, a **Flask endpoint** for answering questions, and **AI-powered feedback analysis** after curriculum completion.

**🔴 Live & Deployed** on PythonAnywhere with automated daily delivery.

**👉 [Sign up here](https://forms.gle/kvrm7mGFfEiqf5Gf9) to try it — pick any topic and start receiving daily questions.**

---

#### 🚀 Project Overview

This project automates the creation + delivery of educational content:

- A **research agent** (with Google Search grounding) produces a topic-specific learning corpus using the latest available information.
- A **question-generation agent** produces a structured, multi-day curriculum of MCQ-style questions.
- Outputs are persisted in **SQLite** so every question set can be traced back to the exact corpus version it came from.
- A daily delivery script fetches the next "Day N" question from the DB (no LLM call) and emails it to the user.
- Users answer via email links that hit a Flask `/check` endpoint, which validates + stores responses.
- After completing 30 days, a **feedback agent** analyses the user's entire response history and generates a personalised learning report.

#### 🌟 Key Features

- **Search-Grounded Research**: The research agent uses Google Search to ensure the learning corpus reflects the latest information, not just the LLM's training data.
- **Structured Output**: Uses Gemini's response schema to ensure the model returns valid, parsable JSON matching the project schema.
- **Index-Based Answer Validation**: Correct answers are stored as option indices (0-3), eliminating text mismatch issues from LLM generation.
- **Resilient API Calls**: Implements a "Safe Call" wrapper with exponential backoff to handle timeouts and server-side spikes.
- **Relational Persistence**: Data is normalized into SQLite (traceability via `corpus_id`).
- **Daily Delivery (No LLM)**: Daily send selects the appropriate "Day N" question from the database.
- **Answer Tracking**: A Flask endpoint records answers and prevents duplicate attempts per user per question.
- **AI-Powered Feedback**: After completing a curriculum, users receive a detailed analysis of their strengths, weaknesses, and personalised next steps.

#### 🛠️ Tech Stack

- **Python**
- **Google Gemini** via the new SDK (`from google import genai`)
- **Google Search** grounding for up-to-date research
- **SQLite** for persistence (`ka_data.db`)
- **Flask** (answer submission + result page)
- **SMTP (Gmail)** for sending daily questions
- **Structured output** using typed schemas (e.g., `TypedDict`) and JSON
- **PythonAnywhere** for hosting + scheduled task automation

#### 📂 Repository Layout

- `main.py` — CLI entrypoint for all operations:
  - `generate` — Create a curriculum and register a user
  - `send` — Send daily questions to all active users
  - `feedback` — Generate a feedback report for a user
  - `init-db` — Initialize the database
  - `delete-user` — Remove a user for re-registration
- `agents.py` — Agent calls to Gemini: research (with search), question generation, and feedback analysis
- `sqlite_database.py` — SQLite schema + DB helpers (users, curriculum, responses, feedback)
- `gmail_sender.py` — Builds + sends daily question emails (fetch → send → increment day)
- `app.py` — Flask app: `/check?q_id=...&ans=...&user=...` validates answer and saves response
- `templates/` — HTML templates (e.g. `result.html`)

#### 📊 Data Model (high-level)

Primary tables:

- `corpus` — stores the generated learning material per topic (linked by `corpus_id`)
- `questions` — 30 days of questions with options, `correct_answer_index`, difficulty, explanations
- `curriculums` — links a topic to its corpus with total day count
- `users` — tracks email, curriculum assignment, current day, and active status
- `user_responses` — stores each answer attempt with correctness (unique per user per question)
- `feedback_reports` — stores AI-generated feedback after curriculum completion

This design supports:
- Traceable question sets (via `corpus_id`)
- User progress tracking (via `current_day`)
- Answer tracking + analytics readiness
- Personalised feedback generation

#### ⚙️ How It Works (end-to-end)

1. **Generate curriculum (LLM + Search)**
   - `research_agent(topic)` → searches the web + generates corpus text
   - `question_agent(topic, corpus)` → structured 30-day question set
   - Both are saved into SQLite (linked by `corpus_id`).

2. **Register user**
   - User is linked to a curriculum (`users.curriculum_id`) and starts at `current_day = 1`.

3. **Daily delivery (no LLM call)**
   - For each active user, fetch the question for their `current_day`
   - Email it with A/B/C/D links

4. **User answers via email link**
   - Link hits Flask `/check`
   - App checks correctness using index comparison, stores attempt, and renders result + explanation

5. **Feedback (after completion)**
   - After 30 days, run the feedback command to generate a detailed analysis
   - The feedback agent reviews all responses and produces a personalised learning report

#### 🔐 Environment Variables

Create a `.env` file (do **not** commit secrets). See `.env.example` for the template:

- `GEMINI_API_KEY` — Gemini API key
- `SENDER_EMAIL` — Gmail address used to send emails
- `GMAIL_PASSWORD` — Gmail **App Password** (recommended), not your normal password
- `BASE_URL` — Base URL for answer links (e.g. `https://yourusername.pythonanywhere.com/check`)
- `DB_NAME` — SQLite DB path (use absolute path in production)

#### Running Locally

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

4. Initialize the database:

```bash
python main.py init-db
```

5. Generate a curriculum and register a user:

```bash
python main.py generate --topic "Machine Learning" --email user@gmail.com
```

6. Run the Flask app (answer endpoint):

```bash
python app.py
```

7. Send daily questions to all active users:

```bash
python main.py send
```

8. Generate feedback for a user (after they've answered questions):

```bash
python main.py feedback --email user@gmail.com
```

9. Delete a user (for re-registration with a new topic):

```bash
python main.py delete-user --email user@gmail.com
```

#### ✅ MVP Behavior / Constraints

- **One user per topic/curriculum**: If a user email is already registered, the generation/register flow stops early — preventing accidental re-generation and unnecessary LLM usage.
- Users are automatically marked inactive once they reach the end of their curriculum (`total_days`).
- Feedback can be generated at any point but is most useful after curriculum completion.

#### 🧹 Cleanup Utilities (DB)

Use the CLI to delete a user and their response history, allowing re-registration with a new topic:

```bash
python main.py delete-user --email user@gmail.com
```

Additional helper functions are available in `sqlite_database.py` for resetting individual or all responses during testing.

#### Agents

| Agent | Model | Purpose | Tools |
|-------|-------|---------|-------|
| Research Agent | `gemini-2.5-flash` | Generates structured learning corpus | Google Search |
| Question Agent | `gemini-2.5-flash-lite` | Produces 30-day question curriculum | Structured output schema |
| Feedback Agent | `gemini-2.5-flash` | Analyses responses and generates learning report | — |

#### Status

Live and deployed. Core generation + persistence + traceability + daily delivery + answer tracking + feedback analysis are all implemented and working in production.
