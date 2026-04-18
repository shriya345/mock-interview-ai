# backend/session.py
from dotenv import load_dotenv
load_dotenv()
import redis
import json
import uuid
import os
from datetime import datetime

# Connect to Redis
r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

def create_session(name: str, role: str, difficulty: str) -> str:
    """
    Create a new interview session and save it in Redis.
    Returns a unique session_id.
    """
    session_id = str(uuid.uuid4())[:8]   # Short unique ID like "a3f7c2d1"
    
    session_data = {
        "session_id": session_id,
        "name": name,
        "role": role,
        "difficulty": difficulty,
        "started_at": datetime.now().isoformat(),
        "questions": [],     # Will be filled as interview progresses
        "answers": [],
        "scores": [],
        "current_question_index": 0
    }
    
    # Save to Redis with 2-hour expiry (7200 seconds)
    r.setex(
        f"session:{session_id}",
        7200,
        json.dumps(session_data)
    )
    
    return session_id


def get_session(session_id: str) -> dict:
    """Retrieve session data from Redis."""
    data = r.get(f"session:{session_id}")
    if not data:
        return None
    return json.loads(data)


def update_session(session_id: str, session_data: dict):
    """Save updated session back to Redis."""
    r.setex(
        f"session:{session_id}",
        7200,
        json.dumps(session_data)
    )


def add_qa_to_session(session_id: str, question: str, answer: str, score: dict):
    """Add a completed Q&A round to the session."""
    session = get_session(session_id)
    if not session:
        return
    
    session["questions"].append(question)
    session["answers"].append(answer)
    session["scores"].append(score)
    session["current_question_index"] += 1
    
    update_session(session_id, session)