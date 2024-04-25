import streamlit as st
from src.chatbot_ui.chat_ui import message_display, reset_chat_history
from src.utils.chatutils import get_response
from src.utils.snowflakeutils import get_database, write_logs, get_user_id, update_logs
from src.utils.llmutils import convert_to_langchainmsg
from datetime import datetime
from langchain.memory import ConversationBufferMemory
import uuid

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

if "db" not in st.session_state:
    db = get_database()
    st.session_state.db = db
    # print(f'db is {st.session_state.db}')

if "schema_info" not in st.session_state:
    st.session_state.schema_info = st.session_state.db.get_table_info()
    # print(f'schema_info is {st.session_state.schema_info}')

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
if ((len(query) > 1) and (query != st.session_state.previous_query)) or submit_button:

    messages = st.session_state["messages"]
    result = get_response(
        user_query=query,
        db=st.session_state.db,
        schema_info = st.session_state.schema_info,
        chat_history=convert_to_langchainmsg(st.session_state.chat_history),
    )
    
    st.session_state.chat_history.append(query)    
    st.session_state.chat_history.append(result)
    st.session_state.run_id += 1
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

try:
    print(f'result is {result}')
except Exception as e:    
    result = 'a'
    
if ((len(query) > 1)) and ((len(result)> 1)) or submit_button:
    write_logs(
        user=get_user_id(st.session_state.user),
        user_query=query,
        response=result,
        time=datetime.now(),
        session_id=st.session_state.session_id,
        run_id=st.session_state.run_id,
    )