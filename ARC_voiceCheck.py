

from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI
from langchain.output_parsers.json import SimpleJsonOutputParser
from langsmith import Client
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from streamlit_feedback import streamlit_feedback

from functools import partial
import uuid
import os

import streamlit as st


## import our prompts: 

from lc_prompts import *
from lc_scenario_prompts import *
from testing_prompts import * 



os.environ["OPENAI_API_KEY"] = st.secrets['OPENAI_API_KEY']
os.environ["LANGCHAIN_API_KEY"] = st.secrets['LANGCHAIN_API_KEY']
os.environ["LANGCHAIN_PROJECT"] = "databot-v2-arc"
os.environ["LANGCHAIN_TRACING_V2"] = 'true'


DEBUG = False

# Auto-trace LLM calls in-context
# client = wrap_openai(openai.Client())
smith_client = Client()


st.set_page_config(page_title="Story bot ", page_icon="📖")
st.title("📖 Story bot — Trying Out Different Voices")

"""

"""


if 'run_id' not in st.session_state: 
    ##TEMP TO TEST CODE -- adding feedback to particular run ! 
    st.session_state['run_id'] = None

# we want to be able to tie together all feedback within a session (while collecting the feedback options one at a time)
if 'client' not in st.session_state: 
    st.session_state['client'] = uuid.uuid4()

# set up the counter to track number of scenarios generated
if 'counter' not in st.session_state: 
    st.session_state['counter'] = 0

if 'agentState' not in st.session_state: 
    st.session_state['agentState'] = "start"
if 'consent' not in st.session_state: 
    st.session_state['consent'] = False
if 'exp_data' not in st.session_state: 
    st.session_state['exp_data'] = True

if 'latestScenario' not in st.session_state: 
    st.session_state['latestScenario'] = ""

if 'logs' not in st.session_state:
    st.session_state['logs'] = []

## set the model to use in case this is the first run 
# llm_model = "gpt-3.5-turbo-1106"
if 'llm_model' not in st.session_state:
    # st.session_state.llm_model = "gpt-3.5-turbo-1106"
    st.session_state.llm_model = "gpt-4o"

# Set up memory for the data collection 
msgs = StreamlitChatMessageHistory(key="langchain_messages")

memory = ConversationBufferMemory(memory_key="history", chat_memory=msgs)



# selections = st.sidebar

## removing this option for now. 
# selections.markdown("## Feedback Scale")
# feedback_option = (
#     "thumbs" if st.sidebar.toggle(label="`Faces` ⇄ `Thumbs`", value=False) else "faces"
# )

# with selections:
#     st.markdown("## LLM model selection")
#     st.markdown(":blue[Different models have widely differing costs.   \n \n  It seems that running this whole flow with chatGPT 4 costs about $0.1 per full flow as there are multiple processing steps 👻; while the 3.5-turbo is about 100x cheaper 🤑 and gpt-4o is about 6x cheaper (I think).]")
#     st.markdown('**Our prompts are currently set up for gpt-4 so you might want to run your first trial with that** ... however, multiple runs might be good to with some of the cheaper models.')
    


#     st.session_state.llm_model = st.selectbox(
#         "Which LLM would you like to try?",
#         [ 
#             'gpt-4o', 
#             'gpt-4',
#             'gpt-3.5-turbo-1106'
#             ],
#         key = 'llm_choice',
#     )

#     st.write("**Current llm-model selection:**  \n " + st.session_state.llm_model)

## ensure we are using a better prompt for 4o 
if st.session_state['llm_model'] == "gpt-4o":
    prompt_datacollection = prompt_datacollection_4o




def extractChoices(msgs, testing ):
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



def getData (testing = False ): 
    prompt = st.chat_input()

    if len(msgs.messages) == 0:
        msgs.add_ai_message("Hi there -- I'm collecting stories about challenging experiences on social media to better understand and support our students. I'd appreciate if you could share your experience with me by answering a few questions. \n\n I'll start with a general question and then we'll move to a specific situation you remember. \n\n  Let me know when you're ready! ")

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
            with entry_messages:
                st.chat_message(msg.type).write(msg.content)


    # If user inputs a new prompt, generate and draw a new response
    if prompt:
        with entry_messages:
            st.chat_message("human").write(prompt)
            # Note: new messages are saved to history automatically by Langchain during run
            response = conversation.invoke(input = prompt)
            # print(response)
            if "FINISHED" in response['response']:
                st.divider()
                st.chat_message("ai").write("Great, I think I got all I need -- but let me double check!")
                st.session_state.agentState = "setup"
                setUpStory(testing)
            
            else:
                st.chat_message("ai").write(response["response"])

 
        
        #st.text(st.write(response))


