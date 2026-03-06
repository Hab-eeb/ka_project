import os
import json 
import sqlite3 
from dotenv import load_dotenv
import resend 

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
BASE_URL = os.getenv("BASE_URL")
DB_NAME = os.getenv("DB_NAME")

resend.api_key = RESEND_API_KEY

def fetch_question(question_id: int):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    q = conn.execute('''
        SELECT * FROM questions WHERE id = ?
        ''', (question_id)
                     ).fetchone()
    
    conn.close()
    return q 

def build_question_email_html(q, recipent_email:str):
    options = json.loads(q['options'])
    letters = ["A","B","C","D"]

    html = f"""
        <div style="font-family: Arial, sans-serif;line-height:1.4;" >
            <h2>KA Daily Question</h2> 
            <p><strong> {q["question_text"]}</strong></p>
            <p style = "color:#666;">Topic: {q.get("topic", "")}</p>
            <hr/>
        """
    
    for i, opt in enumerate(options):
        letter = letters[i]
        link = f"{BASE_URL}?q_id={q['id']}&ans="
