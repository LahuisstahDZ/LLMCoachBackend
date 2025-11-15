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
        self.system_prompt = "You are a writer. You take in entry a boolean, True or False. If True you have to say how much you love the bananas. If False you have to scream BANANA"


    def handle_request(self, user_input) :
        response = self.model.chat.completions.create(
        messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user_input}],
        max_tokens=4096,
        temperature=1.0,
        top_p=1.0,
        model=deployment)
        return response.choices[0].message.content