import streamlit as st
from google.cloud import bigquery
import uuid
from datetime import datetime
from src.utils.snowflakeutils import authenticate_creds


def load_streamlit():
    if login_page():
        st.switch_page("pages/chatwindow.py")


# Function to authenticate username and password
def authenticate(username, password):
    client = bigquery.Client()
    query = f"""
    SELECT COUNT(*)
    FROM rag-exploration-417710.user.user_credentials
    WHERE user_id = '{username}'
      AND password = '{password}'
    """

    # Execute the query
    query_job = client.query(query)

    # Get the query result
    result = query_job.result()

    # Iterate through the result rows
    for row in result:
        count = row[0]  # Assuming the result is a single value representing count
        if count > 0:
            return True  # Authentication successful
        else:
            return False  # Authentication failed


def authenticate_hardcoded(username, password):
    if username == "test@ngenux.com" and password == "ngenuxrag":
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
