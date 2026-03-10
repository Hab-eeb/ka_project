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
            topic TEXT UNIQUE,
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
            FOREIGN KEY (corpus_id) REFERENCES corpus (id),
            UNIQUE (corpus_id,day_number, question_text)
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

    #Table for Curriculum link between user, topic and corpus

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS curriculums (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   topic TEXT UNIQUE NOT NULL, 
                   corpus_id INTEGER NOT NULL,
                   total_days INTEGER DEFAULT 30,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY (corpus_id) REFERENCES corpus (id) 
                   )
    
    ''')

    #Table for user - ensuring unique list of users 

    cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   email TEXT UNIQUE NOT NULL,
                   curriculum_id INTEGER NOT NULL,
                   start_date DATE DEFAULT (date('now')),
                   current_day INTEGER DEFAULT 1,
                   is_active INTEGER DEFAULT 1, 
                   FOREIGN KEY (curriculum_id) REFERENCES curriculums (id)  
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

def save_curriculum(topic: str, corpus_id:int, total_days: int= 30) -> int:
    """ Creates a curriculum linking topic, corpus """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
            INSERT OR IGNORE INTO curriculums (topic, corpus_id, total_days)
                 VALUES (?,?,?)
                ''', (topic, corpus_id,total_days)
                 )
    
    if cursor.lastrowid:
        curriculum_id = cursor.lastrowid 
    else:
        #Fetch the id whether its present incase of duplicates
        curriculum_id = cursor.execute('''
                SELECT id FROM curriculums WHERE topic = ? 
                ''', (topic,)
        ).fetchone()[0]

    conn.commit()
    conn.close()
    return curriculum_id

def register_user(email: str, curriculum_id: int):
    """ Registers a new user to a curriculum """

    conn = sqlite3.connect(DB_NAME)
    conn.execute('''
            INSERT OR IGNORE INTO users (email,curriculum_id)
            VALUES (?,?)
    ''', (email, curriculum_id))

    conn.commit()
    conn.close()

    print(f"User {email} registered to the curriculum {curriculum_id}")

def get_active_users():
    """Returns a list of all active users and their current day"""

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    users = conn.execute('''
            SELECT email, current_day FROM users WHERE is_active = 1
            ''').fetchall()
    conn.close()
    return [dict(u) for u in users]

def get_question_for_user_day(email:str):
    """ Fetches the question for the user's current day based on their curriculum"""

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT q.* 
        FROM questions q
        JOIN curriculums c ON q.corpus_id = c.corpus_id
        JOIN users u ON u.curriculum_id = c.id
        WHERE u.email = ? AND q.day_number = u.current_day
        LIMIT 1
        """
    question = conn.execute(query,(email,)).fetchone()
    conn.close()
    return dict(question) if question else None

def increment_user_day(email:str):
    """ Moves the user forward to the next day in their curriculum, deactivates if curriculum is complete"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    #Fetch the current day and total days 
    row = conn.execute('''
            SELECT u.current_day, c.total_days
            FROM users u
            JOIN curriculums c ON u.curriculum_id = c.id
            WHERE u.email = ?
        ''', (email,)
        ).fetchone()
    
    if not row:
        conn.close()
        print(f"User {email} not found")
        return 
    
    if row['current_day'] >= row['total_days']:

        #They just completed the last day - deactivate 
        conn.execute('''
                UPDATE users SET is_active = 0 WHERE email = ?
            ''', (email,))
        conn.commit()
        conn.close()
        print(f"{email} has completed the curriculum! Marked as inactive.")

    else:
        conn.execute('''
                UPDATE users SET current_day = current_day + 1 WHERE email = ?
            ''', (email,)
                    )
        
        conn.commit()
        conn.close()
        print(f"{email} moved to day {row['current_day'] + 1}")


def get_existing_corpus_id(topic:str):
    """ Checks if a topic already exists and returns its corpus id"""

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    row = conn.execute('''
            SELECT id FROM corpus WHERE topic = ?
        ''', (topic,)
                       ).fetchone()
    conn.close()

    return row[0] if row else None


def delete_user(email: str):
    """ Removes a user and their response history from the database. """
    conn = sqlite3.connect(DB_NAME)
    conn.execute('DELETE FROM user_responses WHERE user_email = ?', (email,))
    conn.execute('DELETE FROM users WHERE email = ?', (email,))
    conn.commit()
    conn.close()
    print(f"🗑️ User {email} deleted.")

def get_existing_user(email:str):
    """ Checks if a topic already exists and returns its corpus id"""

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    row = conn.execute('''
            SELECT id FROM users WHERE email = ?
        ''', (email,)
                       ).fetchone()
    conn.close()

    if row :
        return True
    else :
        return False





if __name__ == "__main__":
    init_db()
    print("DB initialized")

    #reset_all_user_responses("agbajeh8@gmail.com") #Uncomment when needed
    #delete_user("agbajeh8@gmail.com") #Uncomment when needed



