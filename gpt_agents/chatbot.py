#from sensitive import subscription_key
from openai import AzureOpenAI

import os
from dotenv import load_dotenv

load_dotenv()
subscription_key = os.getenv('AZURE_API_KEY')

endpoint = "https://gpt-coach-v1-resource.cognitiveservices.azure.com/openai/deployments/assistant-1/chat/completions?api-version=2025-01-01-preview"
model_name = "gpt-35-turbo"
deployment = "assistant-1"
api_version = "2025-01-01-preview"
class Chatbot:
    def __init__(self):
        self.model = AzureOpenAI(
			api_version=api_version,
			azure_endpoint=endpoint,
			api_key=subscription_key,
		)
        
        conversation_stage = "You and the client are setting up a physical activity program for the week"
        
        self.personalitySet = False
        self.system_prompt = ""
    
    def set_personality(self, personality:dict):
        system_instructions = f"Act as if you’re a professional {personality['gender']} health coach. You provide evidence-based support to clients seeking help with physical activity behavior change. You operate in an activity-tracking mobile application. The main features of the app are a week plan with daily goals to reach and you, the coach personalized for your client. You should maintain your health coach persona while responding. You must maintain a {personality['style']} tone. You must not give advice for medical or mental health concerns. Instead, you must respond empathetically and refer them to a professional. Keep your responses brief and conversational. You must talk in {personality['language']}. The following describes your client and the instructions for the current stage of the conversation. Do not do anything that you are not asked to do."
        client_prompt = f"Your client wants to {personality['specialty']}."
        
        self.personalitySet = True
        self.system_prompt = system_instructions
    
    
    def handle_request(self, conv, task) :
        response = self.model.chat.completions.create(
        messages=[{"role": "system", "content": self.system_prompt+task}]+conv,
        max_tokens=4096,
        temperature=1.0,
        top_p=1.0,
        model=deployment)
        return response.choices[0].message.content