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

    #Difficulty badge color 

    difficulty_colors = {
        "beginner" :"#28a745",
        "intermediate":"#fd7e14",
        "advanced":"#dc3545"
    }

    difficulty = q.get("difficulty","intermediate").lower()
    badge_color = difficulty_colors.get(difficulty,"#6c757d")

    #Option buttons
    options_html = ""
    for i, opt in enumerate(options):
        letter = letters[i]
        link = f"{BASE_URL}?q_id={q['id']}&ans={letter}&user={recipient_email}"
        options_html += f"""
            <a href = "{link}" style ="
            display:block;
            margin: 10px 0;
            padding:12px 2px;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            text-decoration: none;
            color: #212529;
            font-size: 15px;
            font-family: Arial, sans-serif;
            ">
                <strong>{letter}. </strong> {opt}
                </a> 
            """
   
    
    html = f"""
        <div style="
        font-family: Arial, sans-serif;
        max-width: 600px;
        margin: 0 auto;
        border: 1px solid #dee2e6;
        border-radius: 12px;
        overflow: hidden;
        " >

            <!-- Header --> 
            <div style ="background-color: #212529; padding: 20px 30px;">
                <h1 style="color: #ffffff; margin:0; font-size: 20px;" > 📚 KA Daily Question </h1>
            </div>

            <!-- Meta Info -->
            <div style="background-color: #f8f9fa; padding: 12px 30px; border-bottom: 1px solid #dee2e6; display:flex;">
            <span style="margin-right: 20px; font-size: 13px; color:#495057;" >
            📅 <strong> Day {q.get('day_number', 'N/A')} </strong>
            </span>

            <span style ="margin-right: 20px; font-size:13px; color:#495057;">
            📖 <strong> {q.get('topic','N/A')} </strong>
            </span>

            <span style ="
                background-color ={badge_color};
                color:white;
                padding: 2px 10px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
                ">{difficulty}</span>
            </div>
        
            <!-- Question Text -->
            <div style="padding: 30px;">
                <p style= "font-size: 17px; font-weight: bold; color:#212529; 
                margin-top: 0;"> 
                    {q['question_text']}
                </p>

                <!-- Options -->
                <div style="margin-top: 20px;">
                    {options_html}
                </div>
            </div>

            <!-- Footer -->
            <div style ="
                background-color: #f8f9fa;
                padding: 15px 30px;
                border-top:1px solid #dee2e6;
                text-align:center;
                ">
            
                <p style="color: #6c757d; font-size:12px ; margin:0;"> 
                    Click an option to submit your answer and see the explanation instantly. 
                </p>

                <p style="color: #adb5bd; font-size:11px; margin:5px 0 0 0;"> 
                    KA Project · Built with Google Gemini + Flask + SQLite
                </p>
            </div> 
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
    print(send_daily_question("agbajeh8@gmail.com",37))



    
