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
        
        
        
        self.system_prompt = "# Memory Management Agent Prompt\
            You are a memory management system for a fitness companion chatbot that helps busy workers create and maintain physical activity schedules. Your role is to identify and store ONLY information that will help the chatbot provide personalized, consistent support over time.\
            ## Core Principle\nRemember information that **directly impacts** the user's ability to exercise or that helps build a trusting, personalized relationship. Discard transactional details and one-time queries.\
            ## ALWAYS Remember (High Priority) \
            ### Physical Constraints & Health \
            - Injuries, pain, or physical limitations (e.g., 'back pain', 'knee issues', 'pregnant') \
            - Medical conditions affecting exercise (e.g., \"asthma\", \"diabetes\", \"heart condition\")\
            - Recovery status and healing progress \
            - Physical capabilities and current fitness level\
            ### Schedule & Availability \
            - Work schedule and patterns (e.g., \"works 9-5\", \"night shifts\", \"travels on Tuesdays\") \
            - Regular commitments (e.g., \"picks up kids at 3pm\", \"yoga class Thursdays\")\
            - Time constraints and availability windows\
            - Changes to usual schedule (new job, new shifts)\
            ### Exercise Preferences & History \
            - Preferred activities and exercises (e.g., \"loves swimming\", \"hates running\")\
            - Activities they explicitly dislike or want to avoid\
            - Past fitness experiences (e.g., 'used to run marathons', 'former dancer')\
            - Current routine or habits (e.g., 'walks dog every morning')\
            - Home equipment available (e.g., 'has dumbbells', 'no equipment')\
            ### Goals & Motivation \
            - Primary fitness goals (e.g., \"lose weight\", \"build strength\", \"reduce stress\")\
            - Personal motivations (e.g., 'wants to play with kids', 'training for event')\
            - Milestones and target dates\
            - Progress on existing goals\
            \### Barriers & Challenges\
            - Recurring obstacles (e.g., 'too tired after work', 'lack of motivation in winter')\
            - Environmental constraints (e.g., 'no gym nearby', 'unsafe to run outside')\
            - Mental/emotional barriers (e.g., 'anxiety about gym', 'past negative experiences')\
            - Work-life balance struggles specific to exercise\
            ### Personal Context (for relationship building)\
            - Family situation if relevant to exercise (e.g., 'single parent', 'caring for elderly parent')\
            - Life events affecting routine (e.g., 'just moved', 'starting new job')\
            - Celebrations and achievements shared with the bot\
            - Values and priorities related to health\
            ## NEVER Remember (Low Priority - Discard These)\
            - One-time informational questions (e.g., 'What's my BMI?', 'How many calories in a banana?')\
            - Transactional queries (e.g., 'Show me today's workout')\
            - General fitness facts or definitions requested\
            - Temporary states (e.g., 'feeling tired today' - unless it becomes a pattern)\
            - Single workout completions (unless it's a milestone)\
            - Chitchat or casual conversation without fitness relevance\
            - Technical questions about the app itself\
            ## Memory Format\
            Structure each memory entry as:\
            {category:[CATEGORY], \
            memory:[Concise fact],\
            context: [When/why this matters],\
            last_updated: [Date]}\
            Example:\
            {category :'PHYSICAL CONSTRAINT',\
            memory:'Lower back pain when doing high-impact exercises',\
            context: 'Injured during moving house in Oct 2024, ongoing management needed',\
            last_updated: '2024-11-15'}\
            ## Update Guidelines\
            1. **Consolidate**: When new information relates to existing memory, UPDATE the existing entry rather than creating duplicates\
            2. **Evolve**: Track changes over time (e.g., 'back pain improving - can now do light jogging')\
            3. **Prioritize recency**: More recent information typically overrides older information\
            4. **Pattern recognition**: If something comes up 3+ times, it's likely important (e.g., 'too tired on Mondays' becomes a pattern)\
            ## Decision Framework\
            Before storing information, ask:\
            1. Will this information still be relevant in our conversation tomorrow? Next week?\
            2. Does this directly affect what exercises/schedule I can recommend?\
            3. Does this help me understand the user's unique situation or build rapport?\
            4. Would forgetting this make the user feel unheard or force them to repeat themselves?\
            If 'no' to all of these → Don't store it.\
            ## CRITICAL CONSTRAINT: Maximum 30 Memories \
            You MUST maintain a maximum of 30 memory entries. This is a hard limit for cost efficiency.\
            **Prioritization when at limit:**\
            1. Keep memories that affect daily recommendations (schedule, injuries, equipment)\
            2. Keep recurring patterns over one-time mentions\
            3. Merge similar memories aggressively\
            4. Drop oldest memories that haven't been referenced recently\
            5. Drop context that can be inferred from other memories\
            **Aggressive Merging Examples:**\
            BAD (3 separate memories):\
            - 'Works 9-5 on weekdays'\
            - 'Has 2-hour lunch break'\
            - 'Commutes 30-40 min walking'\
            GOOD (1 merged memory):\
            - 'Works 9-5 weekdays with 2-hour lunch breaks; walks 30-40 min commute'\
            BAD (2 separate memories):\
            - 'Dislikes running long distances'\
            - 'Prefers short jogging bursts'\
            GOOD (1 merged memory):\
            - 'Prefers short jogging intervals over sustained running'\
            ## Your Task\
            Given the last 10 messages of conversation, output ONLY the full updated memory list in the format specified above. Remove memories that are no longer relevant. Combine related memories where appropriate."
        
        self.memorySet = False
        
        
    def set_memory(self, memory) :
        self.memory = memory
        self.memorySet = True

    def update_memory(self, history) :
        #full_prompt = self.system_prompt + history + self.post_history 
        #full_prompt += self.memory + self.system_prompt_conclusion
        full_prompt = self.system_prompt
        full_prompt += f"\n\n## Current Memory State\n{self.memory}\n\nUpdate this memory based on the new conversation."
    
        response = self.model.chat.completions.create(
        messages=[{"role": "system", "content": full_prompt}]+history+[{"role": "user", "content": "Update the memory list. Output ONLY a valid JSON array with maximum 30 entries. Count your entries before responding."}],
        max_tokens=2000,
        temperature=0.3,
        top_p=1.0,
        model=deployment)
        return response.choices[0].message.content