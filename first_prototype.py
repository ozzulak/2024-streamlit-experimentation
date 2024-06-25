

from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain.chains import ConversationChain
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers.json import SimpleJsonOutputParser
import openai
from langsmith.wrappers import wrap_openai
from langsmith import traceable
import os
import streamlit as st

os.environ["OPENAI_API_KEY"] = st.secrets['OPENAI_API_KEY']
os.environ["LANGCHAIN_API_KEY"] = st.secrets['LANGCHAIN_API_KEY']
os.environ["LANGCHAIN_PROJECT"] = st.secrets['LANGCHAIN_PROJECT']
os.environ["LANGCHAIN_TRACING_V2"] = 'true'

# Auto-trace LLM calls in-context
client = wrap_openai(openai.Client())


st.set_page_config(page_title="Petr-bot", page_icon="📖")
st.title("📖 Petr-teenbot")

"""

"""


if 'agentState' not in st.session_state: 
    st.session_state['agentState'] = "start"

## set the model to use in case this is the first run 
# llm_model = "gpt-3.5-turbo-1106"
if 'llm_model' not in st.session_state:
    # st.session_state.llm_model = "gpt-3.5-turbo-1106"
    st.session_state.llm_model = "gpt-4o"

# Set up memory
msgs = StreamlitChatMessageHistory(key="langchain_messages")

memory = ConversationBufferMemory(memory_key="history", chat_memory=msgs)

selections = st.sidebar


with selections:
    st.write("""**LLM model selection:**
                Different models have widely differing costs.   \n \n  It seems that running this whole flow with chatGPT 4 costs about $0.1 per full flow as there are multiple processing steps 👻; while the 3.5-turbo is about 100x cheaper 🤑 and gpt-4o is about 6x cheaper (I think).  
                """
                )
    st.write('**Our prompts are currently set up for gpt-4 so you might want to run your first trial with that** ... however, multiple runs might be good to with some of the cheaper models.')
    

    st.session_state.llm_model = st.selectbox(
        "Which LLM would you like to try?",
        [ 
            'gpt-4o', 
            'gpt-4',
            'gpt-3.5-turbo-1106'
            ],
        key = 'llm_choice',
    )

    st.write("**Current llm-model selection:**  \n " + st.session_state.llm_model)



view_messages = st.expander("View the message contents in session state")

# Get an OpenAI API Key before continuing
if "openai_api_key" in st.secrets:
    openai_api_key = st.secrets.openai_api_key
else:
    openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Enter an OpenAI API Key to continue")
    st.stop()



chat = ChatOpenAI(temperature=0.3, model=st.session_state.llm_model, openai_api_key = openai_api_key)

from lc_prompts import *

# Set up the LangChain, passing in Message History
prompt_updated = PromptTemplate(input_variables=["history", "input"], template = prompt_datacollection)

conversation = ConversationChain(
    prompt = prompt_updated,
    llm = chat,
    verbose = True,
    memory = memory
    )


prompt = st.chat_input()

@traceable # Auto-trace this function
def getData (): 
    if len(msgs.messages) == 0:
        msgs.add_ai_message("Hi there -- I'm collecting stories about challenging experiences on social media to better understand and support our students. I'd appreciate if you could share your experience with me by answering a few questions. Let me know when you're ready! ")

    # ## write the whole history:
    # for msg in msgs.messages:
    #     st.chat_message(msg.type).write(msg.content)

   # write just the last conversational turn: 

    if len(msgs.messages) >= 2:
        last_two_messages = msgs.messages[-1:]
    else:
        last_two_messages = msgs.messages

    for msg in last_two_messages:
        if msg.type == "ai":
            st.chat_message(msg.type).write(msg.content)


    # If user inputs a new prompt, generate and draw a new response
    if prompt:
        st.chat_message("human").write(prompt)
        # Note: new messages are saved to history automatically by Langchain during run
        response = conversation.invoke(input = prompt)
        print(response)
        if "FINISHED" in response['response']:
            st.divider()
            st.chat_message("ai").write("Great, I think I got all I need -- let me summarise this for you:")
            st.session_state.agentState = "summarise"
            summariseData(msgs)
        else:
            st.chat_message("ai").write(response["response"])

 
        
        #st.text(st.write(response))

