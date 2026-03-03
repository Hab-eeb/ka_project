from agents import safe_agent_call, research_agent, question_agent
from sq_database import init_db, save_questions_to_db

def main():
    # Db setup fine to run multiple times 
    init_db()

    # Agents 
    topic = 'Generators'
    data_research = safe_agent_call(lambda : research_agent(topic))
    topic_corpus = data_research['response_text']

    data_questions = safe_agent_call(lambda: question_agent(topic, topic_corpus))
    parsed_questions = data_questions['parsed_response']

    #Store into the DB
    save_questions_to_db(parsed_questions)

    print("Questions and Corpus saved into ka_data.db")

if __name__ == "__main__":
    main()




