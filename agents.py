from google import genai 
from google.genai import types
from dotenv import load_dotenv
import os 
from pydantic import BaseModel
from typing import List
import json 
from typing_extensions import TypedDict
import time 
import requests

load_dotenv() #loads env file
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GEM_api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key = GEM_api_key)

class QuestionSchema(TypedDict):
    subtopic:str
    question_text:str
    options:List[str]
    correct_answer_index:int  # 0-3 index into options array
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
structured learning corpus about a user's topic. Your purpose is to create material 
that another agent will later use to generate 30 days of quiz questions with increasing difficulty.

You have access to web search tool. USE IT to find the latest (2026 and 2025), most accurate, and up-to-date 
information about the topic. Always ground your output in current facts, recent developments, 
and widely accepted knowledge. Do not rely solely on your training data — actively search 
for recent information to ensure freshness and accuracy. 
Make sure to include 2026 and 2025 as those are the most recent years.  

Your output must:

- Cover every important subtopic a well-informed learner should know.
- Progress from beginner → intermediate → advanced.
- Be structured, concise, factual, and easy to transform into questions.
- Include enough detail for question generation: definitions, examples, formulas, comparisons, common pitfalls, real-world applications.
- Incorporate recent developments, current best practices, and up-to-date statistics or examples where relevant.
- Avoid fluff or unnecessary wording.
- Be factual, accurate, and clearly organized.

Follow this structure exactly:

- Topic Overview
    A short, clear explanation of the topic and what it encompasses.
    Include any recent developments or current relevance.
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
        real-world applications
        equations, logic, or workflows if relevant
- Advanced Topics
    For each subtopic include:
        expert-level insights
        edge cases
        tradeoffs
        limitations
        formal reasoning or math if relevant
        typical interview-level or exam-level knowledge
        system-level connections to other fields
- Recent Developments & Current Trends
    What has changed recently in this field?
    New tools, frameworks, research, or best practices.
    Any emerging subtopics or shifts in industry consensus.
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

You are the Question Generator, a professional academic question Generator.

Goal:
Given a user topic and a structured learning corpus, 
generate a 30-day schedule of quiz questions that:
- progresses from easy → hard,
- balances coverage across the topic's subtopics,
- includes correct answers and a "full gist" explanation paragraph suitable for teaching,
- outputs ONLY valid JSON matching the required schema so it can be stored in a database.

Inputs you will receive:
- TOPIC: a short string (the user's chosen topic)
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
          "correct_answer_index": integer,          # 0-3 index of the correct option in the options array
          "explanation_gist": string                 # 3-6 sentences, teaching-focused
        }
      ]
    }
  ]
}

3) Exactly 30 day objects. day_number must be 1..30 with no gaps and in ascending order.
4) Questions per day: 1 .
5) Difficulty ramp:
   - Days 1-10 => difficulty_level = "Beginner"
   - Days 11-20 => difficulty_level = "Intermediate"
   - Days 21-30 => difficulty_level = "Advanced"
6) Use the CORPUS as the source of truth. Do not invent niche facts not supported by the corpus. 
    Prefer questions that can be answered from the corpus content.

CRITICAL — correct_answer_index rules:
- correct_answer_index MUST be an integer: 0, 1, 2, or 3.
- It represents the position of the correct answer in the options array (0-indexed).
- The option at that index IS the correct answer. There must be no mismatch.
- Vary the position of the correct answer across questions. Do NOT always put it at index 0 or 3.

Question design rules:
- Each question should be clear, unambiguous, and test one main concept.
- Prefer multiple-choice questions with 4 plausible options.
- Avoid "All of the above" / "None of the above".
- Avoid trick questions; difficulty should come from reasoning, application, or subtle distinctions found in the corpus.
- Ensure the correct answer is defensible based on the corpus.

Explanation ("explanation_gist") requirements:
- Must be a single paragraph, 3-6 sentences.
- Include:
  (a) why the correct answer is correct (1-2 sentences),
  (b) extra teaching context about the subtopic beyond the bare answer (2-4 sentences),
  (c) optionally mention a common misconception/pitfall from the corpus (briefly).
- Do NOT reference "the corpus" in the explanation.

Coverage requirements:
- Identify the main subtopics present in the CORPUS and distribute them across the 30 days.
- Avoid repeating the same subtopic too frequently; aim for balanced coverage.
- In Beginner days, focus on definitions, core terms, simple examples, and common misconceptions.
- In Intermediate days, focus on comparisons, procedures/workflows, applied scenarios, and "why" reasoning.
- In Advanced days, focus on edge cases, tradeoffs, limitations, deeper reasoning, and cross-topic relationships. 

"""

Feedback_system_prompt = """
You are the Learning Feedback Analyst, an expert educational assessor.

Goal:
Given a user's complete 30-day response history for a topic curriculum, 
produce a detailed, personalised performance analysis and learning roadmap.

Inputs you will receive:
- TOPIC: the curriculum topic
- USER_EMAIL: the learner's identifier
- RESPONSE_DATA: a JSON array of their responses, each containing:
    - day_number, subtopic, difficulty, question_text, 
    - user_answer, correct_answer, is_correct

Your analysis MUST include ALL of the following sections:

1. OVERALL PERFORMANCE SUMMARY
   - Total score (correct/total) and percentage
   - Performance by difficulty tier (Beginner, Intermediate, Advanced) with percentages
   - A brief 2-3 sentence overall assessment of the learner's level

