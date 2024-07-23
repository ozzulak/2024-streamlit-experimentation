

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

import os

import streamlit as st


## import our prompts: 

from lc_prompts import *
from lc_scenario_prompts import *
from testing_prompts import * 



os.environ["OPENAI_API_KEY"] = st.secrets['OPENAI_API_KEY']
os.environ["LANGCHAIN_API_KEY"] = st.secrets['LANGCHAIN_API_KEY']
os.environ["LANGCHAIN_PROJECT"] = st.secrets['LANGCHAIN_PROJECT']
os.environ["LANGCHAIN_TRACING_V2"] = 'true'


DEBUG = False

# Auto-trace LLM calls in-context
# client = wrap_openai(openai.Client())
smith_client = Client()


st.set_page_config(page_title="Study bot", page_icon="📖")
st.title("📖 Study bot")

"""

"""


if 'run_id' not in st.session_state: 
    ##TEMP TO TEST CODE -- adding feedback to particular run ! 
    st.session_state['run_id'] = None

if 'agentState' not in st.session_state: 
    st.session_state['agentState'] = "start"
if 'consent' not in st.session_state: 
    st.session_state['consent'] = False
if 'exp_data' not in st.session_state: 
    st.session_state['exp_data'] = True


## set the model to use in case this is the first run 
# llm_model = "gpt-3.5-turbo-1106"
if 'llm_model' not in st.session_state:
    # st.session_state.llm_model = "gpt-3.5-turbo-1106"
    st.session_state.llm_model = "gpt-4o"

# Set up memory for the data collection 
msgs = StreamlitChatMessageHistory(key="langchain_messages")

memory = ConversationBufferMemory(memory_key="history", chat_memory=msgs)

adaptation = False
## set up the memory & process for the adaptation: 
if adaptation: 
    adaptation_msgs = StreamlitChatMessageHistory(key = "adaptation_messages")
    adaptation_memory = ConversationBufferMemory(memory_key="adaptation_history", chat_memory=adaptation_msgs)


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





def getData (testing = False ): 
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
                st.session_state.agentState = "summarise"
                summariseData(testing)
            else:
                st.chat_message("ai").write(response["response"])

 
        
        #st.text(st.write(response))


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


def collectFeedback(answer, column_id,  scenario):

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
        feedback_type_str = f"{answer['type']} {score} {answer['text']} \n {scenario}"

        st.session_state.temp_debug = feedback_type_str

        payload = f"{answer['score']} rating scenario: \n {scenario} \n Based on: \n {answer_set}"

        # Record the feedback with the formulated feedback type string
        # and optional comment
        smith_client.create_feedback(
            run_id= run_id,
            value = payload,
            key = column_id,
            score=score,
            comment=answer['text']
        )
    else:
        st.warning("Invalid feedback score.")    



