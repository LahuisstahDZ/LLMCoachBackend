#from sensitive import subscription_key
from openai import AzureOpenAI
import os
from dotenv import load_dotenv

load_dotenv()
subscription_key = os.getenv('AZURE_API_KEY')

endpoint = "https://gpt-coach-v1-resource.cognitiveservices.azure.com/openai/deployments/gpt-35-turbo/chat/completions?api-version=2025-01-01-preview"
model_name = "gpt-35-turbo"
deployment = "gpt-35-turbo"
api_version = "2025-01-01-preview"



class Analyzer:
    def __init__(self):
        self.model = AzureOpenAI(
			api_version=api_version,
			azure_endpoint=endpoint,
			api_key=subscription_key,
		)
        self.system_prompt ="You are a conversation analyst. You have to analyze an ongoing conversation between a health coach and their client. "
        self.system_prompt_conclusion = "Failing to do a modification is worse than an unnecessary change. Answer only one word : true or false."
        #self.system_prompt = "You are a sentence analyst. You analyze the user prompt and return a boolean stating if the condition is met. If the user prompt contains 'banana' you have to return True. If the user prompt does not contain 'banana' you have to return False."


    def detect_week_change(self, user_input) :
        full_prompt = self.system_prompt + "The client has a physical activity schedule with multiple goals they should achieve for the week. You have to detect if the conversation may leads to a modificaton of the schedule. You have to answer 'true' if the schedule may have to be modified to match the conversation. You should answer 'false' if the conversation does not imply a change in the physical activites schedule. "
        full_prompt += self.system_prompt_conclusion
        response = self.model.chat.completions.create(
        messages=[{"role": "system", "content": full_prompt}, {"role": "user", "content": user_input}],
        max_tokens=4096,
        temperature=1.0,
        top_p=1.0,
        model=deployment)
        return response.choices[0].message.content