def collectFeedback(answer, persona,  scenario, counter):

    st.session_state.temp_debug = "called collectFeedback"
    ## not needed for now, but just so we have the opportunity to deal with faces as well 
    score_mappings = {
        "thumbs": {"👍": 1, "👎": 0},
        "faces": {"😀": 1, "🙂": 0.75, "😐": 0.5, "🙁": 0.25, "😞": 0},
    }
    scores = score_mappings[answer['type']]
    
    # Get the score from the selected feedback option's score mapping
    score = scores.get(answer['score'])

    run_id = st.session_state['run_id']

    if DEBUG: 
        st.write(run_id)
        st.write(answer)

    if score is not None:
        # Formulate feedback type string incorporating the feedback option
        # and score value

        # payload = f"{answer['score']} rating scenario: \n {scenario} \n by persona: \n {persona}"

        payload = {
            'id': st.session_state['client'],
            'scenario': scenario,
            'persona': persona,
            'rating_face': answer,
            'rating_num': score
        }

        st.session_state[f"fb_{counter}"] = answer

        # Record the feedback with the formulated feedback type string
        # and optional comment
        smith_client.create_feedback(
            run_id= run_id,
            value = payload,
            key = "persona_feedback",
            score=score,
            comment=answer['text']
        )
    else:
        st.warning("Invalid feedback score.")    




def setUpStory(testing = False): 

     ### NEED TO EXTRACT THE CHOICES:
    if testing: 
        st.markdown(":red[DEBUG active -- using testing messages]")
        answer_set = extractChoices(msgs, True)
    else:
        answer_set = extractChoices(msgs, False)
    
    st.session_state['answer_set'] = answer_set
                

    with entry_messages:

        st.divider()
        st.chat_message("ai").write("Seems I have everything! Are you ready to start exploring possible scenarios?")

    st.session_state['agentState'] = 'explore'
    st.button("I'm ready -- show me!", key = 'progressButton')
    
    #st.rerun() 