@traceable # Auto-trace this function
def summariseData(testing = False): 
    # turn the prompt into a prompt template:
    prompt_template = PromptTemplate.from_template(prompt_one_shot)

    # add a json parser to make sure the output is a json object
    json_parser = SimpleJsonOutputParser()

    # connect the prompt with the llm call, and then ensure output is json with our new parser
    chain = prompt_template | chat | json_parser

    ## pick the prompt we want to use:
    prompt_1 = prompt_formal
    # prompt_1 = prompt_goth
    # prompt_2 = prompt_youth
    # prompt_2 = prompt_youth
    prompt_2 = prompt_sibling
    prompt_3 = prompt_goth
    end_prompt = end_prompt_core

    ### NEED TO EXTRACT THE CHOICES:
    if testing: 
        answer_set = extractChoices(msgs, True)
    else:
        answer_set = extractChoices(msgs, False)
    
    if DEBUG: 
        st.divider()
        st.chat_message("ai").write("**DEBUGGING** *-- I think this is a good summary of what you told me ... check if this is correct!*")
        st.chat_message("ai").json(answer_set)

    st.session_state['answer_set'] = answer_set


    with entry_messages:
        if testing:
            st.markdown(":red[DEBUG active -- using testing messages]")

        st.divider()
        st.chat_message("ai").write("Seems I have everything! Let me try to summarise what you said in three scenarios. \n See you if you like any of these! ")


        ## can't be bothered to stream these, so just showing progress bar 
        progress_text = 'Processing your scenarios'
        bar = st.progress(0, text = progress_text)


    st.session_state.response_1 = chain.invoke({
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
    run_1 = get_current_run_tree()

    bar.progress(33, progress_text)

    st.session_state.response_2 = chain.invoke({
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
    run_2 = get_current_run_tree()

    bar.progress(66, progress_text)

    st.session_state.response_3 = chain.invoke({
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
    run_3 = get_current_run_tree()

    bar.progress(99, progress_text)

    # remove the progress bar
    # bar.empty()

    if DEBUG: 
        st.session_state.run_collection = {
            "run1": run_1,
            "run2": run_2,
            "run3": run_3
        }

    ## update the correct run ID -- all three calls share the same one. 
    st.session_state.run_id = run_1.id

    ## set the next target
    st.session_state["agentState"] = "review"

    st.button("I'm ready -- show me!", key = 'progressButton')
    #st.rerun() 

def testing_reviewSetUp():
    ## DEPRECATED -- DOES NOT WORK AT THIS POINT

    ## setting up testing code -- will likely be pulled out into a different procedure 
    text_scenarios = {
        "s1" : "So, here's the deal. I've been really trying to get my head around this coding thing, specifically in langchain. I thought I'd share my struggle online, hoping for some support or advice. But guess what? My PhD students and postdocs, the very same people I've been telling how crucial it is to learn coding, just laughed at me! Can you believe it? It made me feel super ticked off and embarrassed. I mean, who needs that kind of negativity, right? So, I did what I had to do. I let all the postdocs go, re-advertised their positions, and had a serious chat with the PhDs about how uncool their reaction was to my coding struggles.",

        "s2": "So, here's the thing. I've been trying to learn this coding thing called langchain, right? It's been a real struggle, so I decided to share my troubles online. I thought my phd students and postdocs would understand, but instead, they just laughed at me! Can you believe that? After all the times I've told them how important it is to learn how to code. It made me feel really mad and embarrassed, you know? So, I did what I had to do. I told the postdocs they were out and had to re-advertise their positions. And I had a serious talk with the phds, telling them that laughing at my coding struggles was not cool at all.",

        "s3": "So, here's the deal. I've been trying to learn this coding language called langchain, right? And it's been a real struggle. So, I decided to post about it online, hoping for some support or advice. But guess what? My PhD students and postdocs, the same people I've been telling how important it is to learn coding, just laughed at me! Can you believe it? I was so ticked off and embarrassed. I mean, who does that? So, I did what any self-respecting person would do. I fired all the postdocs and re-advertised their positions. And for the PhDs? I had a serious talk with them about how uncool their reaction was to my coding struggles."
    }
    st.session_state.response_1 = {'output_scenario': text_scenarios['s1']}
    st.session_state.response_2 = {'output_scenario': text_scenarios['s2']}
    st.session_state.response_3 = {'output_scenario': text_scenarios['s3']}

def test_call(answer, key, *args, **kwargs):
    
    if st.session_state[key]:
        answer = st.session_state[key]
        st.write(answer)

        st.write("answer:", answer)
        st.write("key:", key)
        st.write("*args:", args)
        st.write("**kwargs:", kwargs)


    else: 
        st.write("feedback not available")

def click_selection_yes(button_num, scenario):
    st.session_state.scenario_selection = button_num
    
    ## if we are testing, some of these do not have to be ready: 
    if 'answer_set' not in st.session_state:
        st.session_state['answer_set'] = "Testing - no answers"

    ## save all important information in one package
    st.session_state.scenario_package = {
            'scenario': scenario,
            'judgment': st.session_state['scenario_decision'],
            'chat history': msgs, 
            'answer set':  st.session_state['answer_set']
    }


def click_selection_no():
    st.session_state['scenario_judged'] = True

def sliderChange(name, *args):
    st.session_state['scenario_judged'] = False
    # print(f"we're looking at slider name {name}. This should have value of {st.session_state[name]}")
    # print(f"name is {name}, other args given: {args}")
    st.session_state['scenario_decision'] = st.session_state[name]


     
def scenario_selection (popover, button_num, scenario):
    with popover:
        # st.markdown(f"You're thinking of selecting scenario {button_num}:")
        # st.markdown(f"*{scenario}*")

        ## make sure that the button can't be pressed unless slider moved
        if "scenario_judged" not in st.session_state:
            st.session_state['scenario_judged'] = True


        st.markdown(f"How well does the scenario {button_num} capture what you had in mind?")
        sliderOptions = ["Not really ", "Needs some edits", "Pretty good but I'd like to tweak it", "Ready as is!"]
        slider_name = f'slider_{button_num}'

        st.select_slider("Judge_scenario", label_visibility= 'hidden', key = slider_name, options = sliderOptions, on_change= sliderChange, args = (slider_name,))
        

        c1, c2 = st.columns(2)
        
        ## only the accept button button should be disabled 
        c1.button("Continue with this scenario 🎉", key = f'yeskey_{button_num}', on_click = click_selection_yes, args = (button_num, scenario), disabled = st.session_state['scenario_judged'])

        ## the second one needs to be accessible all the time!  
        c2.button("actually, let me try another one 🤨", key = f'nokey_{button_num}', on_click= click_selection_no)



def reviewData(testing):

    ## If we're testing this function, the previous functions have set up the three column structure yet and we don't have scenarios. 
    ## --> we will set these up now. 
    if testing:
        testing_reviewSetUp() 

    # ## ensuring we can clear the screen first time we enter reviewData!
    # if 'reviewing' not in st.session_state:
    #     st.session_state['reviewing'] = True
    #     st.rerun()



    ## if this is the first time running, let's make sure that the scenario selection variable is ready. 
    if 'scenario_selection' not in st.session_state:
        st.session_state['scenario_selection'] = '0'

    ## assuming no scenario has been selected 
    if st.session_state['scenario_selection'] == '0':
        # setting up space for the scenarios 
        col1, col2, col3 = st.columns(3)
        
        ## check if we had any feedback before:
        ## set up a dictionary:
        disable = {
            'col1_fb': None,
            'col2_fb': None,
            'col3_fb': None,
        }
        ## grab any answers we already have:
        for col in ['col1_fb','col2_fb','col3_fb']:
            if col in st.session_state and st.session_state[col] is not None:
                
                if DEBUG: 
                    st.write(col)
                    st.write("Feeedback 1:", st.session_state[col]['score'])
                
                # update the corresponding entry in the disable dict
                disable[col] = st.session_state[col]['score']


        with col1: 
            st.header("Scenario 1") 
            st.write(st.session_state.response_1['output_scenario'])
            col1_fb = streamlit_feedback(
                feedback_type="thumbs",
                optional_text_label="[Optional] Please provide an explanation",
                align='center',
                key="col1_fb",
                # this ensures that feedback cannot be submitted twice 
                disable_with_score = disable['col1_fb'],
                on_submit = collectFeedback,
                args = ('col1',
                        st.session_state.response_1['output_scenario']
                        )
            )

        with col2: 
            st.header("Scenario 2") 
            st.write(st.session_state.response_2['output_scenario'])
            col2_fb = streamlit_feedback(
                feedback_type="thumbs",
                optional_text_label="[Optional] Please provide an explanation",
                align='center',
                key="col2_fb",
                disable_with_score = disable['col2_fb'],            
                on_submit = collectFeedback,
                args = ('col2', 
                        st.session_state.response_2['output_scenario']
                        )
            )        
        
        with col3: 
            st.header("Scenario 3") 
            st.write(st.session_state.response_3['output_scenario'])
            col3_fb = streamlit_feedback(
                feedback_type="thumbs",
                optional_text_label="[Optional] Please provide an explanation",
                align='center',
                key="col3_fb",
                disable_with_score = disable['col3_fb'],            
                on_submit = collectFeedback,
                args = ('col3', 
                        st.session_state.response_3['output_scenario']
                        )
            )   


        ## now we should have col1, col2, col3 with text available -- let's set up the infrastructure. 
        st.divider()

        if DEBUG:
            st.write("run ID", st.session_state['run_id'])
            if 'temp_debug' not in st.session_state:
                st.write("no debug found")
            else:
                st.write("debug feedback", st.session_state.temp_debug)
        


    ## if we haven't selected scenario, let's give them a choice. 
        # st.chat_message("ai").write("Please have a look at the scenarios above and pick one you like the most! You can use 👍 and 👎 if you want to leave a comment for us on any scenario.")

        st.chat_message("ai").write("Please have a look at the scenarios above. Use the 👍 and 👎  to leave a rating and short comment on each of the scenarios. Then pick the one that you like the most to continue. ")
     
        b1,b2,b3 = st.columns(3)
        p1 = b1.popover('Pick scenario 1', use_container_width=True)
        p2 = b2.popover('Pick scenario 2', use_container_width=True)
        p3 = b3.popover('Pick scenario 3', use_container_width=True)

        scenario_selection(p1,'1', st.session_state.response_1['output_scenario']) 
        scenario_selection(p2,'2',st.session_state.response_2['output_scenario']) 
        scenario_selection(p3,'3',st.session_state.response_3['output_scenario']) 
    
    
    ## and finally, assuming we have selected a scenario, let's move into the final state!  Note that we ensured that the screen is free for any new content now! 
    else:
        # great, we have a scenario selected, and all the key information is not in st.session_state['scenario_package'], created in the def click_selection_yes(button_num, scenario):

        st.session_state['agentState'] = 'finalise'
        print("ended loop -- should move to finalise!")
        finaliseScenario()

def test_area (*args):
    print(args)
    

def updateFinalScenario (new_scenario):
    st.session_state.scenario_package['scenario'] = new_scenario
    st.session_state.scenario_package['judgment'] = "Ready as is!"

@traceable
def finaliseScenario():

    debug_expander = st.expander("Debug -- history")

    # grab a 'local' copy of the package
    package = st.session_state['scenario_package']

    with debug_expander:
        st.header("Great -- you've selected a scenario ... this is what we know about it! ")
        st.write(st.session_state['scenario_package'])

    
    if package['judgment'] == "Ready as is!":

        
        
        ## Save final feedback and the scenario
        run_id = st.session_state['run_id']

        smith_client.create_feedback(
            run_id=run_id,
            value=package,
            key="final_package"
        )
        

        st.markdown(":tada: Yay! :tada:")
        st.markdown("You've now completed the interaction and hopefully found a scenario that you liked! Please return to the survey window to complete the rest of the study -- your code for Prolific is '**CyberCorgi CodeCrumbs**' ")
        st.markdown(f":green[{package['scenario']}]")
    else:
        original = st.container()
        
        with original:
            st.markdown(f"It seems that you selected a scenario that you liked: \n\n :green[{package['scenario']}]")
            st.markdown(f"... but that you also think it: :red[{package['judgment']}]")

        adapt_convo_container = st.container()
        
        with adapt_convo_container:
            st.chat_message("ai").write("Okay, what's missing or could change to make this better?")
        
            if prompt:
                st.chat_message("human").write(prompt) 

                adaptation_prompt = PromptTemplate(input_variables=["input", "scenario"], template = prompt_adaptation)
                json_parser = SimpleJsonOutputParser()

                chain = adaptation_prompt | chat | json_parser

                with st.spinner('Working on your updated scenario 🧐'):
                    new_response = chain.invoke({
                        'scenario': package['scenario'], 
                        'input': prompt
                        })
                    # st.write(new_response)

                st.markdown(f"Here is the adapted response: \n :orange[{new_response['new_scenario']}]\n\n **what do you think?**")

                # st.markdown(":red[Still working on how to best do the adaptation here]")

                # c1, c2, c3 = st.columns(3)
                c1, c2  = st.columns(2)

                c1.button("All good!", 
                          on_click=updateFinalScenario,
                          args=(new_response['new_scenario'],))
                c2.button("Keep adapting")
                # popover_rewrite = c3.popover("I'll rewrite it myself")
                # with popover_rewrite:
                #     txt = st.text_area("Edit the scenario yourself and press command + Enter when you're happy with it",value=new_response['new_scenario'], on_change=test_area)            


            

def stateAgent(): 
    testing = False

    if testing:
        print("Running stateAgent loop -- session state: ", st.session_state['agentState'])
### make choice of the right 'agent': 
    if st.session_state['agentState'] == 'start':
            getData(False)
            # summariseData(testing)
            # reviewData(testing)
    elif st.session_state['agentState'] == 'summarise':
            summariseData(testing)
    elif st.session_state['agentState'] == 'review':
            reviewData(testing)
    elif st.session_state['agentState'] == 'finalise':
            finaliseScenario()



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

    
    prompt = st.chat_input()


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

    if adaptation:
        ## set up the LangChain for adaption:
        adaptation_prompt = PromptTemplate(input_variables=["history", "input", "scenario"], template = prompt_adaptation)

        adaptation_convo  = ConversationChain(
            prompt = adaptation_prompt,
            llm = chat,
            verbose = True,
            memory = adaptation_memory
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
           



