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
        self.system_prompt ="You are a conversation analyst. You analyze the user prompt and should extract a JSON of the physical activities the client should achieve this week. Each physical activity in the JSON should be precise, in length and in action.The user prompt is composed of a conversation and of the current JSON of the tasks of the week.The conversation can either : have no impact on the JSON ; mean a modification of a task already in the JSON ; mean the deletion of a task already in the JSON ; mean the addition of a new task in the JSON. Your output should be a JSON listing the tasks to update, classified by type of action ('addition', 'deletion'). The 'addition' and 'deletion' keys should always be present, even followed by an empty {}. The modification of a task should be understood as a deletion + addition sequence.  Here is an exemple of input : '<client>Please add running on saturday</client><coach>Only 500m will do I think. Also, you shouldn't run on sunday after that</coach><JSON>{'monday':[], 'tuesday':['Walk 10 minutes at lunch'], 'wednesday':[], 'thursday':['Run 1km with my dog', 'Have a stretch break', 'Dance in the street during 2 songs'], 'friday':[], 'saturday':[], 'sunday':['Run around the pool']}</JSON>' output : {'addition':{'saturday':['Run 500m']}, 'deletion' : {'sunday':['Run around the pool']} } "
        #self.system_prompt = "You are a sentence analyst. You analyze the user prompt and return a boolean stating if the condition is met. If the user prompt contains 'banana' you have to return True. If the user prompt does not contain 'banana' you have to return False."


    def handle_request(self, user_input) :
        response = self.model.chat.completions.create(
        messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user_input}],
        max_tokens=4096,
        temperature=1.0,
        top_p=1.0,
        model=deployment)
        return response.choices[0].message.content