import sqlite3
import json 

DB_NAME = 'ka_data.db'

def init_db():
    """ Run this once to create tables."""

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    #Table for raw corpus 
    cursor.execute( '''
        CREATE TABLE IF NOT EXISTS corpus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            corpus_text TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP       
                   )
    
    ''')

    #Table for the questions by day
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions(
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            corpus_id INTEGER, --Link to corpus table
            topic TEXT,
            day_number INTEGER,
            difficulty TEXT,
            subtopic TEXT,
            question_text TEXT,
            options TEXT, --Stored as JSON string
            correct_answer TEXT,
            explanation TEXT, 
            FOREIGN KEY (corpus_id) REFERENCES corpus (id)
                   )
    ''')

    #Table for user responses 
    # cursor.execute("DROP TABLE IF EXISTS user_responses") #for making changes only run once when needed
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_responses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER, --Link to question
            user_email TEXT,
            selected_option TEXT,
            is_correct BOOLEAN,
            responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            FOREIGN KEY (question_id) REFERENCES questions (id) ,
            UNIQUE (question_id,user_email)                          
                   )
    ''')




    conn.commit()
    conn.close()

def save_corpus_to_db(topic: str, corpus: str) -> int:
    """ Saves the corpus and topic and returns the rowid to link with question data"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
       INSERT INTO corpus (topic, corpus_text) VALUES (?,?) ''',
       (topic,corpus)
       )
    last_id = cursor.lastrowid  # Gets the id of the row just inserted

    conn.commit()
    conn.close()

    return last_id


def save_questions_to_db(question_data: dict, corpus_id: int):
    """ Saves the entire Question Schema into the database, linked to the corpus"""

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    topic_name = question_data['topic']

    for day in question_data['days']:
        day_num = day['day_number']
        diff_level = day['difficulty_level']

        for q in day['questions']:
            cursor.execute('''
            INSERT INTO questions 
            (corpus_id, topic, day_number, difficulty, subtopic, question_text, options, correct_answer, explanation)
            VALUES (?,?,?,?,?,?,?,?,?) ''', 
            ( 
                corpus_id, # Foreign Key
                topic_name,
                day_num,
                diff_level,
                q['subtopic'],
                q['question_text'],
                json.dumps(q['options']), # convert list to json string for storage
                q['correct_answer'],
                q['explanation_gist']
            )
                           )
    conn.commit()
    conn.close()

def save_user_responses(question_id: int, email: str, users_answer:str, is_correct: bool):
    """Saves the users response into the db"""

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO user_response (question_id,user_email, selected_option, is_correct)
        VALUES (?,?,?,?)''', 
        (question_id,email,users_answer,is_correct)
    )

    conn.commit()
    conn.close()

def reset_user_response(email:str, question_id: int):
    """ Deletes a user's response for a specific question, allowing them to answer again"""

    conn = sqlite3.connect(DB_NAME)
    conn.execute('''
        DELETE FROM user_responses WHERE user_email = ? AND question_id = ?
    ''', (email, question_id)
    )
    conn.commit()
    conn.close()
    print(f"Reset: {email} can now re-answer question {question_id}")

def reset_all_user_responses(email:str):
    """ Deletes ALL responses for a user, resetting their entire history. """
    conn= sqlite3.connect(DB_NAME)
    conn.execute('''
                DELETE FROM user_responses WHERE user_email = ?
                ''', (email,)
                 )
    conn.commit()
    conn.close()

    print(f"Reset: All responses cleared for {email}")



if __name__ == "__main__":
    init_db()
    print("DB initialized")

    reset_all_user_responses("agbajeh8@gmail.com") #Uncomment when needed



