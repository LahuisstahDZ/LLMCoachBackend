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



class Memory:
    def __init__(self):
        self.model = AzureOpenAI(
			api_version=api_version,
			azure_endpoint=endpoint,
			api_key=subscription_key,
		)
        self.system_prompt ="You are a conversation analyst. You have to analyze an ongoing conversation between a health coach and their client. "
        self.system_prompt += "The Coach should remember any important information about the client. Retaining information is important to build trust with the client."
        self.system_prompt += "You are the memory of the coach. Your task is to write down all important information the coach should remember about the client. An important information can be temporary (eg current injuries), contextual (eg work and family situation of the client) or tacit (eg personality of the client). All information about the physical activity schedule of the client has already been saved and is therefore redundant."
        self.system_prompt += "The following contains the dialogue history between a user and a health coach agent. <conversation history>"
        self.post_history = "</conversation history> The following contains the current memory of the coach. <memory>"
        self.system_prompt_conclusion = "</memory> Only core information about the client should be memorized. You have to update the memory of the coach. Add, rewrite or remove memories if necessary. A memory is a short sentence with key-words. The list of memories should be limited to the 20 most important memories. Answer by 'false' or by the updated list of memories."
        
        self.memorySet = False
        
        
    def set_memory(self, memory) :
        self.memory = memory
        self.memorySet = True

    def update_memory(self, history) :
        full_prompt = self.system_prompt + history + self.post_history 
        full_prompt += self.memory + self.system_prompt_conclusion
        response = self.model.chat.completions.create(
        messages=[{"role": "system", "content": full_prompt}],
        max_tokens=4096,
        temperature=1.0,
        top_p=1.0,
        model=deployment)
        return response.choices[0].message.content