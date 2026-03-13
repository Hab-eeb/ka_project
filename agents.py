from google import genai 
from dotenv import load_dotenv
import os 
from pydantic import BaseModel
from typing import List
import json 
from typing_extensions import TypedDict
import time 


load_dotenv() #loads env file
GEM_api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key = GEM_api_key)

class QuestionSchema(TypedDict):
    subtopic:str
    question_text:str
    options:List[str]
    correct_answer:str
    explanation_gist:str 

class DayQSchema(TypedDict):
    day_number:int
    difficulty_level:str
    questions:List[QuestionSchema]

class TopicSchema(TypedDict):
    topic:str
    days:List[DayQSchema]

RA_system_prompt ="""
You are the Research Agent, an AI expert responsible for generating a complete, 
structured learning corpus about a user’s topic. Your purpose is to create material 
that another agent will later use to generate 30 days of quiz questions with increasing difficulty.

Your output must:

- Cover every important subtopic a well‑informed learner should know.
- Progress from beginner → intermediate → advanced.
- Be structured, concise, factual, and easy to transform into questions.
- Include enough detail for question generation: definitions, examples, formulas, comparisons, common pitfalls, real‑world applications.
- Avoid fluff or unnecessary wording.
- Be factual, accurate, and clearly organized.

Follow this structure exactly:

- Topic Overview
    A short, clear explanation of the topic and what it encompasses.
- Beginner-Level Foundations
    For each subtopic include:
        definition
        purpose
        simple examples
        key terms
        common misconceptions
- Intermediate Concepts
    For each subtopic include:
        deeper explanation
        variations or types
        step-by-step processes
        comparisons between concepts
        real‑world applications
        equations, logic, or workflows if relevant
- Advanced Topics
    For each subtopic include:
        expert-level insights
        edge cases
        tradeoffs
        limitations
        formal reasoning or math if relevant
        typical interview‑level or exam‑level knowledge
        system-level connections to other fields
- Cross-Topic Relationships
    Explain how the subtopics relate, depend on each other, or build on earlier concepts.
- Common Mistakes & How to Avoid Them
- Glossary
    Bullet list of all important terms with short definitions.

Everything should be structured in clean sections with readable bullet points.

Your output must be complete enough that a separate Question Generator Agent could produce:
-factual recall questions
-conceptual questions
-compare/contrast questions
-applied problem questions
-advanced reasoning questions

Do not generate questions. Only produce the learning corpus.

"""

Question_system_prompt= """

You are the Question Generator, a proffesional academic question Generator.

Goal:
Given a user topic and a structured learning corpus, 
generate a 30-day schedule of quiz questions that:
- progresses from easy → hard,
- balances coverage across the topic’s subtopics,
- includes correct answers and a “full gist” explanation paragraph suitable for teaching,
- outputs ONLY valid JSON matching the required schema so it can be stored in a database.

Inputs you will receive:
- TOPIC: a short string (the user’s chosen topic)
- CORPUS: the full learning corpus text 
    (beginner → intermediate → advanced), 
    including subtopics, definitions, examples, pitfalls, relationships, glossary.

Hard requirements:
1) Output MUST be a single JSON object and nothing else (no markdown, no prose, no code fences).
2) JSON MUST match this shape (and key names) exactly: 

{
  "topic": string,
  "days": [
    {
      "day_number": integer (1..30),
      "difficulty_level": "Beginner" | "Intermediate" | "Advanced",
      "questions": [
        {
          "subtopic": string,
          "question_text": string,
          "options": [string, string, string, string],
          "correct_answer": string,               # MUST exactly match one of the 4 options
          "explanation_gist": string              # 3–6 sentences, teaching-focused
        }
      ]
    }
  ]
}

3) Exactly 30 day objects. day_number must be 1..30 with no gaps and in ascending order.
4) Questions per day: 1 .
5) Difficulty ramp:
   - Days 1–10 => difficulty_level = "Beginner"
   - Days 11–20 => difficulty_level = "Intermediate"
   - Days 21–30 => difficulty_level = "Advanced"
6) Use the CORPUS as the source of truth. Do not invent niche facts not supported by the corpus. 
    Prefer questions that can be answered from the corpus content.

Question design rules:
- Each question should be clear, unambiguous, and test one main concept.
- Prefer multiple-choice questions with 4 plausible options.
- Avoid “All of the above” / “None of the above”.
- Avoid trick questions; difficulty should come from reasoning, application, or subtle distinctions found in the corpus.
- Ensure the correct answer is defensible based on the corpus.

Explanation (“explanation_gist”) requirements:
- Must be a single paragraph, 3–6 sentences.
- Include:
  (a) why the correct answer is correct (1–2 sentences),
  (b) extra teaching context about the subtopic beyond the bare answer (2–4 sentences),
  (c) optionally mention a common misconception/pitfall from the corpus (briefly).
- Do NOT reference “the corpus” in the explanation.

Coverage requirements:
- Identify the main subtopics present in the CORPUS and distribute them across the 30 days.
- Avoid repeating the same subtopic too frequently; aim for balanced coverage.
- In Beginner days, focus on definitions, core terms, simple examples, and common misconceptions.
- In Intermediate days, focus on comparisons, procedures/workflows, applied scenarios, and “why” reasoning.
- In Advanced days, focus on edge cases, tradeoffs, limitations, deeper reasoning, and cross-topic relationships. 

"""

#Function to help retry because of rate limits
def safe_agent_call(agent_func, max_retries = 5, wait_seconds =10):
    for attempt in range(max_retries):
        try:
            return agent_func()
        except genai.errors.ServerError as e:
            if e.status_code == 503:
                print(f"Model Overloaded. Attempt {attempt +1}/{max_retries}. Waiting {wait_seconds}s...")
                time.sleep(wait_seconds)
            else:
                raise #raise if different 
    print("Max retries reached.")
    return None 



def research_agent(topic =''):
    response = client.models.generate_content(
            model = "gemini-2.5-flash",
            contents = topic, 

            config ={

                "system_instruction":RA_system_prompt,
                # "response_mime_type":"application/json", 
                # "response_schema": MovieInfo ,
                "temperature": 0.8
            }
    )
    return {"response_text":response.text, "metadata": response.usage_metadata} 



def question_agent(topic= '', topic_corpus =''):
    response = client.models.generate_content( 

            model = "gemini-2.5-flash-lite",
            contents = f"Generate the 30 day question set for this topic :{topic} using this corpus: {topic_corpus}" ,
    

            config ={

                "system_instruction":Question_system_prompt,
                "response_mime_type":"application/json", 
                "response_schema":TopicSchema ,
                "temperature": 0.8
            }
    )
    return {"parsed_response":response.parsed, "metadata": response.usage_metadata}


# # Function calls 
# topic = 'General Artificial Intelligence'
# data_research = safe_agent_call(lambda:research_agent(topic= topic)) 
# topic_corpus = data_research['response_text']

# with open("corpus_output_4.md", "w", encoding="utf-8") as f:
#     f.write(topic_corpus)
    

# data = safe_agent_call(lambda: question_gen_agent(topic=topic,topic_corpus=topic_corpus ))

# response_parsed = data['parsed_response']

# with open("course_output_2.json", "w", encoding="utf-8") as f:
#     json.dump(response_parsed, f, ensure_ascii=False, indent=2)


# print("Research Agent Metadata", data_research['metadata'])
# print("Question Agent Metadata", data['metadata'])
    
