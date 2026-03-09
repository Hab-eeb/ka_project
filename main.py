from agents import safe_agent_call, research_agent, question_agent
from ka_project.sqlite_database import init_db, save_questions_to_db, save_corpus_to_db, save_curriculum, register_user

def main():
    # Db setup 
    init_db() #fine to run multiple times 

    print("Db instatiated, Agents starting...")

    # Research Agent
    topic = 'Generators'
    data_research = safe_agent_call(lambda : research_agent(topic))
    topic_corpus = data_research['response_text']

    #Store corpus into the DB
    corpus_id = save_corpus_to_db(topic,topic_corpus)

    print("Research agent done and corpus generated and saved to corpus table, Question Agent starting...")

    # Question Agent
    data_questions = safe_agent_call(lambda: question_agent(topic, topic_corpus))
    parsed_questions = data_questions['parsed_response']

    print("Question agent done and questions generated and saved to questions table")

    #Store questions into the DB

    save_questions_to_db(parsed_questions,corpus_id) 

    print("Questions and Corpus saved into ka_data.db")

    # Register Curriculum per topic 
    curriculum_id = save_curriculum(topic, corpus_id, total_days=30)

    #Register user per curriculum 
    register_user('agbajeh8@gmail.com',curriculum_id)
    

if __name__ == "__main__":
    main()




