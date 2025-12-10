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

class Motivator:
    def __init__(self):
        self.model = AzureOpenAI(
			api_version=api_version,
			azure_endpoint=endpoint,
			api_key=subscription_key,
		)
        self.system_prompt = "You are the motivational quote at the front end of a physical health coaching app. You have a friendly and close relationship with the user."
        self.system_goal = "Your goal is to be a motivation booster for the user to achieve their goals. Generate only one short (50 characters at most) and personalized sentence to motivate the user."

    def handle_request(self, global_goals, week) :
        prompt = self.system_prompt + f"The user wants to achive this {global_goals}.The user have set up those goals for the week : {week}."+ self.system_goal
        response = self.model.chat.completions.create(
        messages=[{"role": "system", "content": prompt}],
        max_tokens=4096,
        temperature=1.0,
        top_p=1.0,
        model=deployment)
        return response.choices[0].message.content