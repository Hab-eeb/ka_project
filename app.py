from flask import Flask, request, render_template
import sqlite3
import json 
from dotenv import load_dotenv
import os 

load_dotenv()
DB_NAME = os.getenv("DB_NAME")

app = Flask(__name__)


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
        SELECT * FROM questions WHERE id = ? 
        ''',   (q_id,)
        
        ).fetchone()
    if not question:
        conn.close()
        return "Question not found", 404
    
    #3 Convert the JSON string of options back into a python list 
    options_list = json.loads(question['options'])

    #4 Map the letter (A,B,C,D) to the list index (0,1,2,3)
    letter_to_index = {'A': 0, 'B':1, 'C': 2, 'D':3}
    index = letter_to_index.get(user_answer)

    #5 Get the actual answer
    if index is not None and index < len(options_list):
        user_answer_text = options_list[index]
    else:
        return "Invalid Choice", 400
    
    #6 Compare full text 
    is_correct = (user_answer_text == question['correct_answer'])


    # Save the response into the db and handle duplicate attempt

    try:
        conn.execute ('''
            INSERT INTO user_responses (question_id, user_email, selected_option, is_correct) 
            VALUES (?,?,?,?)
            ''' , (q_id,user_email,user_answer_text,is_correct)
                    )
        conn.commit()
        already_answered = False
    except sqlite3.IntegrityError:
        already_answered = True
    finally :
        conn.close()

    return render_template('result.html',
                           is_correct = is_correct,
                           correct_answer = question['correct_answer'],
                           explanation = question['explanation'],
                           user_answer = user_answer_text, 
                           already_answered = already_answered
                           )


if __name__ == '__main__':
    app.run(debug =True, port =5000)

