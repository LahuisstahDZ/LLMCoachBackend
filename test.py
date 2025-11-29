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
from gpt_agents.week_plan_analyzer import WeekPlanAnalyst
from gpt_agents.motivator import Motivator
from db.database import engine, Base, SessionLocal
from db.models import User, Week, Settings
import json


class Orchestrator:
    def __init__(self):
        
        self.analyzer = Analyzer()
        self.week_plan_analyzer = WeekPlanAnalyst()
        personality = self.get_personality_prompt()
        self.chatbot = Chatbot(personality)
        self.motivator = Motivator()

    def interpret_analysis(self, analysis: str, user_id=1):
        # parse JSON string returned by the analyzer
        dico = json.loads(analysis)

        results = []

        # handle additions
        print("--- Starting additions")
        if "addition" in dico:
            for day in dico["addition"]:
                for task in dico["addition"][day]:
                    print(f"Adding task '{task}' to day '{day}'")
                    payload = {"day": day, "task": task}
                    resp = call_add_task(user_id, payload)
                    try:
                        resp.raise_for_status()
                        results.append(resp.json())
                    except Exception:
                        # fall back to text if JSON not available
                        results.append({"status_code": resp.status_code, "text": resp.text})

        # handle deletions
        print("--- Starting deletions")
        if "deletion" in dico:
            for day in dico["deletion"]:
                for task in dico["deletion"][day]:
                    print(f"Deleting task '{task}' from day '{day}'")
                    payload = {"day": day, "task": task}
                    resp = call_delete_task(user_id, payload)
                    try:
                        resp.raise_for_status()
                        results.append(resp.json())
                    except Exception:
                        results.append({"status_code": resp.status_code, "text": resp.text})

        # return a serializable structure: empty dict if nothing happened, single dict if one result, else list
        if len(results)==0 :
            return {}
        if len(results) == 1:
            return results[0]
        print("--- Ending interpret_analysis")
        return results 

    def get_week_json(self, user_id = 1) :
        response = call_get_week(user_id)
        data = response.json()
        return json.dumps(data["description"])
    
    def get_training_goals_json(self, user_id) :
        response = call_training_goals(user_id)
        data = response.json()
        answer = ""
        for key in data :
            for i in range(len(data[key])) :
                answer += data[key][i] + ", "
        answer = answer.removesuffix(', ')
        return answer
    
    def get_personality_prompt(self, user_id=1) :
        response = call_coach_preferences(user_id)
        data = response.json()
        print(data)
        gender = data["gender"]
        if not gender : gender = "male"
        gender_prompt = f"You are a {gender} health and sport training coach."
        
        teaching_style = data["style"]
        teaching_prompt = ""
        if teaching_style == "strict" :
            teaching_prompt = "To coach your client, you act as a strict military drill sergeant. Your tone must be direct, no-nonsense, and commanding. Use short, imperative sentences and avoid any pleasantries. "
        elif teaching_style == "encouraging" :
            teaching_prompt = "As a coach, you use an uplifting and inspiring tone to fuel their determination. You aim to inspire and motivate your client as they navigate the challenges of starting to actively take care of their health. "
        elif teaching_style == "scientific" :
            teaching_prompt = "To coach your client, you need to take a scientific approach. Always lean on clear, scientific facts, with an objective tone. You can also rely on their activity facts and their real struggles to help them overcome their sedentariness. "
        else : #flexible by default
            teaching_prompt ="You know the client intimately -strengths, flaws, fears, and aspirations. To coach them, adopt a direct, no-nonsense tone. Be unrelentingly assertive, even a bit confrontational, to challenge the client in confronting the truths they might be avoiding. Push them into getting the best out of themselves, peeling back the layers of defensiveness and excuses, but do so with an undertone of care, ensuring they feel guided rather than attacked. The goal is self-motivation through tough love and sharp insight. "
        
        specialty = data["specialty"] #strength, cardio, yoga, pilates, functional training
        specialty_prompt = ""
        if specialty == "strength" :
            specialty_prompt = "Your client wants to build their body strength. "
        elif specialty == "cardio" :
            specialty_prompt = "Your client wants to focus on enhancing their cardio. "
        elif specialty == "yoga" :
            specialty_prompt = "Your client is drawn to yoga exercises although you might assume they don't know anything about it. "
        elif specialty == "pilates" :
            specialty_prompt = "Your client likes pilates training although you might assume they don't know anything about it. "
        else: # functional training by default
            specialty_prompt = "Your client wants to use functional training. It is a fitness approach designed to enhance the body's ability to perform everyday movements with ease and efficiency. Functional training focuses on exercises that mimic real-life activities, such as lifting, squatting, and climbing."

        specialty_prompt += "Your suggestions and recommendations should take this preference into account. "
        
        
        language = data["language"]
        language_prompt = f"You must talk in {language}. "
        
        prompt = language_prompt + gender_prompt + teaching_prompt + specialty_prompt
        return prompt
    
    def handle_request(self, user_input):
        chatbot_str = self.chatbot.handle_request(user_input)
        analysis_input = "<client>"+user_input+"</client>"+"<coach>"+chatbot_str+"</coach>"
        
        analysis = self.analyzer.detect_week_change(analysis_input) #is a week plan modification necessary ? 

        #analysis = true or false
        if analysis.lower() == "true" :
            week_plan_input = analysis_input +"<JSON>"+self.get_week_json()+"</JSON>"
            #make a llm call to modify the week plan
            analysis = self.week_plan_analyzer.handle_request(week_plan_input) 
            response = self.interpret_analysis(analysis)
        else :
            response = {}
        
        return chatbot_str, response
    
    def get_motivational_quote(self, u_id:int) :
        #send general_goals et week to Motivator
        week = self.get_week_json(user_id = u_id)
        training_goals = self.get_training_goals_json(u_id)
        print(training_goals)
        sentence = self.motivator.handle_request(global_goals=training_goals, week=week)
        
        return sentence



