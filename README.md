🧠 AI-Driven Learning Curriculum Generator (WIP)
A modular Python-based pipeline that transforms raw topic data into structured, multi-day learning curriculums and practice questions using the Google Gemini 2.0 SDK.

🚀 Project Overview
This project automates the creation of educational content. It uses a "Research Agent" to build a knowledge corpus and a "Question Agent" to generate structured assessments. All data is persisted in a relational database to ensure traceability between the source material and the generated questions.

🛠️ Tech Stack
Language: Python 3.10+
AI Model: Google Gemini (gemini-2.0-flash)
SDK: New Google Gen AI Python SDK (from google import genai)
Database: SQLite (Relational storage for corpus and Q&A pairs)
Data Validation: Pydantic / TypedDict for structured JSON enforcement
📂 File Structure
main.py: The central orchestrator. Handles the execution flow: initializing the database, triggering agents, and saving outputs.
agents.py: Contains the logic for AI agents. Includes custom retry logic to handle 503 Service Unavailable errors during high-demand periods.
sq_database.py: The data persistence layer. Manages SQLite schema creation and relational inserts.
ka_data.db: The local SQLite database (contains the generated curriculum and questions).

📊 Database Architecture
The project uses a Foreign Key relationship to link questions back to their specific source corpus. This allows for versioning—if the corpus is updated, we can track exactly which questions were generated from which version.

corpus Table: Stores id, topic, content, and timestamp.
questions Table: Stores id, corpus_id (FK), day_number, difficulty, question_text, options (JSON-serialized), correct_answer, and explanation_gist.
🌟 Key Features
Structured Output: Uses Gemini’s response_schema to ensure the AI always returns valid, parsable JSON matching the project's TopicSchema.
Resilient API Calls: Implements a "Safe Call" wrapper with exponential backoff to handle API timeouts and server-side spikes.
Relational Persistence: Instead of loose JSON files, data is normalized into SQLite, making it ready for future analytics or a web frontend.
🛠️ Setup & Usage
Install Dependencies:
bash
Copy
pip install google-genai pydantic
Configure API Key:
Ensure your Gemini API key is available in your environment.
Run the Pipeline:
bash
Copy
python main.py
📈 Roadmap
 Automated Delivery: Integration with email services to send "Daily Questions" to learners.
 Respondent Module: Tables to store user answers and calculate scores.
 Analytics Agent: An agent to review the database and identify gaps in the generated curriculum.
Note: This project is currently in active development. Generated artifacts like .db and __pycache__ are excluded from version control via .gitignore.