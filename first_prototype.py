

from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain.chains import ConversationChain
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers.json import SimpleJsonOutputParser
from langchain.callbacks.streamlit import StreamlitCallbackHandler
import openai
from langsmith.wrappers import wrap_openai
from langsmith import traceable
from langsmith import Client
from streamlit_feedback import streamlit_feedback
import uuid

import os

import streamlit as st


## import our prompts: 

from lc_prompts import *
from testing_prompts import * 


os.environ["OPENAI_API_KEY"] = st.secrets['OPENAI_API_KEY']
os.environ["LANGCHAIN_API_KEY"] = st.secrets['LANGCHAIN_API_KEY']
os.environ["LANGCHAIN_PROJECT"] = st.secrets['LANGCHAIN_PROJECT']
os.environ["LANGCHAIN_TRACING_V2"] = 'true'

# Auto-trace LLM calls in-context
client = wrap_openai(openai.Client())
smith_client = Client()


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

## removing this option for now. 
# selections.markdown("## Feedback Scale")
# feedback_option = (
#     "thumbs" if st.sidebar.toggle(label="`Faces` ⇄ `Thumbs`", value=False) else "faces"
# )

with selections:
    st.markdown("## LLM model selection")
    st.markdown(":blue[Different models have widely differing costs.   \n \n  It seems that running this whole flow with chatGPT 4 costs about $0.1 per full flow as there are multiple processing steps 👻; while the 3.5-turbo is about 100x cheaper 🤑 and gpt-4o is about 6x cheaper (I think).]")
    st.markdown('**Our prompts are currently set up for gpt-4 so you might want to run your first trial with that** ... however, multiple runs might be good to with some of the cheaper models.')
    

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

## ensure we are using a better prompt for 4o 
if st.session_state['llm_model'] == "gpt-4o":
    prompt_datacollection = prompt_datacollection_4o


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


def extractChoices(msgs, testing):
    extraction_llm = ChatOpenAI(temperature=0.1, model=st.session_state.llm_model, openai_api_key=openai_api_key)

    ## taking the prompt from lc_prompts.py file
    extraction_template = PromptTemplate(input_variables=["conversation_history"], template = extraction_prompt)

    ## set up the rest of the chain including the json parser we will need. 
    json_parser = SimpleJsonOutputParser()
    extractionChain = extraction_template | extraction_llm | json_parser

    
    # allow for testing with pre-coded messages -- see testing_prompts.py
    if testing:
        extractedChoices = extractionChain.invoke({"conversation_history" : test_messages})
    else: 
        extractedChoices = extractionChain.invoke({"conversation_history" : msgs})
    

    return(extractedChoices)

@traceable # Auto-trace this function
def summariseData(testing): 
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
    if testing: 
        answer_set = extractChoices(msgs, True)
    else:
        answer_set = extractChoices(msgs, False)
    
    
    st.divider()
    st.chat_message("ai").write("**DEBUGGING** *-- I think this is a good summary of what you told me ... check if this is correct!*")
    st.chat_message("ai").json(answer_set)






    #set_debug(True)
    # try to get two different responses, each using a slightly different prompt
    st.divider()
    st.chat_message("ai").write("I'm going to try and summarise what you said in three scenarios. \n See you if you like any of these! ")

    col1, col2, col3 = st.columns(3)

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
    with col1: 
        st.header("Scenario 1") 
        st.write(response_1['output_scenario'])

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

    with col2: 
        st.header("Scenario 2") 
        st.write(response_2['output_scenario'])

    
    # st.chat_message("ai").write("**Scenario 2:**  " +response_2['output_scenario'])

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

    # st.chat_message("ai").write("**Scenario 3:**  " + response_3['output_scenario'])
    with col3: 
        st.header("Scenario 3") 
        st.write(response_3['output_scenario'])
  
    st.session_state["agentState"] = "review"

    reviewData()


def collectFeedback(run_id, column, fb_score, scenario, fb_text = "", feedback_option = "thumbs"):

    ## not needed for now, but just so we have the opportunity to deal with faces as well 
    score_mappings = {
        "thumbs": {"👍": 1, "👎": 0},
        "faces": {"😀": 1, "🙂": 0.75, "😐": 0.5, "🙁": 0.25, "😞": 0},
    }
    scores = score_mappings[feedback_option]
    
    # Get the score from the selected feedback option's score mapping
    score = scores.get(fb_score)

    if score is not None:
        # Formulate feedback type string incorporating the feedback option
        # and score value
        feedback_type_str = f"{feedback_option} {score}"

        run_id = run_id + column
        # Record the feedback with the formulated feedback type string
        # and optional comment
        feedback_record = smith_client.create_feedback(
            run_id = run_id,
            value = feedback_type_str,
            key = "testingKey",
            score=score,
            comment=fb_text,
        )
    else:
        st.warning("Invalid feedback score.")    


