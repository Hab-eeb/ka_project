from flask import Flask, request, render_template
import sqlite3
import json 

app = Flask(__name__)
DB_NAME = "ka_data.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row #This allows accessing columns by name 
    return conn

@app.route('/check')
def check_answer():
    #1 Get parameters from the url (e.g /check?q_id=1&ans=A&user=test@gmail.com)
    q_id = request.args.get('q_id')
    user_answer = request.args.get('ans')
    user_email = request.args.get('user', 'anonymous')

    if not q_id or not user_answer:
        return 'Missing Parameters', 400
    
    #2 Lookup the question in the database 
    conn = get_db_connection()
    question = conn.execute('''
        SELECT * FROM questions WHERE id = ?, 
        ''',   (q_id,)
        
        ).fetchone()
    if not question:
        conn.close()
        return "Question not found", 404
    
    #3 Convert the JSON string of options back into a python list 
    options_list = json.loads(question['options'])

    #4 Map the letter (A,B,C,D) to the list index (0,1,2,3)
    letter_to_index = {'A': 0, 'B':1, 'C': 2, 'D':3}



