import argparse 
from agents import safe_agent_call, research_agent, question_agent
from sqlite_database import (init_db, save_questions_to_db,
                              save_corpus_to_db, save_curriculum,
                                register_user, get_existing_corpus_id,
                                  get_active_users, get_existing_user)
from gmail_sender import send_daily_question



def creation_pipeline(topic:str, user_email:str):
    """ Handles Agents, DB Storage and user registration."""
    init_db()

    #Check if user exists
    if get_existing_user(user_email):
        print(f"User {user_email} is already registered to a curriculum.")
        print("To change their topic, run delete_user(email) first.")
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


def main():
    parser = argparse.ArgumentParser(
        description="KA -Knowledge Agent CLI",
        formatter_class= argparse.RawDescriptionHelpFormatter,
        epilog= """
            Examples:
            python main.py generate --topic "Machine Learning" --email user@gmail.com
            python main.py send 
            python main.py init-db
            python main.py delete-user --email user@gmail.com
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # generate : create curriculum and register user
    gen_parser = subparsers.add_parser("generate", help="Generate a curriculum and register a user")
    gen_parser.add_argument("--topic", required=True, help= "Topic for the curriculum (e.g. 'Machine Learning')")
    gen_parser.add_argument("--email", required=True, help="User email to register")

    #Send: daily email delivery 
    subparsers.add_parser("send", help="Send daily question to all active users")

    # init-db: initialize the database 
    subparsers.add_parser("init-db", help="Initialize the SQLite database tables")

    # delete-user: remove a user for re-registration 
    del_parser = subparsers.add_parser("delete-user", help="Delete a user and their response history")
    del_parser.add_argument("--email", required=True, help= "Email of the user to delete")

    args = parser.parse_args()

    if args.command == "generate":
        creation_pipeline(args.topic, args.email)

    elif args.command == "send":
        daily_sending()

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




