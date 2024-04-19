import streamlit as st
from src.chatbot_ui.chat_ui import message_display, reset_chat_history
from src.utils.chatutils import get_response
from src.utils.snowflakeutils import get_database, write_logs, get_user_id
from src.utils.llmutils import convert_to_langchainmsg
from datetime import datetime
from langchain.memory import ConversationBufferMemory
import uuid


db = get_database()

memory = ConversationBufferMemory(
    return_messages=True, output_key="answer", input_key="input"
)

st.session_state.db = db

### Initialize state variables
state_vars = ["table_id", "session_id", "previous_query"]
for i in state_vars:
    if i not in st.session_state:
        st.session_state[i] = None

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []


st.set_page_config(
    page_title="Ngenux SQL Bot",
    page_icon=":robot_face:",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items={
        "Report a bug": "https://github.com/ibizabroker/gpt-pdf-bot",
        "About": """SQL Bot is a chatbot designed to help you answer questions from an SQL database. It is built using OpenAI's GPT, chromadb and Streamlit. 
            To learn more about the project go to the GitHub repo. https://github.com/ibizabroker/gpt-pdf-bot 
            """,
    },
)

st.title("Ngenux SQL Bot")
st.caption("Easily chat with database.")

messages_container = st.container()

if "generated" not in st.session_state:
    st.session_state["generated"] = (
        "Hey there, I'm SQL Bot, ready to chat up on any questions you might have regarding the data in the database."
    )


if "past" not in st.session_state:
    st.session_state["past"] = "Hey!"
if "input" not in st.session_state:
    st.session_state["input"] = ""
if "stored_session" not in st.session_state:
    st.session_state["stored_session"] = []

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        ("Hello! I'm a chatbot designed to help you with pdf documents.")
    ]


### ----------------- Functionalities on the sidebar --------------------------------

with st.sidebar:

    ### ------------------------- New Chat functionality---------------------------------

    new_chat_button = st.button("New Chat")

    if new_chat_button:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        reset_chat_history()

    ### ------------------------- Logout functionality -----------------------------------

    logoutbutton = st.button("Logout")
    if logoutbutton:
        st.session_state
        st.session_state.end_time = str(datetime.now())
        st.switch_page("app.py")

    st.title(f"Welcome {st.session_state.user}!")


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


if ((len(query) > 1) and (query != st.session_state.previous_query)) or submit_button:

    messages = st.session_state["messages"]
    st.session_state.chat_history.append(query)
    result = get_response(
        user_query=query,
        db=st.session_state.db,
        chat_history=convert_to_langchainmsg(st.session_state.chat_history),
    )
    st.session_state.chat_history.append(result)
    write_logs(
        user=get_user_id(st.session_state.user),
        user_query=query,
        response=result,
        time=datetime.now(),
        session_id=st.session_state.session_id,
    )
    st.session_state.previous_query = query


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


hide_footer = """
                <style>
                footer {visibility: hidden;}
                </style>
            """
st.markdown(hide_footer, unsafe_allow_html=True)