@traceable # Auto-trace this function
def extractChoices(msgs):
    extraction_llm = ChatOpenAI(temperature=0.1, model=st.session_state.llm_model, openai_api_key=openai_api_key)

    ## now should be added into the lc_prompts.py
    # extraction_prompt = """You are an expert extraction algorithm. 
    #         Only extract relevant information from the text, using only the words and phrases that the text contains. 
    #         If you do not know the value of an attribute asked to extract, 
    #         return null for the attribute's value. 

    #         You will output a JSON with `what`, `context`, `outcome` and `reaction` keys. 

    #         These correspond to the following questions 
    #         1. What happened? 
    #         2. What's the context? 
    #         3. What was wrong? 
    #         4. What did it make you do?
            
    #         Message to date: {conversation_history}

    #         Remember, only extract text that is in the messages above and do not change it. 
    # """

    extraction_template = PromptTemplate(input_variables=["conversation_history"], template = extraction_prompt)
    json_parser = SimpleJsonOutputParser()
    extractionChain = extraction_template |extraction_llm | json_parser

    test_messages = """
        AI: Hi there -- welcome to the data collection bot! Let me know when you're ready! 
        Human: Hi I'm read
        AI: Great! Let's start. Can you tell me about a time when something happened on social media that was difficult for you? Specifically, what was said, posted, or done?
        Human: Posted something online about struggling to learn how to code in langchain and my phd students and postdocs just laughted at me!  
        AI: I'm really sorry to hear that you had to go through that. It's not easy when people we look up to react in a way that's less than supportive. Can you give me a bit more context about the situation? Was there any prior conversation or incident that led to this?
        Human: not really, but I have been talking to them excessively about how important it is to learn how to code
        AI: I see, so it sounds like this was something you've been passionate about and have been discussing a lot. Now, can you tell me more about why this was wrong? How did their laughter make you feel and what harm do you think was done?
        Human: wasn't great -- kind of angry and embarrased if you must know!
        AI: I can understand how that would make you feel both angry and embarrassed. It's not easy to put yourself out there, especially when it comes to learning new things. Finally, how did you react to this situation? What did it make you do?
        Human: I was just really miffed -- I obviously I let all the postdocs go and re-advertised their positions, and explained to the phds that this is not appropriate reaction to my coding struggles. 
        AI: Great, I think I got all I need, let me summarise this for you. 
    """
    

    extractedChoices = extractionChain.invoke({"conversation_history" : msgs})
    # extractedChoices = extractionChain.invoke({"conversation_history" : test_messages})

    return(extractedChoices)

