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





if __name__ == "__main__":
    #Setup new user/ topic
    creation_pipeline("Teaching", "agbajeh8@gmail.com")

    #Run the daily send for everyone
    daily_sending()




