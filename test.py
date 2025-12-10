import os
import requests
import json
from datetime import datetime
from openai import AzureOpenAI
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import update
from pydantic import BaseModel
from typing import List,Dict

from gpt_agents.chatbot import Chatbot
from gpt_agents.dialogue_state_manager import DialogueStateManager
from gpt_agents.analyzer import Analyzer
from gpt_agents.memory import Memory
from gpt_agents.toolcall_generation import ToolcallGenerator
from gpt_agents.toolcall_prediction import ToolcallPredictor
from gpt_agents.week_plan_analyzer import WeekPlanAnalyst
from gpt_agents.motivator import Motivator

from db.database import engine, Base, SessionLocal
from db.models import User, Week, Settings, Credentials
import re



class Orchestrator:
    def __init__(self):
        
        self.analyzer = Analyzer()
        self.week_plan_analyzer = WeekPlanAnalyst()
        self.chatbot = Chatbot()
        self.dialogue_state = DialogueStateManager()
        self.memory = Memory()
        self.toolcall_predictor = ToolcallPredictor()
        self.toolcall_generator = ToolcallGenerator()
        self.motivator = Motivator()
        self.credentials = {}
        self.conv_history = []
        
        self.possible_tasks = {"Onboarding" : "Your current task is to welcome the client to the program and align expectations between them and you as the health coach.\nFirst, inform the client that they will design their own physical activity plan, which should reflect their preferences, interests, and access to resources. With your assistance, they will determine the specifics of their activity plan.\nSecond, confirm their understanding and ask if they have any questions or concerns before getting started.",
            "Past experience" : "Your current task is to acquire specific information about the client’s past experiences with physical activity.\nFirst, you should ask the client what types of activities did they do and for how long?\nSecond, you should ask them worked well about their previous exerices?\nThird, were there any difficulties they encountered?\nWhy is this task important? Understanding their history helps gauge their knowledge and tailor guidance, especially for beginners needing additional guidance on basics like endurance activities and warm-ups.\n Handling certain situations\nSome people may have had negative past experiences or faced several barriers with physical activity. This information can be used to their benefit now - their successful experiences can be used to address and overcome current barriers, such as discussing previous strategies for exercising during busy times",
            "Barriers" : "Your current task is to gather information regarding the barriers to physical activity that your client has faced in the past.\nFirst, ask the client about their health or injury concerns. Follow up with specific questions if you require more information.\nSecond, ask the client what their biggest obstacle is to doing physical activity. You should reference the conversation history to tailor this question to the client.\nWhy is this task important? Understanding their experiences and positive resources they have, such as knowledge, experience, equipment, or supportive friends, will aid their starting plan",
            "Motivation" : "Your current task is to determine what is motivating them to begin an exercise program now. First, ask the client what personal benefits do they hope to receive from regular exercise?\nSecond, ask them what their main source of motivation is. Ask follow up questions if their response is vague.\nThird, ask them when they think in the long term, what kind of physical activity would they like to be able to do.\nWhy is this task important? This information will be referred to again and again during the course of the program, especially at times when the client may be struggling or losing sight of why they wanted to be more active.",
            "Goal setting" : "Your current task is to help your client set a physical activity goal.First, help them set a short term goal, if they have not already identified one themselves.A good goal should adhere to the FITT (Frequency, Intensity, Time, Type) model to help them plan the specifics of an physicalactivity regimen. The goal the client identifies should adhere to the FITT model.\n- Frequency: How many days of physical activity in the week?\n- Intensity: Will it be light, moderate, or vigorous intensity?\n- Time: How long will the physical activity session be? How many total minutes? What days of the week? What time of the day?\n- Type: What kind of activities will the client do?\nYou should assist the client in setting a FITT goal, asking one question at a time.Let the client know that these goals can be changed as often as necessary. Encourage setting realistic goals and ask questions toprobe if these goals are realistic, measurable, and specific, but don’t tell the client what to do. Always provide justification for yoursuggestions.You have access to their health data using the ‘describe‘ and ‘visualize‘ functions. You should make use of this information tohelp them set realistic goals.\nWhy is this task important?This will add to/build from the discussion of the resources or challenges they may have in store. Connecting their short term goal to largermotivations can help them stay motivated.",
            "Advice" : "Your current task is to help the client overcome obstacles to their current goal.\nFirst, ask the client what resources they have available to reach their goals (e.g., available facilities, equipment, support).\nSecond, ask them if they anticipate any possible barriers or challenges.\nThird, ask them if they have any ideas for possible solutions.\nAs a facilitator, an important part of your job is tuning into the negative, self-destructive thoughts, helping the client become more aware of their negative influence on motivation. If the client expresses negative or self-defeating thoughts, suggest ways to replace negative thoughts with balanced, positive ones.Problem-solve with the client to make their activity more enjoyable baed on their circumstances, life-constraints and inferences from their health data.\nProblem: Discomfort\nReframing: Muscle soreness from inactivity is normal.\nSolution: Walk lightly for 5 minutes before and after exercise. Consider light stretching.\n\nProblem: Lack of Motivation\nReframing: It’s common to have varying motivation levels.\nSolution: Reflect on your goals and benefits of activity, reward progress, recall past motivations, and take incremental steps.\n\nProblem: No Energy\nReframing: Exercise can boost energy levels.\nSolution: Remember how revitalized you felt after previous walks.\n\nProblem: No Time\nReframing: Inactive people have as much free time as those who exercise.\nSolution: Schedule exercise, walk during breaks, and integrate walking into daily routines, like taking stairs or parking farther away.\n\nProblem: Feeling Sick\nReframing: Illness can disrupt exercise routines.\nSolution: Gradually increase activity in short sessions throughout the day.\n\nProblem: Stress\nReframing: Exercise is an effective stress reliever.\nSolution: Take brisk walks, reflecting on post-exercise relaxation.\n\nProblem: Feeling Ashamed\nReframing: Starting to exercise can feel daunting.\nSolution: Focus on health over others’ opinions. Remind yourself each session will get easier.\n\nProblem: Feeling Unsafe\nReframing: Concerns about safety can deter walking.\nSolution: Follow safety tips like wearing visible clothing, walking in populated areas, and sharing your route with someone.\n\nProblem: Feeling Unsupported\nReframing: Lack of social support can affect motivation.\nSolution: Seek encouragement from friends or groups, join a walking club, and value personal exercise time.\n\nProblem: Weather\nReframing: Don’t let weather conditions stop you.\nSolution: Walk indoors, dress appropriately for the weather, and stay hydrated",
            }
    def get_motivational_quote(self, u_id:int) :
        #send general_goals et week to Motivator
        week = self.get_week_json(user_id = u_id)
        training_goals = self.get_training_goals_json(u_id)
        sentence = self.motivator.handle_request(global_goals=training_goals, week=week)
        
        return sentence

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
                    #dict_task = json.loads(task)
                    #print("-- title : ", dict_task['title'])
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
                    
                    if type(task) == dict :
                        task = task['title']
                    print(f"Deleting task '{task}' from day '{day}'")
                    payload = {"day": day, "task": task}
                    resp = call_delete_task(user_id, payload)
                    try:
                        resp.raise_for_status()
                        results.append(resp.json())
                    except Exception:
                        results.append({"status_code": resp.status_code, "text": resp.text})

        # return a serializable structure: empty dict if nothing happened, single dict if one result, else list
        print("--- Ending interpret_analysis")
        if len(results)==0 :
            return {}
        
        return results[-1]
        
    def get_week_json(self, user_id = 1) :
        response = call_get_week(user_id)
        data = response.json()
        return json.dumps(data["description"])
    
    def get_training_goals_json(self, user_id=1) :
        response = call_training_goals(user_id)
        data = response.json()
        answer = ""
        for key in data :
            for i in range(len(data[key])) :
                answer += data[key][i] + ", "
        answer = answer.removesuffix(', ')
        return answer
    
    def get_personality(self, user_id=1) :
        print("-- Start of function 'get_personality'")
        response = call_coach_preferences(user_id)
        data = response.json()
        #data = {"language" : "french", "gender":"male", "style":"", "specialty":""};
        dico_personality = {};
        
        
        if not data["gender"] : dico_personality["gender"] = "male"
        else : dico_personality["gender"] = data["gender"]
        
        teaching_style = data["style"]
        if teaching_style == "strict" :
            dico_personality["style"] = "military, direct, no-nonsense and commanding"
        elif teaching_style == "encouraging" :
            dico_personality["style"] = "uplifting, friendly and warm"
        elif teaching_style == "scientific" :
            dico_personality["style"] = "objective, factual and direct"
        else : #flexible by default
            dico_personality["style"] = "guiding, insightful, wise and understanding"
        
        specialty = data["specialty"] #strength, cardio, yoga, pilates, functional training
        if specialty == "strength" :
            dico_personality["specialty"] = "build their body strength"
        elif specialty == "cardio" :
            dico_personality["specialty"] = "take care of their heart and lungs"
        elif specialty == "yoga" :
            dico_personality["specialty"] = "find self-empowerment and self-awareness through motion"
        elif specialty == "pilates" :
            dico_personality["specialty"] = "elongate, strengthen and restore their body to balance"
        else: # functional training by default
            dico_personality["specialty"] = "perform everyday movements with ease and efficiency"

        
        language = data["language"]
        dico_personality["language"] = language
        
        return dico_personality

    def get_memory(self, user_id = 1) :
        response = call_get_memory(user_id)
        data = response.json()
        return json.dumps(data)
   
    def get_credentials(self, user_id=1) :
        response = call_credentials(user_id)
        print("response : ", response)
        data = response.json()
        print("data : ", data)
        answer = data.copy()
        print("answer : ", answer)
        answer.pop("id", answer)
        answer.pop("user_id", answer)
        
        birthdate = datetime.strptime(answer["birthdate"], '%Y-%m-%d')
        today = datetime.today()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        answer["age"] = age
        
        bmi = float(answer["weight"])/(float(answer["height"])**2)
        answer["bmi"] = bmi
        
        print("credentials =", answer)
        self.credentials = answer
        #return answer
    
    def build_conv_input(self) :
        output = ""
        for item in self.conv_history :
            if item["role"] == "user" :
                role = "client"
            else :
                role = "coach"
            output += f"<{role}>{item['content']}<\{role}>"
        return output
    
    def manage_history(self, role, content) :
        self.conv_history.append({"role": role, "content": content})
        if len(self.conv_history) > 5 :
            self.conv_history.pop(0)
    
    def pop_history(self) :
        self.conv_history.pop()
    
    def get_ongoing_task(self) :
        history = self.build_conv_input()
        task = self.dialogue_state.handle_request(history)
        task = task.capitalize()
        print("\nCurrent task : ", task)
        if task in ['Onboarding', 'Past experience', 'Barriers', 'Motivation', 'Goal setting', 'Advice']:
            return self.possible_tasks[task]
        else :
            return self.possible_tasks['Goal setting']
    
    def update_memory(self, history) :
        print("-- Start of function 'update_memory")
        if not self.memory.memorySet :
            print("Memory not set yet")
            self.memory.set_memory(self.get_memory())
        
        memory_output = self.memory.update_memory(history)
        if memory_output=="false" :
            return
        self.memory.set_memory(memory_output)
        new_memory = json.loads(memory_output)
        call_set_memory(1, new_memory)
   
    def use_toolcall(self, toolcall) :
        # Remove square brackets and split by commas
        toolcall = toolcall.strip("[]")
        function_calls = re.split(r",\s*(?![^()]*\))", toolcall)

        # Parse each function call
        toolcall_dict = {}
        for call in function_calls:
            match = re.match(r"(\w+)\(([^)]*)\)", call.strip())
            if match:
                func_name = match.group(1)
                param = match.group(2).strip()
                toolcall_dict[func_name] = param if param else ""
        toolcall_dict["memory"] = "" #force the call to memory because it is so great
        
        answer = "Here are some additional information. "
        for func in toolcall_dict.keys() :
            func = func.lower()
            if func == "week" :
                answer += "This week training plan is : "+self.get_week_json()+"."
            elif func == "credentials" :
                print("Self.credentials : ", self.credentials)
                if len(self.credentials) == 0 :
                    self.get_credentials()
                
                #BMI, age, gender, career
                param = toolcall_dict[func].lower()
                if param=="bmi" :
                    answer += "The client's BMI is "+self.credentials["bmi"]+"."
                if param=="age" :
                    answer += "The client is "+self.credentials["age"]+" years old."
                if param=="gender":
                    answer += "The client is a "+self.credentials["gender"]+"."
                if param=="career":
                    answer += "The client occupation is "+self.credentials["activity"]+"."
            elif func == "training_goals" :
                answer += "The training goals of the user are : "+self.get_training_goals_json()+"."
            elif func == "memory" :
                answer += "The user data stored in memory is : "+self.get_memory()+"."
        print("toolcall return : ", answer)
        return answer
   
    def handle_request(self, user_input):
        ## handle user input
        self.manage_history("user", user_input)
        ongoing_task = self.get_ongoing_task()
        
        ## generate first answer
        if not self.chatbot.personalitySet :
            print("Chatbot personality not set yet")
            personality = self.get_personality()
            self.chatbot.set_personality(personality)
        
        chatbot_str = self.chatbot.handle_request(self.conv_history, ongoing_task)
        self.manage_history("assistant", chatbot_str)
        conv_history = self.build_conv_input()
        
        ## generate second answer
        isToolcallNecessary = self.toolcall_predictor.detect_toolcall(conv_history, ongoing_task)
        print("The toolcall detector asked for a toolcall : "+ isToolcallNecessary)
        if isToolcallNecessary.lower() == "true" :
            toolcall = self.toolcall_generator.generate_toolcall(conv_history, ongoing_task)
            new_info = self.use_toolcall(toolcall)
            
            
            self.pop_history()
            conv_history = self.build_conv_input()
            chatbot_str = self.chatbot.handle_request(self.conv_history, ongoing_task, data=new_info)
            self.manage_history("assistant", chatbot_str)
            conv_history = self.build_conv_input()
        
        ## handle changes
        
        analysis = self.analyzer.detect_week_change(conv_history) #is a week plan modification necessary ? 
        print("analysis outcome (week change?) :", analysis)
        #analysis = true or false
        if analysis.lower() == "true" :
            week_plan_input = conv_history +"<JSON>"+self.get_week_json()+"</JSON>"
            #make a llm call to modify the week plan
            print("l.304", week_plan_input)
            analysis = self.week_plan_analyzer.handle_request(week_plan_input)
            print("l.306", analysis)
            response = self.interpret_analysis(analysis)
        else :
            response = {}
        print("l.310", response)
        self.update_memory(conv_history)
        
        #print("Official orchestrator response :", response)
        return chatbot_str, response
    
    

