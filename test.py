import os
import requests
from openai import AzureOpenAI
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import update
from pydantic import BaseModel
from typing import List,Dict
from gpt_agents.chatbot import Chatbot
from gpt_agents.analyzer import Analyzer
from db.database import engine, Base, SessionLocal
from db.models import User, Week


class Orchestrator:
    def __init__(self):
        self.analyzer = Analyzer()
        self.chatbot = Chatbot()

    def interpret_analysis(analysis, user_id=1):
        action, toolcall = analysis.split(sep=";", maxsplit=2)

        action = action.lower()
        #action = 'none' OR 'modification' OR 'addition' OR 'deletion'
        
        if action == "none" :
            return {}
        
        elif action == "modification" or action == "addition" or action == "deletion" :
            toolcall = toolcall.json()
            for day in toolcall :
                for task in toolcall[day] :
                    payload = {"day": day, "task": task}
                    response = requests.post(f"http://127.0.0.1:8000/week/{user_id}/add_task", json=payload)
            return response.json()
        
        # elif action == "add":
        #     day = tokens[1].lower()
        #     task = " ".join(tokens[2:])
        #     payload = {"day": day, "task": task}
        #     response = requests.post(f"http://127.0.0.1:8000/week/{user_id}/add_task", json=payload)
        #     return response.json()

        # elif action == "delete":
        #     day = tokens[1].lower()
        #     task = " ".join(tokens[2:])
        #     payload = {"day": day, "task": task}
        #     response = requests.post(f"http://127.0.0.1:8000/week/{user_id}/delete_task", json=payload)
        #     return response.json()

        
        
        else:
            return {"error": "Instruction inconnue"}

    def get_week_json() :
        response = requests.get("http://127.0.0.1:8000/week/1")
        data = response.json()
        return data.description
    
    def handle_request(self, user_input):
        chatbot_str = self.chatbot.handle_request(user_input)
        analysis_input = "<client>"+user_input+"</client>"+"<coach>"+chatbot_str+"</coach>"+"<JSON>"+Orchestrator.get_week_json()+"</JSON>"
        analysis = self.analyzer.handle_request(analysis_input)
        action, toolcall = analysis.split(sep=";", maxsplit=2)
        
        
        
        
        return chatbot_str, action, toolcall



# --- Initialisation de l'application FastAPI ---
app = FastAPI(title="LLM Coach API")
# Crée les tables si elles n'existent pas
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Schéma de la requête ---
class ChatRequest(BaseModel):
    user_prompt: str

@app.get("/")
def root():
    return {"message": "API is running on Render"}

## --- Schéma de la requête ---
@app.post("/chat")
def chat(request: ChatRequest):
   orchestrator = Orchestrator()
   try:
       user_input = request.user_prompt
       if user_input.lower() in ["exit", "quit"]:
           return {"response" : "exit"}
       response = orchestrator.handle_request(user_input)
       return {"response": response[0], "action": response[1], "toolcall": response[2]}
   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))


@app.post("/users/")
def get_or_create_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if user:
        return user

    # Sinon on le crée
    user = User(id=user_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user(username: str, email: str, db: Session = Depends(get_db)):
    user = User(username=username, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Récupérer une week
@app.get("/week/{user_id}")
def get_or_create_week(user_id: int, db: Session = Depends(get_db)):
    get_or_create_user(user_id, db)
    
    # Chercher la week
    week = db.query(Week).filter(Week.user_id == user_id).first()

    if not week:
        # Créer une week par défaut
        week = Week(
            user_id=user_id,
            week_number = 0,
            description={
                "monday": [],
                "tuesday": [],
                "wednesday": [],
                "thursday": [],
                "friday": [],
                "saturday": [],
                "sunday": []
            }
        )
        db.add(week)
        db.commit()
        db.refresh(week)

    return week

# Ajouter une task dans un jour précis
class Task(BaseModel):
    day: str
    task: str

@app.post("/week/{user_id}/add_task")
def add_task(user_id: int, data: Task, db: Session = Depends(get_db)):
    week = get_or_create_week(user_id, db)

    # Ajouter la task
    week.description[data.day] = week.description[data.day] + [data.task]
    flag_modified(week, "description")
    db.commit()
    db.refresh(week)
    return week

# Supprimer une task
@app.post("/week/{user_id}/delete_task")
def delete_task(user_id: int, data: Task, db: Session = Depends(get_db)):
    week = get_or_create_week(user_id, db)
    
    if data.task in week.description[data.day]:
        week.description[data.day].remove(data.task)
        flag_modified(week, "description")

    db.commit()
    db.refresh(week)
    return week

@app.post("/week/{user_id}/delete_day")
def delete_day(user_id: int, day: str, db: Session = Depends(get_db)):
    week = get_or_create_week(user_id, db)

    if day in week.description:
        week.description[day] = []
        flag_modified(week, "description")

    db.commit()
    db.refresh(week)
    return week

# Supprimer une week
@app.delete("/week/{user_id}")
def reset_week(user_id: int, db: Session = Depends(get_db)):
    week = get_or_create_week(user_id, db)

    # Remettre le JSON à zéro
    week.description = {day: [] for day in [
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday"
    ]}
    flag_modified(week, "description")

    db.commit()
    db.refresh(week)
    return week

