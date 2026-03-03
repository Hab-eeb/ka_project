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

#response.text #, response.usage_metadata

#topic_corpus = research_agent(topic='algebra')

topic_corpus_1 = """
# Topic Overview
Algebra is a branch of mathematics that substitutes letters (variables) for numbers to represent relationships and solve for unknown values. It transitions from concrete arithmetic to abstract reasoning, providing the tools to model real-world phenomena through equations, functions, and graphs. The study of algebra progresses from solving simple linear equations to analyzing complex non-linear systems and abstract structures.

---

# Beginner-Level Foundations

### 1. Variables and Constants
*   **Definition:** A variable is a symbol (usually a letter like $x$ or $y$) representing an unknown number. A constant is a fixed numerical value (e.g., $5, -2, \pi$).
*   **Purpose:** To create generalized formulas that apply to any value.
*   **Example:** In $3x + 5$, $x$ is the variable and $5$ is the constant.

### 2. Expressions vs. Equations
*   **Definition:** An expression is a mathematical phrase without an equals sign ($2x + 3$). An equation is a statement that two expressions are equal ($2x + 3 = 11$).
*   **Key Terms:**
    *   **Term:** A single number or variable, or numbers and variables multiplied together ($4x^2$).
    *   **Coefficient:** The numerical factor of a term ($4$ in $4x^2$).
    *   **Operator:** Symbols like $+$, $-$, $\times$, $\div$.

### 3. Order of Operations (PEMDAS/BODMAS)
*   **Definition:** The standard sequence for solving expressions: Parentheses, Exponents, Multiplication and Division (left to right), Addition and Subtraction (left to right).
*   **Common Misconception:** Thinking Multiplication always comes before Division; they hold equal priority and are processed left to right.

### 4. Solving One-Step and Two-Step Equations
*   **Logic:** Use "Inverse Operations" to isolate the variable.
    *   Addition $\leftrightarrow$ Subtraction
    *   Multiplication $\leftrightarrow$ Division
*   **Example:** $2x - 4 = 10$. Add $4$ to both sides ($2x = 14$), then divide by $2$ ($x = 7$).

### 5. The Coordinate Plane
*   **Definition:** A 2D surface formed by the intersection of a horizontal $x$-axis and a vertical $y$-axis.
*   **Key Terms:** Origin $(0,0)$, Quadrants (I, II, III, IV), Ordered Pair $(x, y)$.

---

# Intermediate Concepts

### 1. Linear Functions and Slope
*   **Deeper Explanation:** Linear functions create straight lines on a graph.
*   **Equations:**
    *   **Slope-Intercept Form:** $y = mx + b$ (where $m$ is slope, $b$ is $y$-intercept).
    *   **Point-Slope Form:** $y - y_1 = m(x - x_1)$.
    *   **Standard Form:** $Ax + By = C$.
*   **Slope ($m$):** The "rise over run" or rate of change: $m = (y_2 - y_1) / (x_2 - x_1)$.

### 2. Systems of Equations
*   **Definition:** A set of two or more equations with the same variables.
*   **Methods of Solving:**
    *   **Substitution:** Solve one equation for a variable and plug it into the other.
    *   **Elimination:** Add or subtract equations to cancel out a variable.
    *   **Graphing:** Find the point where lines intersect.
*   **Types of Solutions:** Consistent (one solution), Inconsistent (no solution/parallel lines), Dependent (infinitely many solutions/same line).

### 3. Polynomial Operations and Factoring
*   **Types:** Monomials, Binomials, Trinomials.
*   **FOIL Method:** Used for multiplying two binomials (First, Outer, Inner, Last).
*   **Factoring Techniques:**
    *   **Greatest Common Factor (GCF):** $3x^2 + 6x = 3x(x + 2)$.
    *   **Difference of Squares:** $a^2 - b^2 = (a - b)(a + b)$.
    *   **Trinomial Factoring:** Finding two numbers that multiply to $c$ and add to $b$ in $x^2 + bx + c$.

### 4. Quadratic Equations
*   **Definition:** Equations of the form $ax^2 + bx + c = 0$.
*   **The Quadratic Formula:** $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$.
*   **Discriminant ($b^2 - 4ac$):** Determines the nature of roots.
    *   $> 0$: Two real roots.
    *   $= 0$: One real root.
    *   $< 0$: Two complex roots.

### 5. Rules of Exponents and Radicals
*   **Product Rule:** $x^a \cdot x^b = x^{a+b}$.
*   **Power of a Power:** $(x^a)^b = x^{ab}$.
*   **Negative Exponents:** $x^{-a} = 1/x^a$.
*   **Rational Exponents:** $x^{1/2} = \sqrt{x}$.

---

# Advanced Topics

### 1. Functions: Transformations and Compositions
*   **Composition:** $(f \circ g)(x) = f(g(x))$.
*   **Inverses:** $f^{-1}(x)$ reflects the function over the line $y = x$. To find it, swap $x$ and $y$ and solve for $y$.
*   **Transformations:** $f(x-h) + k$ shifts the graph $h$ units horizontally and $k$ units vertically.

### 2. Logarithms and Exponential Functions
*   **Definition:** A logarithm is the inverse of an exponent. $\log_b(y) = x$ is equivalent to $b^x = y$.
*   **Properties:**
    *   $\log(ab) = \log(a) + \log(b)$.
    *   $\log(a/b) = \log(a) - \log(b)$.
    *   $\log(a^n) = n \cdot \log(a)$.
*   **Natural Log ($ln$):** Logarithm with base $e$ (approx. $2.718$).

### 3. Higher-Degree Polynomials
*   **Remainder Theorem:** If a polynomial $f(x)$ is divided by $(x - c)$, the remainder is $f(c)$.
*   **Synthetic Division:** A shortcut method for dividing polynomials by linear factors.
*   **Fundamental Theorem of Algebra:** A polynomial of degree $n$ has exactly $n$ complex roots.

### 4. Rational Expressions and Asymptotes
*   **Vertical Asymptotes:** Occur where the denominator equals zero (and does not cancel out).
*   **Horizontal Asymptotes:** Determined by comparing the degree of the numerator $(n)$ and denominator $(m)$:
    *   If $n < m$, $y = 0$.
    *   If $n = m$, $y = \text{ratio of leading coefficients}$.
    *   If $n > m$, no horizontal asymptote (potential slant asymptote).

### 5. Matrices and Systems
*   **Definition:** A rectangular array of numbers.
*   **Operations:** Matrix addition, scalar multiplication, and matrix multiplication (row-by-column).
*   **Determinants:** Used to find the inverse of a matrix or solve systems via **Cramer’s Rule**.

### 6. Sequences and Series
*   **Arithmetic:** $a_n = a_1 + (n-1)d$ (constant difference).
*   **Geometric:** $a_n = a_1 \cdot r^{n-1}$ (constant ratio).
*   **Summation (Sigma Notation):** $\sum$ represents the sum of a sequence.

---

# Cross-Topic Relationships
*   **Linear to Quadratic:** Linear equations represent constant change; quadratics represent accelerating change (area, gravity).
*   **Factoring and Graphing:** The factors of a polynomial expression correspond directly to the $x$-intercepts (roots) of its graph.
*   **Exponents and Logs:** These are inverse operations, just like addition and subtraction, allowing us to solve for variables located in the exponent.
*   **Algebra and Geometry:** The distance formula is an algebraic application of the Pythagorean Theorem.

---

# Common Mistakes & How to Avoid Them
*   **Distributive Property Errors:** Forgetting to multiply the second term inside parentheses: $3(x + 4)$ is $3x + 12$, not $3x + 4$.
*   **Negative Signs in Subtraction:** When subtracting a polynomial, distribute the negative to *every* term: $-(x - 5) = -x + 5$.
*   **Squaring a Binomial:** $(x + 3)^2$ is NOT $x^2 + 9$. It must be expanded to $x^2 + 6x + 9$.
*   **Dividing by Zero:** Always check that the denominator of a rational expression or the divisor in an equation is not zero.
*   **Inequality Sign Flip:** When multiplying or dividing an inequality by a negative number, the direction of the inequality sign must flip.

---

# Glossary
*   **Absolute Value:** The distance of a number from zero, always non-negative.
*   **Binomial:** A polynomial with exactly two terms.
*   **Domain:** The set of all possible input values ($x$) for a function.
*   **Function:** A relation where every input has exactly one output.
*   **Inequality:** A mathematical statement relating two quantities as being greater than, less than, or equal to each other.
*   **Parabola:** The U-shaped graph of a quadratic function.
*   **Radicand:** The value inside a radical (square root) symbol.
*   **Range:** The set of all possible output values ($y$) for a function.
*   **Root/Zero:** The value of $x$ that makes an equation equal to zero.
*   **Slope:** The measure of the steepness of a line.
"""
#topic = 'algebra'


def question_gen_agent(topic= '', topic_corpus =''):
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


# Function calls 
topic = 'General Artificial Intelligence'
data_research = safe_agent_call(lambda:research_agent(topic= topic)) 
topic_corpus = data_research['response_text']

with open("corpus_output_4.md", "w", encoding="utf-8") as f:
    f.write(topic_corpus)
    

data = safe_agent_call(lambda: question_gen_agent(topic=topic,topic_corpus=topic_corpus ))

response_parsed = data['parsed_response']

with open("course_output_2.json", "w", encoding="utf-8") as f:
    json.dump(response_parsed, f, ensure_ascii=False, indent=2)


print("Research Agent Metadata", data_research['metadata'])
print("Question Agent Metadata", data['metadata'])
    
