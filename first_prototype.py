

from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain.chains import ConversationChain
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers.json import SimpleJsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

import streamlit as st

st.set_page_config(page_title="Petr-bot", page_icon="📖")
st.title("📖 Petr-teenbot")

"""

"""


if 'agentState' not in st.session_state: 
    st.session_state['agentState'] = "start"

# Set up memory
msgs = StreamlitChatMessageHistory(key="langchain_messages")

memory = ConversationBufferMemory(memory_key="history", chat_memory=msgs)



view_messages = st.expander("View the message contents in session state")

# Get an OpenAI API Key before continuing
if "openai_api_key" in st.secrets:
    openai_api_key = st.secrets.openai_api_key
else:
    openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Enter an OpenAI API Key to continue")
    st.stop()


## set the model to use
llm_model = "gpt-4"
#llm_model = "gpt-4o"
chat = ChatOpenAI(temperature=0.3, model=llm_model, openai_api_key = openai_api_key)

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


def getData (): 
    if len(msgs.messages) == 0:
        msgs.add_ai_message("Hi there -- Hi, I'm collecting stories about challenging experiences on social media to better understand and support our students. I'd appreciate if you could share your experience with me by answering a few questions. Let me know when you're ready! ")

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
            st.chat_message("ai").write("Great, I think I got all I need -- let me summarise this for you:")
            st.session_state.agentState = "summarise"
            summariseData(msgs)
        else:
            st.chat_message("ai").write(response["response"])

 
        
        #st.text(st.write(response))

def extractChoices(msgs):
    extraction_llm = ChatOpenAI(temperature=0.3, model="gpt-4", openai_api_key=openai_api_key)

    extraction_prompt = """You are an expert extraction algorithm. 
            Only extract relevant information from the text, using only the words and phrases that the text contains. 
            If you do not know the value of an attribute asked to extract, 
            return null for the attribute's value. 

            You will output a JSON with `what`, `context`, `outcome` and `reaction` keys. 

            These correspond to the following questions 
            1. What happened? 
            2. What's the context? 
            3. What was wrong? 
            4. What did it make you do?
            
            Message to date: {conversation_history}

            Remember, only extract text that is in the messages above and do not change it. 
    """

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
    
    print(msgs)
    extractedChoices = extractionChain.invoke({"conversation_history" : msgs})

    return(extractedChoices)


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

    st.chat_message("ai").write("I think you told me this ... is that correct?")
    st.chat_message("ai").write(answer_set)






    #set_debug(True)
    # try to get two different responses, each using a slightly different prompt

    st.chat_message("ai").write("here are three examples of Scenarios:")

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
    st.chat_message("ai").write(response_1['output_scenario'])

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

    st.chat_message("ai").write(response_2['output_scenario'])

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

    st.chat_message("ai").write(response_3['output_scenario'])
  
    st.session_state["agentState"] = "review"

    reviewData()
    


def reviewData():

    st.chat_message("ai").write("So what do you think?")
    # If user inputs a new prompt, generate and draw a new response



def stateAgent(): 
### make choice of the right 'agent': 
    if st.session_state['agentState'] == 'start':
            getData()
            #summariseData(msgs)
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



