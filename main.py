import argparse
import os
import sqlite3
from agents import safe_agent_call, research_agent, question_agent, feedback_agent
from sqlite_database import (
    init_db,
    save_questions_to_db,
    save_corpus_to_db,
    save_curriculum,
    register_user,
    get_existing_corpus_id,
    get_active_users,
    get_existing_user,
    get_user_responses_for_feedback,
    get_user_topic,
    save_feedback_report,
    get_questions_count_for_corpus,
    get_corpus_text,
)
from gmail_sender import send_daily_question, send_feedback_email

DB_NAME = os.getenv("DB_NAME", "ka_data.db")


def creation_pipeline(topic: str, user_email: str):
    """
    Handles Agents, DB Storage and user registration.

    Has checkpoint logic:
    if corpus exists but questions failed, it skips research
    and retries question generation.
    """
    init_db()

    # Check if user exists
    if get_existing_user(user_email):
        print(f"User {user_email} is already registered to a curriculum.")
        print("To change their topic, run: python main.py delete-user --email <user_email>")
        return

    # Step 1: Corpus — check if it already exists
    corpus_id = get_existing_corpus_id(topic)
    if corpus_id:
        print(f"Corpus for '{topic}' already exists (ID:{corpus_id}). Skipping research.")
        topic_corpus = get_corpus_text(corpus_id)
    else:
        # Research Agent and saving to DB
        print(f"Starting research for: {topic}...")
        data_research = safe_agent_call(lambda: research_agent(topic))
        if not data_research:
            print("Research agent failed after max retries. Try again later.")
            return

        topic_corpus = data_research["response_text"]
        corpus_id = save_corpus_to_db(topic, topic_corpus)
        print("Corpus saved.")

    # Step 2: Questions — check if they already exist for this corpus
    q_count = get_questions_count_for_corpus(corpus_id)
    if q_count > 0:
        print(f"Questions already exist ({q_count} found). Skipping generation.")
    else:
        print("Generating Questions...")
        data_questions = safe_agent_call(lambda: question_agent(topic, topic_corpus))
        if not data_questions:
            print("Question agent failed after max retries.")
            print("Re-run the same command to retry — corpus is saved.")
            return

        parsed_questions = data_questions["parsed_response"]
        save_questions_to_db(parsed_questions, corpus_id)
        print("Questions saved.")

    # Step 3: User Registration
    curr_id = save_curriculum(topic, corpus_id)
    register_user(user_email, curr_id)
    print(f"Setup complete. {user_email} is ready for '{topic}'.")


def daily_sending():
    """Sends current day's questions to all active users."""
    print("Starting daily delivery...")

    users = get_active_users()
    if not users:
        print("No active users found.")
        return

    for user in users:
        send_daily_question(user["email"])

    print(f"Daily delivery complete. {len(users)} user(s) processed.")


def generate_feedback(user_email: str, send_email: bool = False):
    """Generates a detailed feedback report for a user who has completed their curriculum."""
    topic = get_user_topic(user_email)
    if not topic:
        print(f"No topic found for this user {user_email}.")
        return

    responses = get_user_responses_for_feedback(user_email)
    if not responses:
        print(f"No responses found for {user_email}. They may not have answered any questions yet.")
        return

    print(f"Generating feedback for {user_email} ({len(responses)} responses on '{topic}')...")

    result = safe_agent_call(lambda: feedback_agent(topic, user_email, responses))
    if result and result.get("feedback_text"):
        save_feedback_report(user_email, topic, result["feedback_text"])
        print("Feedback saved to database.")

        if send_email:
            send_feedback_email(user_email, topic, result["feedback_text"])
        else:
            print("\n" + "=" * 60)
            print(f"FEEDBACK REPORT: {user_email} — {topic}")
            print("=" * 60)
            print(result["feedback_text"])
            print("=" * 60 + "\n")
            print("Use --send to email this report to the user.")
    else:
        print("Failed to generate feedback.")