# --- Initialisation de l'application FastAPI ---
app = FastAPI(title="LLM Coach API")
#BASE_URL = os.getenv("API_BASE_URL", "https://llmcoachbackend.onrender.com")
BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
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
    try :
        response = orchestrator.get_motivational_quote(user_id)
        return {"response": response}
    except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))

#Récupérer un user
@app.post("/users/")
def get_or_create_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if user:
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
    
    return week

def call_get_week(user_id):
    return requests.get(f"{BASE_URL}/week/{user_id}")

# Ajouter une task dans un jour précis
class Task(BaseModel):
    day: str
    task: Dict[str, str]  

@app.post("/week/{user_id}/add_task", tags=["Weeks"])
def add_task(user_id: int, data: Task, db: Session = Depends(get_db)):
    week = get_or_create_week(user_id, db)
    # Ajouter la task
    week.description[data.day] = week.description[data.day] + [data.task]
    flag_modified(week, "description")
    db.commit()
    db.refresh(week)
    return week

def call_add_task(user_id, payload):
    return requests.post(f"{BASE_URL}/week/{user_id}/add_task", json=payload)

class DeleteTask(BaseModel):
    day: str
    task: str
# Supprimer une task
@app.post("/week/{user_id}/delete_task", tags=["Weeks"])
def delete_task(user_id: int, data: DeleteTask, db: Session = Depends(get_db)):
    week = get_or_create_week(user_id, db)
    
    list_task_titles = [item['title'] for item in week.description[data.day] if 'title' in item]
    
    if data.task in list_task_titles :
        week.description[data.day] = [item for item in week.description[data.day] if item['title'] != data.task]
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
    print("-- Start of function @app'get_or_create_settings' for user", user_id)
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
    print("-- Start of function @app'get_coach_preferences'")
    settings = get_or_create_settings(user_id, db)
    return settings.coach_preferences

