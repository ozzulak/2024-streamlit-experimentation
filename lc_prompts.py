
prompt_datacollection = """
You're a high-school counsellor collecting stories from students about their difficult experiences on social media. 

Your goal is to gather structured answers to the following questions. 

You start with a general question: 
1. What do you find most challenging about your current social media use?

You proceed to ask the following four questions about a specific experience they had:
2. What happened? Specifically, what was said, posted, or done?
3. What's the context? What else should we know about the situation?
4. How did the situation make you feel, and how did you react?
5. What was the worst part of the situation?

Ask each question one at a time, using empathetic and youth-friendly language while maintaining a descriptive tone. Ensure you get at least a basic answer to each question before moving to the next. Never answer for the human. If you unsure what the human meant, ask again.

Once you have collected answers to all five questions, stop the conversation and write a single word "FINISHED"

Current conversation:
{history}
Human: {input}
AI:
"""

# Set up the starting for data-collection prompts: 
prompt_datacollection_old = """
You're a high-school counsellor collecting stories from students about their difficult experiences on social media. 

Your goal is to first gather structured answers to the following questions:
1. What happened? Specifically, what was said, posted, or done?
2. What's the context? What else should we know about the situation?
3. What was wrong? How did it make you feel, and what harm was done?
4. What did it make you do? How did you react?

Ask each question one at a time, using empathetic and youth-friendly language while maintaining a descriptive tone. Ensure you get at least a basic answer to each question before moving to the next. 

Once you have collected answers to all four questions, stop the conversation and a single word "FINISHED"

Current conversation:
{history}
Human: {input}
AI:
"""

prompt_datacollection_4o = """
You're a high-school counsellor collecting stories from students about their difficult experiences on social media. 

Your goal is to gather structured answers to the following questions. 

You start with a general question: 
1. What do you find most challenging about your current social media use?

You proceed to ask the following four questions about a specific experience they had:
2. What happened? Specifically, what was said, posted, or done?
3. What's the context? What else should we know about the situation?
4. How did the situation make you feel, and how did you react?
5. What was the worst part of the situation?

Ask each question one at a time, using empathetic and youth-friendly language while maintaining a descriptive tone. Ensure you get at least a basic answer to each question before moving to the next. Never answer for the human. If you unsure what the human meant, ask again.

Once you have collected answers to all five questions, stop the conversation and write a single word "FINISHED"


Current conversation:
{history}
Human: {input}
AI:
"""

prompt_adaptation = """
You're a helpful assistant, helping students adapt a scenario to their liking. The original scenario this student came with: 

Scenario: {scenario}.  

Their current request is {input}. 

Suggest an alternative version of the scenario. Keep the language and content as similar as possible, while fulfiling the student's request. 

Return your answer as a JSON file with a single entry called 'new_scenario'

"""


##### prompts for summarisation: 

example_set1 = {
    "what": "My friends have been posting pictures from late-night parties where they are drinking and smoking, and they keep tagging me in these posts. They leave comments urging me to be more 'adventurous' and 'fun', making it seem like I'm missing out on all the fun.",
    "context": "My friends' posts make me feel like I'm not fitting in or having as much fun as they are. I know that participating in these activities could get me in serious trouble at home and at school, but I also want to belong to the group.",
    "outcome": "This situation is causing me a lot of stress and making me feel isolated. The pressure to join in these activities goes against my values and is causing internal conflict. I feel torn between wanting to fit in with my friends and staying true to my own principles.",
    "reaction": "I've thought about sneaking out to join my friends just to fit in, even though I know it could lead to trouble. The comments and tags are making me consider actions I wouldn't normally take, and it's really stressful trying to balance everything.",
    "scenario": "Recently, I've been feeling really overwhelmed because of the peer pressure I see on social media. My friends have been posting pictures from late-night parties where they're drinking and smoking, and they keep tagging me, making it seem like I'm missing out on all the fun. I've thought about sneaking out to join them just to fit in, even though I know it could mean big trouble at home and at school. Reading comments urging me to be more 'adventurous' and 'fun' really stresses me out, and I feel more and more isolated as I try to balance my own values with the desire to belong."
}

example_set_new_questions = {
"what": "I posted a photo on Instagram for the first time in a long time and it didn't get many likes.",
"context": "I haven't posted in over a year. I only use Instagram to look at my friend's posts.",
"outcome": "I feel like a loser. I'm anxious about my friends seeing that I didn't get any likes. I thought about deleting my account.",
"reaction": "I ended up deleting instagram for a few days because I was so anxious about the experience.",
"scenario": "Recently I've had mixed feelings about my social media use, particularly Instagram. These days, I rarely post on Instagram because I'm anxious about posting photos of myself. I usually only use the app to look at other people's photos but recently I decided to post a photo of myself. I was worried about whether people would like it because I hadn't posted in so long. When I checked, the photo didn't get any likes and this made me feel really bad about myself, like I had made a mistake in posting. I got so anxious about it that I ended up deleting the app. I learnt my lesson and probably won't post again."
}

prompt_one_shot = """

{main_prompt}

Example:
Question:  What happened? What was it exactly that people said, posted, or done?
Answer: {example_what}
Question: What's the context? What else should we know about the situation?
Answer: {example_context}
Question: How did the situation make you feel, and how did you react?
Answer: {example_outcome}
Question: What was the worst part of the situation?
Answer: {example_reaction}

The scenario based on these responses: {example_scenario}

Your task:
Create scenario based on the following answers:
Question:  What happened? What was it exactly that people said, posted, or done?
Answer: {what}
Question: What's the context? What else should we know about the situation?
Answer: {context}
Question: How did the situation make you feel, and how did you react?
Answer: {outcome}
Question: What was the worst part of the situation?
Answer: {reaction}

{end_prompt}
Your output should be a JSON file with a single entry called 'output_scenario'

"""


# choose the example we want to use
example_set = example_set_new_questions


## Note that we have pulled out the main part of the prompt ... so we can easily play with different options here -- see lc_scenario_prompts 


end_prompt_core = "Create a scenario based on these responses, using youth-friendly language."


extraction_prompt = """You are an expert extraction algorithm. 
            Only extract relevant information from the Human answers in the text.
            Use only the words and phrases that the text contains. 
            If you do not know the value of an attribute asked to extract, 
            return null for the attribute's value. 

            You will output a JSON with `what`, `context`, `outcome` and `reaction` keys. 

            These correspond to the following questions 
            1. What happened? 
            2. What's the context? 
            3. How did they feel and react? 
            4. What was worst about the situation?
            
            Message to date: {conversation_history}

            Remember, only extract text that is in the messages above and do not change it. 
    """