# -------------------------------------------------------------------
# Reporting helpers
# -------------------------------------------------------------------

def _get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def _status_label(is_active):
    return "active" if _safe_int(is_active) == 1 else "inactive"


def _build_users_report_query(include_email_filter=False):
    email_filter_sql = "AND u.email = ?" if include_email_filter else ""

    return f"""
    WITH question_totals AS (
        SELECT
            corpus_id,
            COUNT(*) AS total_questions
        FROM questions
        GROUP BY corpus_id
    ),
    answered_totals AS (
        SELECT
            ur.user_email,
            COUNT(DISTINCT ur.question_id) AS answered_questions
        FROM user_responses ur
        GROUP BY ur.user_email
    )
    SELECT
        u.email,
        c.topic,
        u.is_active,
        u.start_date,
        u.current_day,
        c.total_days,
        COALESCE(qt.total_questions, c.total_days, 0) AS total_questions,
        COALESCE(at.answered_questions, 0) AS answered_questions
    FROM users u
    JOIN curriculums c
        ON u.curriculum_id = c.id
    LEFT JOIN question_totals qt
        ON c.corpus_id = qt.corpus_id
    LEFT JOIN answered_totals at
        ON u.email = at.user_email
    WHERE 1=1
        {email_filter_sql}
    ORDER BY u.is_active DESC, u.email ASC
    """


def get_users_progress_report(email: str = None):
    conn = _get_db_connection()
    try:
        query = _build_users_report_query(include_email_filter=bool(email))
        params = (email,) if email else ()
        rows = conn.execute(query, params).fetchall()
        return [_format_report_row(dict(row)) for row in rows]
    finally:
        conn.close()


def _format_report_row(row: dict) -> dict:
    total_days = _safe_int(row.get("total_days"))
    current_day = _safe_int(row.get("current_day"), 1)
    total_questions = _safe_int(row.get("total_questions"))
    answered_questions = _safe_int(row.get("answered_questions"))

    unanswered_questions = max(total_questions - answered_questions, 0)

    completed_days = 0
    if total_days > 0:
        completed_days = _clamp(current_day - 1, 0, total_days)

    progress_percent = 0.0
    if total_questions > 0:
        progress_percent = round((answered_questions / total_questions) * 100, 2)
    elif total_days > 0:
        progress_percent = round((completed_days / total_days) * 100, 2)

    next_day = None
    if total_days > 0:
        next_day = _clamp(current_day, 1, total_days)

    return {
        "email": row.get("email"),
        "topic": row.get("topic"),
        "status": _status_label(row.get("is_active")),
        "start_date": row.get("start_date"),
        "current_day": current_day,
        "completed_days": completed_days,
        "total_days": total_days,
        "next_day_to_send": next_day,
        "answered_questions": answered_questions,
        "unanswered_questions": unanswered_questions,
        "total_questions": total_questions,
        "progress_percent": progress_percent,
    }


def filter_report_rows(rows, status="all"):
    normalized = (status or "all").strip().lower()
    if normalized == "all":
        return rows
    return [row for row in rows if row["status"] == normalized]


def _format_value(value):
    return "" if value is None else str(value)


