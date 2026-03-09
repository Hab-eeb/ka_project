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
    q = conn.execute(
        "SELECT * FROM questions WHERE id = ?", (question_id,)
                     ).fetchone()
    
    conn.close()
    return dict(q) if q else None 

def build_question_email_html(q, recipient_email:str):
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
        link = f"{BASE_URL}?q_id={q['id']}&ans={letter}&user={recipient_email}"
        html += f"""
            <p> 
                <a href = "{link}" style = "font-size:16px; text-decoration:none;">
                <strong>{letter} </strong> {opt}
                </a> 
            </p>
            """
    html += """
        <hr/>

        <p style ="color:#666; font-size:12px;">
            Click an option to submit your answer and get feedback immediately. 
        </p>
        </div>        
        """
    return html 

def send_daily_question(recepient_email: str, question_id:int):
    if not RESEND_API_KEY:
        raise RuntimeError("Missing RESEND API KEY env var")
    

    q = fetch_question(question_id)
    if not q:
        raise ValueError(f"Question id ={question_id} not found")
    

    subject = f"KA Daily Question (Day {q['day_number']})" 
    html = build_question_email_html(q,recepient_email)

    #Resend expects: from,to, subject, html/text
    resp = resend.Emails.send({
        "from":SENDER_EMAIL,
        "to": [recepient_email],
        "subject": subject,
        "html": html
    })

    return resp


if __name__ == "__main__":

    #Replace with your email and a real question id for testing
    print(send_daily_question("agbajeh8@gmail.com",5))



    
