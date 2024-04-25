import streamlit as st
import requests
from src.chatbot_ui.chat_ui import message_display, reset_chat_history
from datetime import datetime
from langchain.memory import ConversationBufferMemory
import uuid
import os
import time

code_start_time = time.time()
memory = ConversationBufferMemory(
    return_messages=True, output_key="answer", input_key="input"
)

### Initialize state variables
state_vars = ["table_id", "session_id", "previous_query"]
for i in state_vars:
    if i not in st.session_state:
        st.session_state[i] = None


if "run_id" not in st.session_state:
    st.session_state.run_id = 0

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []


st.set_page_config(
    page_title="Badger CPA Time Tracker",
    page_icon=":robot_face:",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items={
        "About": """SQL Bot is a chatbot designed to help you answer questions from an SQL database.""",
    },
)

st.title("Badger CPA Time Tracker")
# st.caption("Easily chat with database.")

messages_container = st.container()

if "generated" not in st.session_state:
    st.session_state["generated"] = (
        "Hey there, I'm Badger Time tracker Bot, ready to chat up on any questions you might have regarding the data in the timesheets."
    )


if "past" not in st.session_state:
    st.session_state["past"] = "Hey!"
if "input" not in st.session_state:
    st.session_state["input"] = ""
if "stored_session" not in st.session_state:
    st.session_state["stored_session"] = []

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        ("Hello! I'm a chatbot designed to help you with the data in your timesheets.")
    ]


### ----------------- Functionalities on the sidebar --------------------------------

with st.sidebar:

    ### ------------------ Add logo ----------------------------------------------------

    import base64

    with open("logo/Badger-CPA.jpg", "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

        st.sidebar.markdown(
            f"""
            <div style="display:table;margin-top:-20%;margin-left:6%;">
                <img src="data:image/png;base64,{data}" width="250" height="100">
            </div><br>
            """,
            unsafe_allow_html=True,
        )
        st.sidebar.markdown("")

    ### ------------------------- New Chat functionality---------------------------------

    new_chat_button = st.button("New Chat")

    if new_chat_button:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.session_state.run_id = 0
        reset_chat_history()

    ### ------------------------- Logout functionality -----------------------------------

    logoutbutton = st.button("Logout")
    if logoutbutton:
        st.session_state
        st.session_state.end_time = str(datetime.now())
        st.switch_page("app.py")

    # st.title(f"Welcome {st.session_state.user}!")

### ---------- User feedback ---------------------------------------------------

# feedback = streamlit_feedback(
#     feedback_type="thumbs", key=f"feedback_{st.session_state.run_id}"
# )
# st.session_state.feedback = feedback
# st.write(st.session_state.feedback)
# st.write(st.session_state.run_id)


# c_dummy, c4, c5 = st.columns([0.8, 0.1, 0.1])

# with c4:
#     st.button(
#         "👍",
#         on_click=update_logs,
#         args=(1, st.session_state.session_id, st.session_state.run_id),
#     )

# with c5:
#     st.button(
#         "👎",
#         on_click=update_logs,
#         args=(0, st.session_state.session_id, st.session_state.run_id),
#     )


### -------------- Defining the chat box and submit, reset buttons -------------


c1, c2, c3 = st.columns([6.2, 1, 1])
with c1:
    query = st.text_input(
        label="Query",
        key="input",
        value="",
        placeholder="Ask your question here...",
        label_visibility="collapsed",
    )
    st.session_state.query = query

with c2:
    submit_button = st.button("Submit")

with c3:
    reset_button = st.button("Reset")


### ------------ Reset button ---------------------

if reset_button:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    st.session_state.run_id = 0
    reset_chat_history()


### ------------------------ Chat functionality ---------------------------------


def mod_history(x):
    y = []
    for i, k in enumerate(x):
        if i % 2 == 0:
            y.append("user: " + k)
        else:
            y.append("system: " + k)
    return y

badger_backend_url = os.getenv("badger_backend_url")

def send_query(payload):
    try:
        # Make a POST request to the API endpoint
        response = requests.post(badger_backend_url, json=payload)
        
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Return the response content
            return response.json().get("response")
        else:
            # Print error message if request was not successful
            print(f"Error: {response.status_code} - {response.reason}")
            return None
    except Exception as e:
        # Handle exceptions
        print(f"An error occurred: {str(e)}")
        return None 


if ((len(query) > 1) and (query != st.session_state.previous_query)) or submit_button:

    messages = st.session_state["messages"]
    
    payload = {
        "query": query,
        "chat_history": st.session_state.chat_history[-6:],
        "username": st.session_state.user,
        "session_id": st.session_state.session_id
    }
    response_start_time = time.time()
    result = send_query(payload)
    response_end_time = time.time()
    response_execution_time = response_start_time - response_end_time
    print(f'response_execution_time of code is {response_execution_time}')    
    st.session_state.chat_history.append(query)
    st.session_state.chat_history.append(result)
    st.session_state.run_id += 1
    st.session_state.previous_query = query
    print(f'chat history is {st.session_state.chat_history}')

### -------------------- This displays the chat window ------------------------

with messages_container:
    message_display(st.session_state["past"], is_user=True)
    message_display(st.session_state["generated"])
    if st.session_state.chat_history != []:
        for i in range(len(st.session_state.chat_history)):
            if i % 2 == 0:
                message_display(st.session_state["chat_history"][i], is_user=True)
            else:
                message_display(st.session_state["chat_history"][i])


# if feedback:
#     update_logs(
#         feedback=st.session_state.feedback,
#         session_id=st.session_state.session_id,
#         run_id=st.session_state.run_id,
#     )

hide_footer = """
                <style>
                footer {visibility: hidden;}
                </style>
            """
st.markdown(hide_footer, unsafe_allow_html=True)
code_end_time = time.time()
total_execution_time = code_start_time - code_end_time
print(f'total_execution_time of code is {total_execution_time}')
