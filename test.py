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
import json


class Orchestrator:
    def __init__(self):
        self.analyzer = Analyzer()
        self.chatbot = Chatbot()

    def interpret_analysis(self, analysis: str, user_id=1):
        # parse JSON string returned by the analyzer
        dico = json.loads(analysis)

        results = []
        print(dico)

        # handle additions
        if "addition" in dico:
            print(dico["addition"])
            for day in dico["addition"]:
                for task in dico["addition"][day]:
                    payload = {"day": day, "task": task}
                    resp = requests.post(f"http://127.0.0.1:8000/week/{user_id}/add_task", json=payload)
                    try:
                        resp.raise_for_status()
                        results.append(resp.json())
                    except Exception:
                        # fall back to text if JSON not available
                        results.append({"status_code": resp.status_code, "text": resp.text})

        # handle deletions
        if "deletion" in dico:
            for day in dico["deletion"]:
                for task in dico["deletion"][day]:
                    payload = {"day": day, "task": task}
                    resp = requests.post(f"http://127.0.0.1:8000/week/{user_id}/delete_task", json=payload)
                    try:
                        resp.raise_for_status()
                        results.append(resp.json())
                    except Exception:
                        results.append({"status_code": resp.status_code, "text": resp.text})

        # return a serializable structure: empty dict if nothing happened, single dict if one result, else list
        if not results:
            return {}
        if len(results) == 1:
            return results[0]
        return results

    def get_week_json() :
        response = requests.get("http://127.0.0.1:8000/week/1")
        data = response.json()
        return json.dumps(data["description"])
    
    def handle_request(self, user_input):
        chatbot_str = self.chatbot.handle_request(user_input)
        analysis_input = "<client>"+user_input+"</client>"+"<coach>"+chatbot_str+"</coach>"+"<JSON>"+Orchestrator.get_week_json()+"</JSON>"
        analysis = self.analyzer.handle_request(analysis_input)
        response = self.interpret_analysis(analysis)
        
        return chatbot_str, "", response



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


def user_to_dict(user: User):
    return {"id": user.id}


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


def get_or_create_user_model(user_id: int, db: Session):
    user = db.query(User).filter(User.id == user_id).first()

    if user:
        return user

    # Sinon on le crée
    user = User(id=user_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/users/")
def get_or_create_user(user_id: int, db: Session = Depends(get_db)):
    user = get_or_create_user_model(user_id, db)
    return user_to_dict(user)


# Récupérer une week
def get_or_create_week_model(user_id: int, db: Session):
    get_or_create_user_model(user_id, db)
    
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


@app.get("/week/{user_id}")
def get_or_create_week(user_id: int, db: Session = Depends(get_db)):
    week = get_or_create_week_model(user_id, db)
    return week_to_dict(week)

def week_to_dict(week: Week):
    return {
        "id": week.id,
        "user_id": week.user_id,
        "week_number": week.week_number,
        "description": week.description,
    }

# Ajouter une task dans un jour précis
class Task(BaseModel):
    day: str
    task: str

@app.post("/week/{user_id}/add_task")
def add_task(user_id: int, data: Task, db: Session = Depends(get_db)):
    week = get_or_create_week_model(user_id, db)

    # Ajouter la task
    week.description[data.day] = week.description[data.day] + [data.task]
    flag_modified(week, "description")
    db.commit()
    db.refresh(week)
    return week_to_dict(week)


# Supprimer une task
@app.post("/week/{user_id}/delete_task")
def delete_task(user_id: int, data: Task, db: Session = Depends(get_db)):
    week = get_or_create_week_model(user_id, db)
    
    if data.task in week.description[data.day]:
        week.description[data.day].remove(data.task)
        flag_modified(week, "description")

    db.commit()
    db.refresh(week)
    return week_to_dict(week)

@app.post("/week/{user_id}/delete_day")
def delete_day(user_id: int, day: str, db: Session = Depends(get_db)):
    week = get_or_create_week_model(user_id, db)

    if day in week.description:
        week.description[day] = []
        flag_modified(week, "description")

    db.commit()
    db.refresh(week)
    return week_to_dict(week)

# Supprimer une week
@app.delete("/week/{user_id}")
def reset_week(user_id: int, db: Session = Depends(get_db)):
    week = get_or_create_week_model(user_id, db)

    # Remettre le JSON à zéro
    week.description = {day: [] for day in [
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday"
    ]}
    flag_modified(week, "description")

    db.commit()
    db.refresh(week)
    return week_to_dict(week)