@traceable # Auto-trace this function
def generateScenario(*args):

    prompt_template = PromptTemplate.from_template(prompt_one_shot)

    # add a json parser to make sure the output is a json object
    json_parser = SimpleJsonOutputParser()

    # connect the prompt with the llm call, and then ensure output is json with our new parser
    chain = prompt_template | chat | json_parser

    # ensure we are looking at the right answers 
    answer_set = st.session_state['answer_set']

    prompt_selected = st.session_state['prompt_field']

    run = get_current_run_tree()

    st.session_state['run_id'] = run.id

    ## add the counter 
    st.session_state['counter'] += 1

    with st.spinner("Processing scenario:"):
        st.session_state.latestScenario = chain.invoke({
            "main_prompt" : prompt_selected,
            "end_prompt" : end_prompt_core,
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


        ## Save the corresponding package into the logs. 
        current_scenario = {
            'persona': st.session_state['prompt_field'],
            'scenario': st.session_state.latestScenario['output_scenario'],
            'counter': st.session_state['counter']
        }

        st.session_state.logs.append(current_scenario)

        # st.session_state['latestScenario'] = st.session_state['prompt_field']
    # print(*args)

def printScenario(scenario):
    st.divider()
    st.markdown(f"**Persona:** *{scenario['persona']}*")
    st.markdown(f"**Scenario:** *{scenario['scenario']}*")

    feedbackKey = "fb_" + str(scenario['counter'])
    if feedbackKey in st.session_state: 
        print(f"Feedback key found: {feedbackKey}")
    
        if st.session_state[feedbackKey] is not None: 
            # fb has there components -- type, score, text
            print(st.session_state[feedbackKey])
            fb = st.session_state[feedbackKey]
            st.markdown(f"**Your feedback:** {fb['score']} — {fb['text']}")

    else:
        st.markdown("***no feedback given***")


def exploreOptions ():
   # we know that the page will be empty here -- set up the streamlit infrastructure first:

    #side = st.sidebar
    
    # tab_generate, tab_review = st.tabs(['generate new scenarios', 'review previous'])
    
    sidebar_toggle = True
    if sidebar_toggle: 
        side = st.sidebar

        with side:
             st.markdown("""   
                    > ## :thinking_face: What do do? Three simple steps: 
                    > 
                    > :one: **Play around with how different personas work for your story**
                    > - *Choosing a specific persona will change the voice of the chatbot and the language they use to describe your social media scenario.* 
                    >
                    > - *You can test the voices out by pressing the  **See my story** button. Don't forget to leave feedback!*
                    >
                    > :two: **Make your own!**
                    > - *Now that you've tried our options, make a few of your own -- who would you like to tell your story*
                    >
                    > **Adaptation tips**: *You can change who the persona is (e.g., age, background, tone they should use) as well as how they should engage with your problem! Try a few things and have fun!*
                    > 
                    > :three: **Return to the Qualtrics survey**
                
                    """)

            # st.markdown("### General instructions")
            # st.markdown("**Try our options:**   *In this task we would like you to play around with different personas/voices for our story bot prototype. As you are playing around with the options, we would like you to provide some feedback on which ones you like / dislike and why.* ")
            # st.markdown("**Make your own:**  *Once you've tried a couple of options, try making a few of your own -- who would you like to tell your story?*")
            # st.divider()
            # st.markdown("**Adaptation tips:** *You can change who the persona is (e.g., age, background, tone they should use) as well as how they should engage with your problem! Try a few things and have fun!*")




    col_select, col_review = st.columns(2)

    with col_select:
       
        voice = st.selectbox(
            "**Who would you like to generate your scenario?** *Choosing a specific persona will change the voice of the chatbot and the language they use to describe your social media scenario.*",
            [
                "younger sibling",
                "friend",
                "psychologist",            
                "influencer",
                "cheeky goth",
                "let me make one"
            ]
        )

        prompts_options = {
            "younger sibling": prompt_youth,
            "friend": prompt_friend,
            "psychologist": prompt_formal,
            "influencer": prompt_socialmediainfluencer,
            "cheeky goth": prompt_goth,
            "let me make one": prompt_own
        }
        
    with col_review:
        if voice:
            prompt_text = st.text_area("**Persona description:**  *Feel free to adapt it as much as you like! Remember, you can change 'who' they are or how they retell your story.* ",
                        key = "prompt_field", 
                        value=prompts_options[voice],
                        height=250
                        )
            


    
    ## let them create & see the scenario
    st.button("See my story with as told by the selected persona!", on_click=generateScenario)


    
    
    if st.session_state['latestScenario'] != "": 
        st.divider()
        st.markdown("**Your latest generated scenario:** :balloon: :balloon::balloon:")
        st.markdown(f"*{st.session_state['latestScenario']['output_scenario']}* ")

        st.markdown("**Please share what you think:**")
        latest_rating = streamlit_feedback(
            feedback_type="faces",
            optional_text_label="[Optional] Please provide an explanation",
            align = "flex-start",
            key=f"feedback_{st.session_state['counter']}",
            on_submit=collectFeedback,
            args=(
                st.session_state['prompt_field'],  # persona description
                st.session_state['latestScenario']['output_scenario'],
                st.session_state['counter']
            )
            ## combine in args 
            # the prompt st.session_state['prompt_field'] together 
            # with the st.session_state['latest_scenario']['output_scenario'] 
        )

    ### separate the expander 
        st.markdown('###')
        st.divider()
        
        st.markdown("### Scenario History")
        review_scenarios = st.expander("Click me to see your history")
        
        with review_scenarios:

            for log in st.session_state.logs:
                printScenario(log)

        

    # st.markdown("## The prompt you used: :writing_hand:")
    # if st.session_state['latestScenario'] != "": 
    #     st.markdown(f" \n \n *{st.session_state['prompt_field']}*")








            

def stateAgent(): 
    testing = False

    if testing:
        print("Running stateAgent loop -- session state: ", st.session_state['agentState'])
### make choice of the right 'agent': 
    if st.session_state['agentState'] == 'start':
            if testing:
                setUpStory(testing)
                # reviewData(testing)
            else:
                getData(testing)
            # setUpStory(testing)
            # reviewData(testing)
    elif st.session_state['agentState'] == 'setup':
            setUpStory(testing)
    
    elif st.session_state['agentState'] == 'explore':
            exploreOptions()
    


def markConsent():
    st.session_state['consent'] = True

# #Draw the messages at the end, so newly generated ones show up immediately
# with view_messages:
#     """
#     Message History initialized with:
#     ```python
#     msgs = StreamlitChatMessageHistory(key="langchain_messages")
#     ```

#     Contents of `st.session_state.langchain_messages`:
#     """
#     view_messages.json(st.session_state.langchain_messages)


### check we have consent -- if so, run normally 
if st.session_state['consent']: 
    # st.snow()
    # view_messages = st.expander("View the message contents in session state")
    # print('st.session_state[exp_data] is ', st.session_state['exp_data'])

    if st.session_state['agentState'] == 'review':
        st.session_state['exp_data'] = False

    entry_messages = st.expander("Collecting your story", expanded = st.session_state['exp_data'])

    if st.session_state['agentState'] == 'review':
        review_messages = st.expander("Review Scenarios")

    


    # Get an OpenAI API Key before continuing
    if "openai_api_key" in st.secrets:
        openai_api_key = st.secrets.openai_api_key
    else:
        openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    if not openai_api_key:
        st.info("Enter an OpenAI API Key to continue")
        st.stop()



    chat = ChatOpenAI(temperature=0.3, model=st.session_state.llm_model, openai_api_key = openai_api_key)


    # Set up the LangChain for data collection, passing in Message History
    prompt_updated = PromptTemplate(input_variables=["history", "input"], template = prompt_datacollection)

    conversation = ConversationChain(
        prompt = prompt_updated,
        llm = chat,
        verbose = True,
        memory = memory
        )

        
    stateAgent()

else: 
    print("don't have consent!")
    consent_message = st.container()
    with consent_message:
        st.markdown(''' 
                    ## Welcome to our teenbot-prototype.

                    \n In this task you’re going to engage with a prototype chatbot that asks you to imagine certain social media experiences. We would like you to imagine that you are a young person who regularly uses social media. Please answer the questions from the perspective of this young person. You can refer to *general* social media experiences or situations that have happened to people you know but please do not share any personal data or experiences. 
                    
                    \n \n **It's important that you do not report situations that contain personal information about yourself.** 
                    
                    \n \n To proceed to the task, please confirm that you have read and understood this information.
        ''')
        st.button("I accept", key = "consent_button", on_click=markConsent)
           



