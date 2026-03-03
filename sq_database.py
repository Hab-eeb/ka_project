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
            corpus_text TEXT
                   )
    
    ''')

    #Table for the questions by day
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions(
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            topic TEXT,
            day_number INTEGER,
            difficulty TEXT,
            subtopic TEXT,
            question_text TEXT,
            options TEXT, --Stored as JSON string
            correct_answer TEXT,
            explanation TEXT 
                   )
    ''')
    conn.commit()
    conn.close()

def save_questions_to_db(question_data: dict):
    """ Saves the entire Question Schema into the database. """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    topic_name = question_data['topic']

    for day in question_data['days']:
        day_num = day['day_number']
        diff_level = day['difficulty_level']

        for q in day['questions']:
            cursor.execute('''
            INSERT INTO questions 
            (topic, day_number, difficulty, subtopic, question_text, options, correct_answer, explanation)
            VALUES (?,?,?,?,?,?,?,?) ''', 
            ( 
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