def testing_reviewSetUp():
    ## setting up testing code -- will likely be pulled out into a different procedure 
    text_scenarios = {
        "s1" : "So, here's the deal. I've been really trying to get my head around this coding thing, specifically in langchain. I thought I'd share my struggle online, hoping for some support or advice. But guess what? My PhD students and postdocs, the very same people I've been telling how crucial it is to learn coding, just laughed at me! Can you believe it? It made me feel super ticked off and embarrassed. I mean, who needs that kind of negativity, right? So, I did what I had to do. I let all the postdocs go, re-advertised their positions, and had a serious chat with the PhDs about how uncool their reaction was to my coding struggles.",

        "s2": "So, here's the thing. I've been trying to learn this coding thing called langchain, right? It's been a real struggle, so I decided to share my troubles online. I thought my phd students and postdocs would understand, but instead, they just laughed at me! Can you believe that? After all the times I've told them how important it is to learn how to code. It made me feel really mad and embarrassed, you know? So, I did what I had to do. I told the postdocs they were out and had to re-advertise their positions. And I had a serious talk with the phds, telling them that laughing at my coding struggles was not cool at all.",

        "s3": "So, here's the deal. I've been trying to learn this coding language called langchain, right? And it's been a real struggle. So, I decided to post about it online, hoping for some support or advice. But guess what? My PhD students and postdocs, the same people I've been telling how important it is to learn coding, just laughed at me! Can you believe it? I was so ticked off and embarrassed. I mean, who does that? So, I did what any self-respecting person would do. I fired all the postdocs and re-advertised their positions. And for the PhDs? I had a serious talk with them about how uncool their reaction was to my coding struggles."
    }




    col1, col2, col3 = st.columns(3)
    
    with col1: 
        st.header("Scenario 1") 
        st.write(text_scenarios['s1'])
        # col1_fb = streamlit_feedback(
        #     feedback_type="thumbs",
        #     optional_text_label="[Optional] Please provide an explanation",
        #     align='center',
        #     key="col1_fb",
        #     on_submit = st.write(),
        #     args = 
        # )

    with col2: 
        st.header("Scenario 2") 
        st.write(text_scenarios['s2'])
    
    with col3: 
        st.header("Scenario 3") 
        st.write(text_scenarios['s3'])



def reviewData(testing):

    ## If we're testing, the previous functions have set up the three column structure yet and we don't have scenarios. 
    ## --> we will set these up now. 
    if testing:
        testing_reviewSetUp()



    ## now we should have col1, col2, col3 with text available -- let's set up the infrastructure. 
    st.divider()


        

    ## keeping two options of score mapping as an example -- will only work with thumbs for now. 
    score_mappings = {
        "thumbs": {"👍": 1, "👎": 0},
        "faces": {"😀": 1, "🙂": 0.75, "😐": 0.5, "🙁": 0.25, "😞": 0},
    }

    feedback_option = "thumbs"

    scores = score_mappings[feedback_option]
  
    feedback = streamlit_feedback(
        feedback_type=feedback_option,
        optional_text_label="[Optional] Please provide an explanation",
        key="feedback",
    )

   
    if feedback:
        # Get the score from the selected feedback option's score mapping
        score = scores.get(feedback["score"])

        if score is not None:
            # Formulate feedback type string incorporating the feedback option
            # and score value
            feedback_type_str = f"{feedback_option} {feedback['score']}"

            run_id = str(uuid.uuid4())
            # Record the feedback with the formulated feedback type string
            # and optional comment
            feedback_record = smith_client.create_feedback(
                run_id = run_id,
                value = feedback_type_str,
                key = "testingKey",
                score=score,
                comment=feedback.get("text"),
            )
            st.session_state.feedback_result = {
                "feedback_comment": str(feedback_record.id),
                "score": score
            }
        else:
            st.warning("Invalid feedback score.")

     


    st.chat_message("ai").write("** All done! **  \n *We will be implementing the review & adapt functions next. Please reload the page to restart *")
    # If user inputs a new prompt, generate and draw a new response





def stateAgent(): 
### make choice of the right 'agent': 
    if st.session_state['agentState'] == 'start':
            # getData()
            # summariseData(msgs)
            reviewData(True)
    elif st.session_state['agentState'] == 'summarise':
            summariseData(msgs)
    elif st.session_state['agentState'] == 'review':
            reviewData(False)



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



