import requests
from flask import Flask, request, render_template, flash, redirect, url_for
import sqlite3
import json 
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DB_NAME = os.getenv("DB_NAME", "ka_data.db")
app.secret_key = os.getenv('FLASK_SECRET_KEY')
FORM_URL = os.getenv('GOOGLE_FORM_URL')

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row #This allows accessing columns by name 
    return conn

@app.route('/')
def index():
    return render_template('index.html', title="Knowledge Agent | Start Learning")

@app.route('/signup', methods=['POST'])
def signup():
    topic = request.form.get('topic')
    email = request.form.get('email')

    # 1. Map your HTML fields to the Google Form Entry IDs
    form_data = {
        "entry.567439755": topic,
        "entry.456320852": email
    }

    try:
        # 2. Silently submit the data to Google
        response = requests.post(FORM_URL, data=form_data)
        
        if response.status_code == 200:
            flash(f"Success! Your 30-day curriculum for '{topic}' is being generated.", "success")
        else:
            flash("Submission failed. Please try again.", "error")
            
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")

    return redirect(url_for('index'))

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
    user_index = letter_to_index.get(user_answer)

    #5 Get the user answer text
    if user_index is not None and user_index < len(options_list):
        user_answer_text = options_list[user_index]
    else:
        return "Invalid Choice", 400
    
    #6 Compare by index 
    correct_index = question['correct_answer_index']

    if correct_index is not None and correct_index >= 0:
        # Use index-based comparison (preferred)
        is_correct = (user_index == correct_index)
        correct_answer_text = options_list[correct_index] if correct_index < len(options_list) else question['correct_answer']
    else:
        # Fallback to text comparison for questions without correct_answer_index
        is_correct = (user_answer_text == question['correct_answer'])
        correct_answer_text = question['correct_answer']
    
    

    # Save the response into the db and handle duplicate attempt
    try:
        conn.execute ('''
            INSERT INTO user_responses (question_id, user_email, selected_option, is_correct) 
            VALUES (?,?,?,?)
            ''' , (q_id, user_email, user_answer_text, is_correct)
                    )
        conn.commit()
        already_answered = False
    except sqlite3.IntegrityError:
        already_answered = True
    finally :
        conn.close()

    return render_template('result.html',
                           is_correct = is_correct,
                           correct_answer = correct_answer_text,
                           explanation = question['explanation'],
                           user_answer = user_answer_text, 
                           already_answered = already_answered
                           )


if __name__ == '__main__':
    app.run(debug =True, port =5000)
