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
        analysis = self.analyzer.handle_request(user_input)
        
        return self.chatbot.handle_request(analysis)



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
       return {"response": response}
   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))


# def chat(request: ChatRequest):
#     try:   
#         response = client.chat.completions.create(
#             messages=[
#                 {
#                     "role": "system",
#                     "content": "Your have to introduce yourself as a health coach if you have not already. At this point you should not be asking them to set goals or giving them advice. Your current task is to welcome the client to the program and align expectations between them and you as the health coach. First, inform the client that they will design their own physical activity plan, which should reflect their preferences, interests, and access to resources. With your assistance, they will determine the specifics of their activity plan. Second, confirm their understanding and ask if they have any questions or concerns before getting started.",
                    
#                 },
#                 {
#                     "role": "user",
#                     "content": request.user_prompt,
#                 },
#             ],
#             max_tokens=512, #modifié
#             temperature=1.0,
#             top_p=1.0,
#             model=deployment
#         )

#         ai_message = response.choices[0].message.content
#         return {"response": ai_message}
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    
