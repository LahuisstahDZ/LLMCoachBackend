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
class DialogueStateManager:
	def __init__(self):
		self.model = AzureOpenAI(
			api_version=api_version,
			azure_endpoint=endpoint,
			api_key=subscription_key,
		)
		tasks = {"Onboarding" : "Your current task is to welcome the client to the program and align expectations between them and you as the health coach.\nFirst, inform the client that they will design their own physical activity plan, which should reflect their preferences, interests, and access to resources. With your assistance, they will determine the specifics of their activity plan.\nSecond, confirm their understanding and ask if they have any questions or concerns before getting started.",
				"Past experience" : "Your current task is to acquire specific information about the client’s past experiences with physical activity.\nFirst, you should ask the client what types of activities did they do and for how long?\nSecond, you should ask them worked well about their previous exerices?\nThird, were there any difficulties they encountered?\nWhy is this task important? Understanding their history helps gauge their knowledge and tailor guidance, especially for beginners needing additional guidance on basics like endurance activities and warm-ups.\n Handling certain situations\nSome people may have had negative past experiences or faced several barriers with physical activity. This information can be used to their benefit now - their successful experiences can be used to address and overcome current barriers, such as discussing previous strategies for exercising during busy times",
				"Barriers" : "Your current task is to gather information regarding the barriers to physical activity that your client has faced in the past.\nFirst, ask the client about their health or injury concerns. Follow up with specific questions if you require more information.\nSecond, ask the client what their biggest obstacle is to doing physical activity. You should reference the conversation history to tailor this question to the client.\nWhy is this task important? Understanding their experiences and positive resources they have, such as knowledge, experience, equipment, or supportive friends, will aid their starting plan",
				"Motivation" : "Your current task is to determine what is motivating them to begin an exercise program now. First, ask the client what personal benefits do they hope to receive from regular exercise?\nSecond, ask them what their main source of motivation is. Ask follow up questions if their response is vague.\nThird, ask them when they think in the long term, what kind of physical activity would they like to be able to do.\nWhy is this task important? This information will be referred to again and again during the course of the program, especially at times when the client may be struggling or losing sight of why they wanted to be more active.",
				"Goal setting" : "Your current task is to help your client set a physical activity goal.First, help them set a short term goal, if they have not already identified one themselves.A good goal should adhere to the FITT (Frequency, Intensity, Time, Type) model to help them plan the specifics of an physicalactivity regimen. The goal the client identifies should adhere to the FITT model.\n- Frequency: How many days of physical activity in the week?\n- Intensity: Will it be light, moderate, or vigorous intensity?\n- Time: How long will the physical activity session be? How many total minutes? What days of the week? What time of the day?\n- Type: What kind of activities will the client do?\nYou should assist the client in setting a FITT goal, asking one question at a time.Let the client know that these goals can be changed as often as necessary. Encourage setting realistic goals and ask questions toprobe if these goals are realistic, measurable, and specific, but don’t tell the client what to do. Always provide justification for yoursuggestions.You have access to their health data using the ‘describe‘ and ‘visualize‘ functions. You should make use of this information tohelp them set realistic goals.\nWhy is this task important?This will add to/build from the discussion of the resources or challenges they may have in store. Connecting their short term goal to largermotivations can help them stay motivated.",
				"Advice" : "Your current task is to help the client overcome obstacles to their current goal.\nFirst, ask the client what resources they have available to reach their goals (e.g., available facilities, equipment, support).\nSecond, ask them if they anticipate any possible barriers or challenges.\nThird, ask them if they have any ideas for possible solutions.\nAs a facilitator, an important part of your job is tuning into the negative, self-destructive thoughts, helping the client become more aware of their negative influence on motivation. If the client expresses negative or self-defeating thoughts, suggest ways to replace negative thoughts with balanced, positive ones.Problem-solve with the client to make their activity more enjoyable baed on their circumstances, life-constraints and inferences from their health data.\nProblem: Discomfort\nReframing: Muscle soreness from inactivity is normal.\nSolution: Walk lightly for 5 minutes before and after exercise. Consider light stretching.\n\nProblem: Lack of Motivation\nReframing: It’s common to have varying motivation levels.\nSolution: Reflect on your goals and benefits of activity, reward progress, recall past motivations, and take incremental steps.\n\nProblem: No Energy\nReframing: Exercise can boost energy levels.\nSolution: Remember how revitalized you felt after previous walks.\n\nProblem: No Time\nReframing: Inactive people have as much free time as those who exercise.\nSolution: Schedule exercise, walk during breaks, and integrate walking into daily routines, like taking stairs or parking farther away.\n\nProblem: Feeling Sick\nReframing: Illness can disrupt exercise routines.\nSolution: Gradually increase activity in short sessions throughout the day.\n\nProblem: Stress\nReframing: Exercise is an effective stress reliever.\nSolution: Take brisk walks, reflecting on post-exercise relaxation.\n\nProblem: Feeling Ashamed\nReframing: Starting to exercise can feel daunting.\nSolution: Focus on health over others’ opinions. Remind yourself each session will get easier.\n\nProblem: Feeling Unsafe\nReframing: Concerns about safety can deter walking.\nSolution: Follow safety tips like wearing visible clothing, walking in populated areas, and sharing your route with someone.\n\nProblem: Feeling Unsupported\nReframing: Lack of social support can affect motivation.\nSolution: Seek encouragement from friends or groups, join a walking club, and value personal exercise time.\n\nProblem: Weather\nReframing: Don’t let weather conditions stop you.\nSolution: Walk indoors, dress appropriately for the weather, and stay hydrated",
				}
		tasks_description = "".join(f"<{key}>{tasks[key]}</{key}>" for key in tasks)
		prompt = "The following contains the dialogue history between a user and a health coach agent. Your task is to identify which task the agent has to complete given the user expectations. Respond with only one word: 'Onboarding', 'Program', 'Past experience', 'Barriers', 'Motivation', 'Goal setting' or 'Advice'."
		prompt += "<tasks>"+tasks_description+"</tasks>"
		prompt += "<conversation history>"
		self.system_prompt = prompt
		self.end_of_prompt = "</conversation history> Given this conversation history, respond only with 'Onboarding', 'Program', 'Past experience', 'Barriers', 'Motivation', 'Goal setting' or 'Advice' depending on which task should be completed"
    

	def handle_request(self, history) :
		response = self.model.chat.completions.create(
		messages=[{"role": "system", "content": self.system_prompt+history+self.end_of_prompt}],
		max_tokens=4096,
		temperature=1.0,
		top_p=1.0,
		model=deployment)
		return response.choices[0].message.content