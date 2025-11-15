import os
from openai import AzureOpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from gpt_agents.chatbot import Chatbot
from gpt_agents.analyzer import Analyzer


class Orchestrator:
    def __init__(self):
        self.analyzer = Analyzer()
        self.chatbot = Chatbot()

    def handle_request(self, user_input):
        chatbot_str = self.chatbot.handle_request(user_input)
        analysis_input = "<client>"+user_input+"</client>"+"<coach>"+chatbot_str+"</coach>"+"<JSON>"+"</JSON>"
        analysis = self.analyzer.handle_request(analysis_input)
        action, toolcall = analysis.split(sep=";", maxsplit=2)
        
        return chatbot_str, action, toolcall



# --- Initialisation de l'application FastAPI ---
app = FastAPI(title="LLM Coach API")

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