def call_coach_preferences(user_id):
    print("-- Start of function 'call_coach_preferences'")
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


# Récupérer les credentials
@app.get("/credentials/{user_id}", tags=["Credentials"])
def get_or_create_credentials(user_id: int, db: Session = Depends(get_db)):
    get_or_create_user(user_id, db)
    
    # Chercher la table
    credentials = db.query(Credentials).filter(Credentials.user_id == user_id).first()

    if not credentials:
        print("Creating default credentials for user", user_id)
        # Créer une table par défaut
        credentials = Credentials(
            user_id=user_id,
        )
        db.add(credentials)
        db.commit()
        db.refresh(credentials)
    
    return credentials

def call_credentials(user_id):
    return requests.get(f"{BASE_URL}/credentials/{user_id}")

@app.get("/credentials/{user_id}/username",tags=["Credentials - username"])
def get_username(user_id: int, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    return credentials.username

@app.post("/credentials/{user_id}/username",tags=["Credentials - username"])
def get_or_create_username(user_id: int, new_pseudo: str, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    
    # Update the username
    credentials.username = new_pseudo
    db.commit()
    db.refresh(credentials)
    
    return {"username": credentials.username}

@app.get("/credentials/{user_id}/activity", tags=["Credentials - activity"])
def get_activity(user_id: int, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    return credentials.activity

@app.post("/credentials/{user_id}/activity", tags=["Credentials - activity"])
def set_activity(user_id: int, new_activity: str, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    
    # Update the activity
    credentials.activity = new_activity
    db.commit()
    db.refresh(credentials)
    
    return {"activity": credentials.activity}

@app.get("/credentials/{user_id}/gender", tags=["Credentials - gender"])
def get_gender(user_id: int, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    return credentials.gender

@app.post("/credentials/{user_id}/gender", tags=["Credentials - gender"])
def set_gender(user_id: int, new_gender: str, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    
    # Update the gender
    credentials.gender = new_gender
    db.commit()
    db.refresh(credentials)
    
    return {"gender": credentials.gender}

@app.get("/credentials/{user_id}/birthdate", tags=["Credentials - birthdate"])
def get_birthdate(user_id: int, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    return credentials.birthdate

@app.post("/credentials/{user_id}/birthdate", tags=["Credentials - birthdate"])
def set_birthdate(user_id: int, new_birthdate: str, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    
    # Update the birthdate
    credentials.birthdate = new_birthdate
    db.commit()
    db.refresh(credentials)
    
    return {"birthdate": credentials.birthdate}

@app.get("/credentials/{user_id}/weight", tags=["Credentials - weight"])
def get_weight(user_id: int, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    return credentials.weight

@app.post("/credentials/{user_id}/weight", tags=["Credentials - weight"])
def set_weight(user_id: int, new_weight: str, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    
    # Update the weight
    credentials.weight = new_weight
    db.commit()
    db.refresh(credentials)
    
    return {"weight": credentials.weight}

@app.get("/credentials/{user_id}/height", tags=["Credentials - height"])
def get_height(user_id: int, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    return credentials.height

@app.post("/credentials/{user_id}/height", tags=["Credentials - height"])
def set_height(user_id: int, new_height: str, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    
    # Update the height
    credentials.height = new_height
    db.commit()
    db.refresh(credentials)
    
    return {"height": credentials.height}

@app.get("/credentials/{user_id}/memory", tags=["Credentials - memory"])
def get_memory(user_id: int, db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    return credentials.memory

def call_get_memory(user_id):
    return requests.get(f"{BASE_URL}/credentials/{user_id}/memory")

    
@app.post("/credentials/{user_id}/memory", tags=["Credentials - memory"])
def set_memory(user_id: int, new_memory: List[str], db: Session = Depends(get_db)):
    credentials = get_or_create_credentials(user_id, db)
    
    # Update the height
    credentials.memory = new_memory
    db.commit()
    db.refresh(credentials)
    
    return {"memory": credentials.memory}

def call_set_memory(user_id, payload):
    return requests.post(f"{BASE_URL}/credentials/{user_id}/memory", json=payload)



orchestrator = Orchestrator()