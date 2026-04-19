# backend/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import json
import asyncio

from backend.models import StartSessionRequest
from backend.session import create_session, get_session, add_qa_to_session
from backend.interviewer import get_question, evaluate_answer_stream

load_dotenv()

app = FastAPI(title="AI Mock Interview Platform")

# Serve frontend files
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def serve_frontend():
    with open("frontend/index.html") as f:
        return HTMLResponse(f.read())


@app.post("/start")
def start_interview(request: StartSessionRequest):
    """
    Create a new interview session.
    Returns session_id and the first question.
    """
    session_id = create_session(request.name, request.role, request.difficulty)
    first_question = get_question(request.role, request.difficulty, 0)
    
    # Save first question to session
    session = get_session(session_id)
    session["current_question"] = first_question
    
    from backend.session import update_session
    update_session(session_id, session)
    
    return {
        "session_id": session_id,
        "question": first_question,
        "question_number": 1,
        "total_questions": 3
    }


@app.websocket("/ws/{session_id}")
async def websocket_interview(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for the live interview.
    
    Message flow:
    Client sends: { "answer": "user's answer text" }
    Server sends: multiple { "type": "feedback_token", "content": "..." }
    Server sends: { "type": "score", "data": {...} }
    Server sends: { "type": "next_question", "question": "...", "number": N }
    Server sends: { "type": "interview_complete", "report": {...} }
    """
    await websocket.accept()
    
    try:
        while True:
            # Wait for candidate's answer
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") != "answer":
                continue
            
            answer = message.get("answer", "").strip()
            
            if not answer:
                await websocket.send_json({"type": "error", "message": "Empty answer received"})
                continue
            
            # Get session data
            session = get_session(session_id)
            if not session:
                await websocket.send_json({"type": "error", "message": "Session expired"})
                break
            
            current_question = session.get("current_question", "")
            question_index = session.get("current_question_index", 0)
            
            # Signal that evaluation is starting
            await websocket.send_json({"type": "evaluation_start"})
            
            # Stream the AI feedback + get score
            score = await evaluate_answer_stream(
                current_question,
                answer,
                session["role"],
                websocket
            )
            
            # Send the structured score
            await websocket.send_json({"type": "score", "data": score})
            
            # Save to session
            add_qa_to_session(session_id, current_question, answer, score)
            
            # Check if interview is complete (3 questions)
            if question_index >= 2:
                # Generate final report
                await asyncio.sleep(2)
                updated_session = get_session(session_id)
                scores = updated_session.get("scores", [])
                
                avg_technical = sum(s.get("technical", 0) for s in scores) / len(scores) if scores else 0
                avg_communication = sum(s.get("communication", 0) for s in scores) / len(scores) if scores else 0
                
                report = {
                    "name": session["name"],
                    "role": session["role"],
                    "avg_technical": round(avg_technical, 1),
                    "avg_communication": round(avg_communication, 1),
                    "overall_verdict": "Strong" if avg_technical >= 7 else "Acceptable" if avg_technical >= 5 else "Needs Work",
                    "questions_and_scores": list(zip(
                        updated_session.get("questions", []),
                        updated_session.get("scores", [])
                    ))
                }
                
                await websocket.send_json({"type": "interview_complete", "report": report})
                break
            
            else:
                # Send next question
                next_question = get_question(session["role"], session["difficulty"], question_index + 1)
                
                # Update session with next question
                session = get_session(session_id)
                session["current_question"] = next_question
                from backend.session import update_session
                update_session(session_id, session)
                
                await websocket.send_json({
                    "type": "next_question",
                    "question": next_question,
                    "number": question_index + 2
                })
    
    except WebSocketDisconnect:
        print(f"Session {session_id} disconnected")