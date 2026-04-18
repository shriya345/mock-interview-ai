# backend/models.py
from pydantic import BaseModel
from typing import Optional

class StartSessionRequest(BaseModel):
    role: str          # "SDE", "Data Analyst", "Backend Engineer"
    difficulty: str    # "beginner", "intermediate", "advanced"
    name: str          # Candidate's name

class AnswerSubmission(BaseModel):
    answer: str

class Score(BaseModel):
    technical: int        # 1-10
    communication: int    # 1-10
    suggestion: str       # One concrete improvement tip
    verdict: str          # "Strong" / "Acceptable" / "Needs Work"