@traceable # Auto-trace this function
def summariseData(content): 
    # turn the prompt into a prompt template:
    prompt_template = PromptTemplate.from_template(prompt_one_shot)

    # add a json parser to make sure the output is a json object
    json_parser = SimpleJsonOutputParser()

    # connect the prompt with the llm call, and then ensure output is json with our new parser
    chain = prompt_template | chat | json_parser

    ## pick the prompt we want to use:
    prompt_1 = prompt_formal
    prompt_2 = prompt_youth
    prompt_3 = prompt_friend
    end_prompt = end_prompt_core

    ### NEED TO EXTRACT THE CHOICES:
    answer_set = extractChoices(msgs)
    
    st.divider()
    st.chat_message("ai").write("**DEBUGGING** *-- I think this is a good summary of what you told me ... check if this is correct!*")
    st.chat_message("ai").json(answer_set)






    #set_debug(True)
    # try to get two different responses, each using a slightly different prompt
    st.divider()
    st.chat_message("ai").write("I'm going to try and summarise what you said in three scenarios. \n See you if you like any of these! ")

    response_1 = chain.invoke({
        "main_prompt" : prompt_1,
        "end_prompt" : end_prompt,
        "example_what" : example_set['what'],
        "example_context" : example_set['context'],
        "example_outcome" : example_set['outcome'],
        "example_reaction" : example_set['reaction'],
        "example_scenario" : example_set['scenario'],
        "what" : answer_set['what'],
        "context" : answer_set['context'],
        "outcome" : answer_set['outcome'],
        "reaction" : answer_set['reaction']
    })
    st.chat_message("ai").write("**Scenario 1:**  " + response_1['output_scenario'])

    response_2 = chain.invoke({
        "main_prompt" : prompt_2,
        "end_prompt" : end_prompt,
        "example_what" : example_set['what'],
        "example_context" : example_set['context'],
        "example_outcome" : example_set['outcome'],
        "example_reaction" : example_set['reaction'],
        "example_scenario" : example_set['scenario'],
        "what" : answer_set['what'],
        "context" : answer_set['context'],
        "outcome" : answer_set['outcome'],
        "reaction" : answer_set['reaction']
    })

    
    st.chat_message("ai").write("**Scenario 2:**  " +response_2['output_scenario'])

    response_3 = chain.invoke({
        "main_prompt" : prompt_3,
        "end_prompt" : end_prompt,
        "example_what" : example_set['what'],
        "example_context" : example_set['context'],
        "example_outcome" : example_set['outcome'],
        "example_reaction" : example_set['reaction'],
        "example_scenario" : example_set['scenario'],
        "what" : answer_set['what'],
        "context" : answer_set['context'],
        "outcome" : answer_set['outcome'],
        "reaction" : answer_set['reaction']
    })

    st.chat_message("ai").write("**Scenario 3:**  " + response_3['output_scenario'])
  
    st.session_state["agentState"] = "review"

    reviewData()
    


def reviewData():
    st.divider()

    text_scenarios = [
        "Scenario 1: So, here's the deal. I've been really trying to get my head around this coding thing, specifically in langchain. I thought I'd share my struggle online, hoping for some support or advice. But guess what? My PhD students and postdocs, the very same people I've been telling how crucial it is to learn coding, just laughed at me! Can you believe it? It made me feel super ticked off and embarrassed. I mean, who needs that kind of negativity, right? So, I did what I had to do. I let all the postdocs go, re-advertised their positions, and had a serious chat with the PhDs about how uncool their reaction was to my coding struggles.",

        "Scenario 2: So, here's the thing. I've been trying to learn this coding thing called langchain, right? It's been a real struggle, so I decided to share my troubles online. I thought my phd students and postdocs would understand, but instead, they just laughed at me! Can you believe that? After all the times I've told them how important it is to learn how to code. It made me feel really mad and embarrassed, you know? So, I did what I had to do. I told the postdocs they were out and had to re-advertise their positions. And I had a serious talk with the phds, telling them that laughing at my coding struggles was not cool at all.",

        "Scenario 3: So, here's the deal. I've been trying to learn this coding language called langchain, right? And it's been a real struggle. So, I decided to post about it online, hoping for some support or advice. But guess what? My PhD students and postdocs, the same people I've been telling how important it is to learn coding, just laughed at me! Can you believe it? I was so ticked off and embarrassed. I mean, who does that? So, I did what any self-respecting person would do. I fired all the postdocs and re-advertised their positions. And for the PhDs? I had a serious talk with them about how uncool their reaction was to my coding struggles."
    ]

    st.chat_message("ai").write("** All done! **  \n *We will be implementing the review & adapt functions next. Please reload the page to restart *")
    # If user inputs a new prompt, generate and draw a new response



def stateAgent(): 
### make choice of the right 'agent': 
    if st.session_state['agentState'] == 'start':
            getData()
            # summariseData(msgs)
    elif st.session_state['agentState'] == 'summarise':
            summariseData(msgs)
    elif st.session_state['agentState'] == 'review':
            reviewData()



#Draw the messages at the end, so newly generated ones show up immediately
with view_messages:
    """
    Message History initialized with:
    ```python
    msgs = StreamlitChatMessageHistory(key="langchain_messages")
    ```

    Contents of `st.session_state.langchain_messages`:
    """
    view_messages.json(st.session_state.langchain_messages)



stateAgent()