def print_users_report(rows):
    if not rows:
        print("No users found for the selected filters.")
        return

    headers = [
        "email",
        "status",
        "topic",
        "current_day",
        "completed_days",
        "total_days",
        "answered_questions",
        "unanswered_questions",
        "total_questions",
        "progress_percent",
        "start_date",
    ]

    display_headers = {
        "email": "Email",
        "status": "Status",
        "topic": "Topic",
        "current_day": "Current Day",
        "completed_days": "Completed Days",
        "total_days": "Total Days",
        "answered_questions": "Answered",
        "unanswered_questions": "Unanswered",
        "total_questions": "Total Questions",
        "progress_percent": "Progress %",
        "start_date": "Start Date",
    }

    widths = {}
    for key in headers:
        widths[key] = max(
            len(display_headers[key]),
            max((len(_format_value(row.get(key))) for row in rows), default=0),
        )

    header_line = " | ".join(display_headers[key].ljust(widths[key]) for key in headers)
    separator_line = "-+-".join("-" * widths[key] for key in headers)

    print(header_line)
    print(separator_line)

    for row in rows:
        print(" | ".join(_format_value(row.get(key)).ljust(widths[key]) for key in headers))

    total_users = len(rows)
    active_users = sum(1 for row in rows if row["status"] == "active")
    inactive_users = sum(1 for row in rows if row["status"] == "inactive")

    print("\nSummary")
    print(f"Total users: {total_users}")
    print(f"Active users: {active_users}")
    print(f"Inactive users: {inactive_users}")


def show_users_report(status="all", email=None):
    rows = get_users_progress_report(email=email)
    filtered_rows = filter_report_rows(rows, status=status)
    print_users_report(filtered_rows)


# -------------------------------------------------------------------
# Parser helpers
# -------------------------------------------------------------------

def add_email_argument(parser, help_text):
    parser.add_argument("--email", required=True, help=help_text)


def add_status_filter_argument(parser):
    parser.add_argument(
        "--status",
        choices=["all", "active", "inactive"],
        default="all",
        help="Filter the report by user status",
    )


def add_optional_email_filter_argument(parser):
    parser.add_argument(
        "--email",
        required=False,
        help="Optional: report for one specific user only",
    )


def build_parser():
    parser = argparse.ArgumentParser(
        description="KA — Knowledge Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            python main.py generate --topic "Machine Learning" --email user@gmail.com
            python main.py send
            python main.py feedback --email user@gmail.com
            python main.py feedback --email user@gmail.com --send
            python main.py init-db
            python main.py delete-user --email user@gmail.com
            python main.py report-users
            python main.py report-users --status active
            python main.py report-users --status inactive
            python main.py report-users --email user@gmail.com
                    """,
                )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -- generate: create curriculum + register user --
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate a curriculum and register a user",
    )
    gen_parser.add_argument(
        "--topic",
        required=True,
        help="Topic for the curriculum (e.g. 'Machine Learning')",
    )
    add_email_argument(gen_parser, "User email to register")

    # -- send: daily email delivery --
    subparsers.add_parser(
        "send",
        help="Send daily questions to all active users",
    )

    # -- feedback: generate learning feedback for a user --
    fb_parser = subparsers.add_parser(
        "feedback",
        help="Generate a detailed feedback report for a user",
    )
    add_email_argument(fb_parser, "Email of the user to analyse")
    fb_parser.add_argument(
        "--send",
        action="store_true",
        help="Email the feedback report to the user",
    )

    # -- init-db: initialize the database --
    subparsers.add_parser(
        "init-db",
        help="Initialize the SQLite database tables",
    )

    # -- delete-user: remove a user for re-registration --
    del_parser = subparsers.add_parser(
        "delete-user",
        help="Delete a user and their response history",
    )
    add_email_argument(del_parser, "Email of the user to delete")

    # -- report-users: show active/inactive users and progress --
    report_parser = subparsers.add_parser(
        "report-users",
        help="Show user status and learning progress summary",
    )
    add_status_filter_argument(report_parser)
    add_optional_email_filter_argument(report_parser)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "generate":
        creation_pipeline(args.topic, args.email)

    elif args.command == "send":
        daily_sending()

    elif args.command == "feedback":
        generate_feedback(args.email, send_email=args.send)

    elif args.command == "init-db":
        init_db()
        print("Database initialized.")

    elif args.command == "delete-user":
        from sqlite_database import delete_user
        delete_user(args.email)

    elif args.command == "report-users":
        show_users_report(status=args.status, email=args.email)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()