# --- Initialisation de l'application FastAPI ---
app = FastAPI(title="LLM Coach API")
BASE_URL = os.getenv("API_BASE_URL", "https://llmcoachbackend.onrender.com")

# Crée les tables si elles n'existent pas
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Schéma des requêtes ---
class ChatRequest(BaseModel):
    user_prompt: str

@app.get("/")
def root():
    return {"message": "API is running on Render"}

#Traiter l'user input
@app.post("/chat", tags=["LLM interactions"])
def chat(request: ChatRequest):
   orchestrator = Orchestrator()
   try:
       user_input = request.user_prompt
       if user_input.lower() in ["exit", "quit"]:
           return {"response" : "exit"}
       response = orchestrator.handle_request(user_input)
       print("Ready to return response from /chat endpoint")
       return {"response": response[0], "updated_week": response[1]}
   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))

@app.post("/motivational/{user_id}", tags=["LLM interactions"])
def motivational_quote(user_id: int):
    orchestrator = Orchestrator()
    try :
        response = orchestrator.get_motivational_quote(user_id)
        return {"response": response}
    except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))

#Récupérer un user
@app.post("/users/")
def get_or_create_user(user_id: int, db: Session = Depends(get_db)):
    print("Getting or creating user", user_id)
    user = db.query(User).filter(User.id == user_id).first()

    if user:
        print("User found", user_id)
        return user

    # Sinon on le crée
    print("Creating user", user_id)
    user = User(id=user_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# Récupérer une week
@app.get("/week/{user_id}", tags=["Weeks"])
def get_or_create_week(user_id: int, db: Session = Depends(get_db)):
    print("Getting or creating week for user", user_id)
    get_or_create_user(user_id, db)
    
    # Chercher la week
    week = db.query(Week).filter(Week.user_id == user_id).first()

    if not week:
        print("Creating default week for user", user_id)
        # Créer une week par défaut
        week = Week(
            user_id=user_id,
            week_number = 0,
        )
        db.add(week)
        db.commit()
        db.refresh(week)
    
    print("Returning week for user", user_id)
    return week

def call_get_week(user_id):
    return requests.get(f"{BASE_URL}/week/{user_id}")

# Ajouter une task dans un jour précis
class Task(BaseModel):
    day: str
    task: str

@app.post("/week/{user_id}/add_task", tags=["Weeks"])
def add_task(user_id: int, data: Task, db: Session = Depends(get_db)):
    week = get_or_create_week(user_id, db)
    print("week before addition:", week)
    print("week description:", week.description)
    # Ajouter la task
    week.description[data.day] = week.description[data.day] + [data.task]
    flag_modified(week, "description")
    db.commit()
    db.refresh(week)
    return week

def call_add_task(user_id, payload):
    return requests.post(f"{BASE_URL}/week/{user_id}/add_task", json=payload)


# Supprimer une task
@app.post("/week/{user_id}/delete_task", tags=["Weeks"])
def delete_task(user_id: int, data: Task, db: Session = Depends(get_db)):
    week = get_or_create_week(user_id, db)
    
    if data.task in week.description[data.day]:
        week.description[data.day].remove(data.task)
        flag_modified(week, "description")
        db.commit()
        db.refresh(week)
    return week

def call_delete_task(user_id, payload):
    return requests.post(f"{BASE_URL}/week/{user_id}/delete_task", json=payload)
                    

@app.post("/week/{user_id}/delete_day", tags=["Weeks"])
def delete_day(user_id: int, day: str, db: Session = Depends(get_db)):
    week = get_or_create_week(user_id, db)

    if day in week.description:
        week.description[day] = []
        flag_modified(week, "description")

    db.commit()
    db.refresh(week)
    return week

# Supprimer une week
@app.delete("/week/{user_id}", tags=["Weeks"])
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

# Récupérer les settings
@app.get("/settings/{user_id}", tags=["Settings"])
def get_or_create_settings(user_id: int, db: Session = Depends(get_db)):
    print("Getting or creating settings for user", user_id)
    get_or_create_user(user_id, db)
    
    # Chercher la settings
    settings = db.query(Settings).filter(Settings.user_id == user_id).first()

    if not settings:
        print("Creating default settings for user", user_id)
        # Créer une settings par défaut
        settings = Settings(
            user_id=user_id,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    print("Returning settings for user", user_id)
    return settings


#personal_goals = Column(ARRAY(String), default=list)

#Manage training_goals
#format de training_goal = {random_type_de_goal : ["goal1", "goal2"], ...}
@app.get("/settings/{user_id}/training_goals",tags=["Settings - training goal"])
def get_training_goals(user_id: int, db: Session = Depends(get_db)):
    settings = get_or_create_settings(user_id, db)
    return settings.training_goals

def call_training_goals(user_id):
    return requests.get(f"{BASE_URL}/settings/{user_id}/training_goals")

#add goal type (like "Outcome", "Learning", "Process", "Character")
@app.get("/settings/{user_id}/training_goals/{goal_type}",tags=["Settings - training goal"])
def get_or_create_training_goal_type(user_id: int, goal_type: str, db: Session = Depends(get_db)):
    settings = get_or_create_settings(user_id, db)
    content = settings.training_goals.get(goal_type, None)
    
    if content is None :
        settings.training_goals[goal_type] = []
        flag_modified(settings, "training_goals")
        db.commit()
        db.refresh(settings)
        
        return []
    
    return content

#delete goal type
@app.delete("/settings/{user_id}/training_goals/{goal_type}",tags=["Settings - training goal"])
def delete_training_goal_type(user_id:int, goal_type:str, db:Session = Depends(get_db)):
    settings = get_or_create_settings(user_id, db)
    
    if goal_type in settings.training_goals :
        settings.training_goals.pop(goal_type)
        flag_modified(settings, "training_goals")
        db.commit()
        db.refresh(settings)
    
    return settings.training_goals

class Goal(BaseModel):
    goal_type : str
    content : str

#add precise goal
@app.post("/settings/{user_id}/training_goals/{goal_type}/add",tags=["Settings - training goal"])
def add_training_goal(user_id:int, data: Goal, db:Session = Depends(get_db)):
    settings = get_or_create_settings(user_id, db)
    get_or_create_training_goal_type(user_id, data.goal_type, db)
        
    settings.training_goals[data.goal_type] = settings.training_goals[data.goal_type] + [data.content]
    flag_modified(settings, "training_goals")
    db.commit()
    db.refresh(settings)
    
    return settings.training_goals

#delete precise goal
@app.post("/settings/{user_id}/training_goals/{goal_type}/delete",tags=["Settings - training goal"])
def delete_training_goal(user_id:int, data: Goal, db:Session = Depends(get_db)):
    settings = get_or_create_settings(user_id, db)
    
    if data.goal_type in settings.training_goals :
        if data.content in settings.training_goals[data.goal_type] :
            settings.training_goals[data.goal_type].remove(data.content)
            flag_modified(settings, "training_goals")
            db.commit()
            db.refresh(settings)
    
    return settings.training_goals


#Manage coach_preferences
#format de coach_preferences = {random_type_de_preférence : ["préférence"], ...} (oui, toutes les valeurs sont des listes à max 1 élément)
@app.get("/settings/{user_id}/coach_preferences",tags=["Settings - coach"])
def get_coach_preferences(user_id: int, db: Session = Depends(get_db)):
    settings = get_or_create_settings(user_id, db)
    return settings.coach_preferences

def call_coach_preferences(user_id):
    return requests.get(f"{BASE_URL}/settings/{user_id}/coach_preferences")

#add goal type (like "Outcome", "Learning", "Process", "Character")
@app.get("/settings/{user_id}/coach_preferences/{pref_type}",tags=["Settings - coach"])
def get_or_create_training_pref_type(user_id: int, pref_type: str, db: Session = Depends(get_db)):
    settings = get_or_create_settings(user_id, db)
    content = settings.coach_preferences.get(pref_type, None)
    
    if content is None :
        settings.coach_preferences[pref_type] = []
        flag_modified(settings, "coach_preferences")
        db.commit()
        db.refresh(settings)
        
        return []
    
    return content

#delete goal type
@app.delete("/settings/{user_id}/coach_preferences/{pref_type}",tags=["Settings - coach"])
def delete_training_pref_type(user_id:int, pref_type:str, db:Session = Depends(get_db)):
    settings = get_or_create_settings(user_id, db)
    
    if pref_type in settings.coach_preferences :
        settings.coach_preferences.pop(pref_type)
        flag_modified(settings, "coach_preferences")
        db.commit()
        db.refresh(settings)
    
    return settings.coach_preferences

class Pref(BaseModel):
    pref_type : str
    content : str

#set precise pref
@app.post("/settings/{user_id}/coach_preferences/{pref_type}/set",tags=["Settings - coach"])
def set_coach_preference(user_id:int, data: Pref, db:Session = Depends(get_db)):
    settings = get_or_create_settings(user_id, db)
    get_or_create_training_pref_type(user_id, data.pref_type, db)
        
    settings.coach_preferences[data.pref_type] = [data.content]
    flag_modified(settings, "coach_preferences")
    db.commit()
    db.refresh(settings)
    
    return settings.coach_preferences

#delete precise goal
@app.post("/settings/{user_id}/coach_preferences/{pref_type}/delete",tags=["Settings - coach"])
def delete_coach_preference(user_id:int, data: Pref, db:Session = Depends(get_db)):
    settings = get_or_create_settings(user_id, db)
    
    if data.pref_type in settings.coach_preferences :
        if settings.coach_preferences[data.pref_type] == [data.content]:
            settings.coach_preferences[data.pref_type] = []
            flag_modified(settings, "coach_preferences")
            db.commit()
            db.refresh(settings)
    
    return settings.coach_preferences