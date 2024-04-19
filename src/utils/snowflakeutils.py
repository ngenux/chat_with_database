from sqlalchemy import create_engine
import snowflake.connector as sn
import os
from langchain_community.utilities import SQLDatabase
import urllib
from dotenv import load_dotenv


def get_snowflake_engine(
    username, password, hostname, port, database, schema, warehouse=None, role=None
):
    # Construct the connection string
    connection_string = f"snowflake://{username}:{password}@{hostname}/{database}/{schema}?warehouse={warehouse}&role={role}"
    db_engine = create_engine(connection_string)
    return db_engine


def get_database() -> SQLDatabase:
    load_dotenv()
    db_user = os.getenv("username1")
    db_password = urllib.parse.quote_plus(os.getenv("password"))
    db_host = os.getenv("hostname")
    db_name = os.getenv("database")
    db_role = os.getenv("role")
    db_warehouse = os.getenv("warehouse")
    db_schema = os.getenv("schema")

    db_uri = f"snowflake://{db_user}:{db_password}@{db_host}/{db_name}/{db_schema}?warehouse={db_warehouse}&role={db_role}"
    return SQLDatabase.from_uri(db_uri)


def write_logs(user, session_id, user_query, response, time):
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

    cursor.execute(
        "INSERT INTO logs (user_id, session_id, query, response, timestamp) VALUES (%s,%s,%s,%s,%s)",
        (user, session_id, user_query, response, time),
    )


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


def get_user_id(username):
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
    SELECT user_id
    FROM STREAMLIT_APPS.SQLBOT_LOGS.USERS
    WHERE email_id = '{username}'
    """
    return cursor.execute(query).fetchall()[0][0]