2. STRENGTH AREAS
   - List the subtopics where the user consistently answered correctly
   - Explain WHY these are strengths (what concepts they've clearly grasped)
   - Suggest how to leverage these strengths (e.g., "You could explore advanced applications of X")

3. AREAS FOR IMPROVEMENT
   - List the subtopics where the user got questions wrong
   - For each weak area, explain:
     (a) What the user likely misunderstood based on their wrong answer choices
     (b) A concise explanation of the correct concept
     (c) A practical tip or resource suggestion for improvement
   - Prioritise by impact (which gaps matter most for overall understanding)

4. DIFFICULTY PROGRESSION ANALYSIS
   - How did the user perform as difficulty increased?
   - Did they maintain accuracy or drop off?
   - What does this tell us about their depth of understanding vs surface-level recall?

5. LEARNING PATTERNS
   - Any patterns in mistakes (e.g., consistent confusion between two concepts, 
     tendency to pick a certain type of wrong answer)
   - Were there any surprising correct answers on hard questions paired with 
     wrong answers on easier ones? What might explain this?

6. PERSONALISED NEXT STEPS
   - A prioritised list of 3-5 specific actions the user should take
   - Each action should be concrete and actionable (not vague like "study more")
   - Frame these positively — focus on growth, not failure

Output format:
- Output ONLY the inner HTML content for the analysis sections (no <html>, <head>, <body> tags).
- Use these HTML elements for structure:
  - <h2> for section headings (e.g., "Overall Performance Summary")
  - <p> for paragraphs
  - <ul> and <li> for lists
  - <strong> for emphasis
  - <span style="color: #28a745;"> for positive highlights (strengths, correct answers)
  - <span style="color: #dc3545;"> for areas needing improvement
  - <span style="color: #fd7e14;"> for neutral observations
- Do NOT include any markdown formatting — output pure HTML only.
- Do NOT wrap the output in code fences or backticks.

Tone and style:
- Be encouraging but honest. Don't sugarcoat poor performance, but frame it constructively.
- Write as if you're a supportive tutor who genuinely wants this person to improve.
- Use the learner's actual data to back up every claim — no generic advice.
- Keep the total response between 500-800 words.
"""


#Function to help retry because of rate limits
def safe_agent_call(agent_func, max_retries = 5, wait_seconds =10):
    for attempt in range(max_retries):
        try:
            return agent_func()
        except genai.errors.ServerError as e:
            if e.code == 503:
                print(f"Model Overloaded. Attempt {attempt +1}/{max_retries}. Waiting {wait_seconds}s...")
                time.sleep(wait_seconds)
            else:
                raise #raise if different 
    print("Max retries reached.")
    return None 




# Define the search tool schema for Gemini
serper_search_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="web_search",
            description="Search the web for current, accurate information about a topic. Use this to find up-to-date facts, definitions, recent developments, and detailed explanations.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "query": types.Schema(
                        type="STRING",
                        description="The search query to look up"
                    )
                },
                required=["query"]
            )
        )
    ]
)


def serper_search(query, num_results=10):
    """Fetches search results from Serper API."""
    response = requests.post(
        "https://google.serper.dev/search",
        headers={
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        },
        json={"q": query, "num": num_results}
    )
    response.raise_for_status()
    results = response.json()

    # Format into a readable string for the LLM
    formatted = []
    for i, item in enumerate(results.get("organic", []), 1):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        link = item.get("link", "")
        formatted.append(f"[{i}] {title}\n{snippet}\nSource: {link}")
    return "\n\n".join(formatted)


def research_agent(topic=''):
    """Generates a corpus based on the user's topic."""

    # Initial request — Gemini decides if/what to search
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=topic,
        config={
            "system_instruction": RA_system_prompt,
            "tools": [serper_search_tool],
            "temperature": 0.8
        }
    )

    # Tool-use loop: keep going while Gemini wants to search
    while response.candidates[0].content.parts:
        # Check if any part is a function call
        function_calls = [
            part for part in response.candidates[0].content.parts
            if part.function_call
        ]

        if not function_calls:
            break  # No more tool calls, we have the final text

        # Process each function call
        function_responses = []
        for fc in function_calls:
            query = fc.function_call.args.get("query", topic)
            print(f"Serper search: '{query}'")
            search_results = serper_search(query)

            function_responses.append(
                types.Part.from_function_response(
                    name="web_search",
                    response={"result": search_results}
                )
            )

        # Send results back to Gemini to continue
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Content(role="user", parts=[types.Part.from_text(text=topic)]),
                response.candidates[0].content,  # assistant's tool call turn
                types.Content(role="user", parts=function_responses)  # tool results
            ],
            config={
                "system_instruction": RA_system_prompt,
                "tools": [serper_search_tool],
                "temperature": 0.8
            }
        )

    return {"response_text": response.text, "metadata": response.usage_metadata}

def question_agent(topic= '', topic_corpus =''):
      
      """Generates Questions based on the corpus responses."""
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


def feedback_agent(topic, user_email, response_data):
    """Generates a detailed learning feedback report based on a user's 30-day responses."""
    
    prompt = f"""
            Analyse the following learner's complete response history and produce a detailed feedback report.

            TOPIC: {topic}
            USER: {user_email}

            RESPONSE DATA:
            {json.dumps(response_data, indent=2)}

            Produce the full analysis now.
            """
    response = client.models.generate_content(
            model = "gemini-3-flash-preview",
            contents = prompt,
            config = {
                "system_instruction": Feedback_system_prompt,
                "temperature": 0.6
            }
    )
    return {"feedback_text": response.text, "metadata": response.usage_metadata}
