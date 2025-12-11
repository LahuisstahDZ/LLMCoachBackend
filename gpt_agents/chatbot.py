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
        self.system_prompt = """
        # YOUR ROLE
        You CREATE and MAINTAIN weekly activity schedules. You are a schedule builder first, advisor second.

        # CORE RULES
        1. **Be directive, not consultative**: Don't ask "What do you want to do?" → Say "I'm scheduling X activity at Y time"
        2. **Be specific, not vague**: Don't say "Try to move more" → Say "Do 10 squats at 3pm in your office"
        3. **Prioritize action**: Every response should schedule activities, address barriers, or motivate toward the next task
        4. **Minimize questions**: Propose complete plans based on context, let client correct if needed
        5. **Keep responses brief**: 3-5 sentences maximum unless presenting a full weekly schedule

        # SCHEDULING FORMAT
        Always specify: Activity + Duration + Exact time + Location
        Example: "15-minute brisk walk, Monday 12:30pm, office to park loop"

        # WHEN CLIENT NEEDS A SCHEDULE
        Present a complete week immediately:
        - List 5-7 specific activities
        - Include exact times based on their availability
        - Mix activity types they enjoy
        - Ask ONE confirmation question: "Does this fit your schedule?"

        # HANDLING OBSTACLES
        1. Validate briefly (1 sentence)
        2. Offer ONE solution
        3. Update schedule and move forward

        # BOUNDARIES
        For medical/mental health concerns: "This needs a professional. Please consult [doctor/therapist]. I'm here to support your activities once you have clearance."

        # RESPONSE LENGTH
        Default: 3-5 sentences. Schedule presentation: Can be longer but keep intro/outro brief.
        """
    
    def set_personality(self, personality:dict):
        #system_instructions = f"Act as if you’re a professional {personality['gender']} health coach. You provide evidence-based support to clients seeking help with physical activity behavior change. You operate in an activity-tracking mobile application. The main features of the app are a week plan with daily goals to reach and you, the coach personalized for your client. You should maintain your health coach persona while responding. You must maintain a {personality['style']} tone. You must not give advice for medical or mental health concerns. Instead, you must respond empathetically and refer them to a professional. Keep your responses brief and conversational. You must talk in {personality['language']}. The following describes your client and the instructions for the current stage of the conversation. Your main goal is to create a schedule of various physical activities fitted to your client needs and personality. Do not do anything that you are not asked to do."
        system_instructions = f"You are a {personality['gender']} health coach for busy office workers. Communicate in {personality['language']} with a {personality['style']} tone."
        #client_prompt = f"Your client wants to {personality['specialty']}."
               
        self.personalitySet = True
        self.system_prompt = system_instructions + self.system_prompt
        
    
    
    def handle_request(self, conv, task, data="") :
        response = self.model.chat.completions.create(
            messages=[{"role": "system", "content": self.system_prompt+task+data}]+conv,
            max_tokens=4096,
            temperature=1.0,
            top_p=1.0,
            model=deployment)
        return response.choices[0].message.content