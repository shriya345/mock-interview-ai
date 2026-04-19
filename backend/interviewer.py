import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def get_groq_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


QUESTION_BANK = {
    "SDE": {
        "beginner": [
            "Explain the difference between an array and a linked list.",
            "What is recursion? Give an example.",
            "What is the time complexity of binary search?"
        ],
        "intermediate": [
            "How would you design a URL shortening service?",
            "Explain how a HashMap works internally.",
            "What is the difference between process and thread?"
        ],
        "advanced": [
            "Design a distributed rate limiter.",
            "How would you handle database sharding at scale?",
            "Explain CAP theorem with a real-world example."
        ]
    },
    "Data Analyst": {
        "beginner": [
            "What is the difference between INNER JOIN and LEFT JOIN?",
            "Explain what a null value means in a database.",
            "What is the purpose of GROUP BY in SQL?"
        ],
        "intermediate": [
            "How would you identify outliers in a dataset?",
            "Explain the difference between correlation and causation.",
            "What is a window function in SQL? Give an example."
        ],
        "advanced": [
            "How would you design an A/B testing framework?",
            "Explain how you would handle class imbalance in a ML dataset.",
            "Design a real-time analytics pipeline for 1M daily events."
        ]
    },
    "Backend Engineer": {
        "beginner": [
            "What is the difference between GET and POST requests?",
            "What is a REST API?",
            "Explain what JWT authentication is."
        ],
        "intermediate": [
            "How does caching improve API performance?",
            "What is the difference between SQL and NoSQL databases?",
            "Explain how you would implement rate limiting."
        ],
        "advanced": [
            "How would you design a notification system for 10M users?",
            "Explain event-driven architecture with a practical example.",
            "How does a message queue differ from a pub/sub system?"
        ]
    }
}


def get_question(role: str, difficulty: str, question_index: int) -> str:
    questions = QUESTION_BANK.get(role, {}).get(difficulty, [])
    if question_index < len(questions):
        return questions[question_index]
    else:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": f"Generate ONE {difficulty} level interview question for a {role} position. Return only the question, nothing else."
            }],
            max_tokens=100
        )
        return response.choices[0].message.content.strip()


async def evaluate_answer_stream(question: str, answer: str, role: str, websocket):
    client = get_groq_client()

    evaluation_prompt = f"""You are an experienced technical interviewer for a {role} position.

Question asked: {question}
Candidate's answer: {answer}

Provide a helpful, encouraging interview evaluation. Structure it as:

**What you got right:** [1-2 sentences]
**What could be stronger:** [1-2 sentences]
**Sample strong answer would include:** [2-3 key points]

Be specific, practical, and encouraging. Then on the LAST LINE write exactly this JSON and nothing after it:
SCORE:{{"technical": X, "communication": Y, "suggestion": "one sentence tip", "verdict": "Strong/Acceptable/Needs Work"}}

Where X and Y are scores from 1-10."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": evaluation_prompt}],
        max_tokens=600,
        stream=False
    )

    full_response = response.choices[0].message.content
    feedback_text = full_response.split("SCORE:")[0].strip()

    await websocket.send_json({
        "type": "feedback_token",
        "content": feedback_text
    })

    score = {"technical": 7, "communication": 7, "suggestion": "Keep practicing!", "verdict": "Acceptable"}

    if "SCORE:" in full_response:
        try:
            score_line = full_response.split("SCORE:")[-1].strip()
            score = json.loads(score_line)
        except Exception:
            pass

    return score