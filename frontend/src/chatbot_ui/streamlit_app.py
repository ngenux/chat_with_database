import streamlit as st
import uuid
from datetime import datetime
import snowflake.connector as sn
from dotenv import load_dotenv
import os


def load_streamlit():
    if login_page():
        st.switch_page("pages/chatwindow.py")

def authenticate_creds(username, password):
    load_dotenv()
    conn = sn.connect(
        user=os.getenv("username1"),
        password=os.getenv("password"),
        role=os.getenv("role"),
        schema=os.getenv("logs_schema"),
        account=os.getenv("hostname"),
        database=os.getenv("database"),
    )
    cursor = conn.cursor()
    query = f"""
    SELECT COUNT(*)
    FROM STREAMLIT_APPS.SQLBOT_LOGS.USERS
    WHERE email_id = '{username}'
    AND password = '{password}'
    """
    if cursor.execute(query).fetchall()[0][0] > 0:
        return True
    else:
        return False

# Login page
def login_page():
    st.title("Login Page")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")

    if login_button:
        if authenticate_creds(username, password):
            st.success("Login successful!")
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.user = username
            st.session_state.session_start = str(datetime.now())
            # Clear the login page content
            # session_dicts = []
            # for i in get_values_for_string(search_string=st.session_state.user):
            #     session_dicts.append(
            #         {
            #             "session_id": st.session_state.session_id,
            #             "user_id": st.session_state.user,
            #             "table": i,
            #         }
            #     )
            # create_session(data_dict=session_dicts)
            return True
        else:
            st.error("Invalid username or password")
            return False
