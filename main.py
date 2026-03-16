import argparse
from agents import safe_agent_call, research_agent, question_agent, feedback_agent
from sqlite_database import (init_db, save_questions_to_db,
                              save_corpus_to_db, save_curriculum,
                                register_user, get_existing_corpus_id,
                                  get_active_users, get_existing_user,
                                  get_user_responses_for_feedback,
                                  get_user_topic, save_feedback_report)
from gmail_sender import send_daily_question, send_feedback_email



def creation_pipeline(topic:str, user_email:str):
    """ Handles Agents, DB Storage and user registration."""
    init_db()

    #Check if user exists
    if get_existing_user(user_email):
        print(f"User {user_email} is already registered to a curriculum.")
        print("To change their topic, run: python main.py delete-user --email <email>")
        return

    #Check if topic exists 
    corpus_id = get_existing_corpus_id(topic)

    if corpus_id:
        print(f" Topic already exists in DB (ID:{corpus_id}). Skipping AI generation")
    else:

        # Research Agent and saving to DB
        print(f"Starting research for : {topic}...")
        data_research = safe_agent_call(lambda : research_agent(topic))
        topic_corpus = data_research['response_text']
        corpus_id = save_corpus_to_db(topic,topic_corpus)
        print("Corpus saved")

        #Question Agent and saving to DB
        print("Generating Questions... ")
        data_questions = safe_agent_call(lambda: question_agent(topic, topic_corpus))
        parsed_questions = data_questions['parsed_response']
        save_questions_to_db(parsed_questions,corpus_id) 
        print("Questions saved")
    
    #User Registration 
    curr_id = save_curriculum(topic, corpus_id)
    register_user(user_email,curr_id)
    print(f" Setup complete. {user_email} is ready for '{topic}'.")


def daily_sending():
    """ Sends current days questions to all active users """
    print(" Starting daily Delivery ")

    users = get_active_users()

    if not users:
        print("No active users found.")
        return
    
    for user in users:
        send_daily_question(user['email'])

    print(f"Daily Delivery complete. {len(users)} user(s) processed")


def generate_feedback(user_email: str, send_email: bool = False):
    """Generates a detailed feedback report for a user who has completed their curriculum."""
    
    # Get user's topic
    topic = get_user_topic(user_email)
    if not topic:
        print(f"No topic found for this user {user_email}.")
        return
    
    # Get all their responses
    responses = get_user_responses_for_feedback(user_email)
    if not responses:
        print(f"No responses found for {user_email}. They may not have answered any questions yet.")
        return
    
    print(f"Generating feedback for {user_email} ({len(responses)} responses on '{topic}')...")
    
    # Call the feedback agent
    result = safe_agent_call(lambda: feedback_agent(topic, user_email, responses))
    
    if result and result.get('feedback_text'):
        # Save to database
        save_feedback_report(user_email, topic, result['feedback_text'])
        print("Feedback saved to database.")
        
        if send_email:
            send_feedback_email(user_email, topic, result['feedback_text'])
        else:
            # Print to console
            print("\n" + "="*60)
            print(f"FEEDBACK REPORT: {user_email} — {topic}")
            print("="*60)
            print(result['feedback_text'])
            print("="*60 + "\n")
            print("Use --send to email this report to the user.")
    else:
        print("Failed to generate feedback.")


def main():
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
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -- generate: create curriculum + register user --
    gen_parser = subparsers.add_parser("generate", help="Generate a curriculum and register a user")
    gen_parser.add_argument("--topic", required=True, help="Topic for the curriculum (e.g. 'Machine Learning')")
    gen_parser.add_argument("--email", required=True, help="User email to register")

    # -- send: daily email delivery --
    subparsers.add_parser("send", help="Send daily questions to all active users")

    # -- feedback: generate learning feedback for a user --
    fb_parser = subparsers.add_parser("feedback", help="Generate a detailed feedback report for a user")
    fb_parser.add_argument("--email", required=True, help="Email of the user to analyse")
    fb_parser.add_argument("--send", action="store_true", help="Email the feedback report to the user")

    # -- init-db: initialize the database --
    subparsers.add_parser("init-db", help="Initialize the SQLite database tables")

    # -- delete-user: remove a user for re-registration --
    del_parser = subparsers.add_parser("delete-user", help="Delete a user and their response history")
    del_parser.add_argument("--email", required=True, help="Email of the user to delete")

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

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
