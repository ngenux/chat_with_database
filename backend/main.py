# base libraries
import functions_framework
import os
import logging as logging
import json
import re
import urllib
from datetime import datetime
import time

# llm model
from langchain_google_genai import ChatGoogleGenerativeAI

# langchain database
from langchain_community.utilities import SQLDatabase

# langchain libs
from langchain.prompts.chat import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import AIMessage, HumanMessage

# snowflake connector
import snowflake.connector as sn

def get_properties():
    properties_dict = {}
    properties_dict["googleapi_key"] = "AIzaSyCWqyqXNgPvHdRRqq0Jrt-mziAC2WYq8Vg"    
    properties_dict["username"] = "NG_SRIKANTH"
    properties_dict["password"] = "Mercedes@123"
    properties_dict["hostname"] = "fe87374.central-india.azure"
    properties_dict["database"] = "STREAMLIT_APPS"
    properties_dict["schema"] = "MARKETPLACE_DATA"
    properties_dict["warehouse"] = "COMPUTE_WH"
    properties_dict["role"] = "DEVELOPER"
    properties_dict["logs_schema"] = "SQLBOT_LOGS"

    return properties_dict

def get_database() -> SQLDatabase:
    project_properties_dict = get_properties()
    db_user = project_properties_dict["username"]
    db_password = urllib.parse.quote_plus(project_properties_dict["password"])
    db_host = project_properties_dict["hostname"]
    db_name = project_properties_dict["database"]
    db_schema = project_properties_dict["schema"]
    db_warehouse = project_properties_dict["warehouse"]
    db_role = project_properties_dict["role"]

    db_uri = f"snowflake://{db_user}:{db_password}@{db_host}/{db_name}/{db_schema}?warehouse={db_warehouse}&role={db_role}"
    return SQLDatabase.from_uri(db_uri)

# get database
db = get_database()

def get_gemini_llm():
    project_properties_dict = get_properties()
    gemini_api_key = project_properties_dict["googleapi_key"]
    llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=gemini_api_key,
        temperature=0.3,
        convert_system_message_to_human=True,
    )
    return llm

def get_sql_chain(llm):
    template = """
    You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database.
    Based on the table schema below, write a SQL query that would answer the user's question. Take the conversation history into account.
    Pay attention to use only the column names you can see in the tables below. Be careful to not query 
    for columns that do not exist. Also, pay attention to which column is in which table.
    <SCHEMA>{schema}</SCHEMA>

    Conversation History: {chat_history}

    Write only the SQL query and nothing else. Do not wrap the SQL query in any other text, not even backticks.

    For example:
    Question: which 3 artists have the most tracks?
    SQL Query: SELECT ArtistId, COUNT(*) as track_count FROM Track GROUP BY ArtistId ORDER BY track_count DESC LIMIT 3;
    Question: Name 10 artists
    SQL Query: SELECT Name FROM Artist LIMIT 10;

    Your turn:

    Question: {question}
    SQL Query:
    """

    prompt = ChatPromptTemplate.from_template(template)

    def get_schema(_):
        return db.get_table_info()

    return (
        RunnablePassthrough.assign(schema=get_schema) | prompt | llm | StrOutputParser()
    )

def get_response(user_query, chat_history, llm):
    try:
        sql_chain = get_sql_chain(llm)

        template = """
        You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database.
        Based on the table schema below, question, sql query, and sql response, write a natural language response.
        <SCHEMA>{schema}</SCHEMA>

        Conversation History: {chat_history}
        SQL Query: <SQL>{query}</SQL>
        User question: {question}
        SQL Response: {response}"""

        prompt = ChatPromptTemplate.from_template(template)

        chain = (
            RunnablePassthrough.assign(query=sql_chain).assign(
                schema=lambda _: db.get_table_info(),
                response=lambda vars: db.run(vars["query"]),
            )
            | prompt
            | llm
            | StrOutputParser()
        )

        return chain.invoke(
            {
                "question": user_query,
                "chat_history": chat_history,
            }
        )
    except Exception as e:
        return f"Sorry, I am not able to find the response to your query in the database"

def get_db_connection():
    project_properties_dict = get_properties()
    conn = sn.connect(
        user=project_properties_dict["username"],
        password=project_properties_dict["password"],
        role=project_properties_dict["role"],
        schema=project_properties_dict["logs_schema"],
        account=project_properties_dict["hostname"],
        database=project_properties_dict["database"],
    )
    cursor = conn.cursor()
    return cursor    

def write_logs(user, session_id, user_query, response, time, cursor):
    cursor.execute(
        "INSERT INTO logs (user_id, session_id, query, response, timestamp) VALUES (%s,%s,%s,%s,%s)",
        (user, session_id, user_query, response, time),
    )
    
def convert_to_langchainmsg(session):
    chat_history = []
    for i, k in enumerate(session):
        if i % 2 == 0:
            chat_history.append(HumanMessage(k))
        else:
            chat_history.append(AIMessage(k))
    return chat_history


def get_user_id(username, cursor):
    query = f"""
    SELECT user_id
    FROM STREAMLIT_APPS.SQLBOT_LOGS.USERS
    WHERE email_id = '{username}'
    """
    return cursor.execute(query).fetchall()[0][0]

@functions_framework.http
def hello_http(request):
    try:
        request_json = request.get_json(silent=True)
        request_args = request.args
        
        # get llm model
        llm_model = get_gemini_llm() 

        # parsing the json request        
        if request_json and "query" in request_json and "chat_history" in request_json and "username" in request_json and "session_id" in request_json:
            query = request_json["query"]
            sesssion_chat_history = request_json["chat_history"]
            user = request_json["username"]
            session_id = request_json["session_id"]
        elif request_args and "query" in request_args and "chat_history" in request_args  and "username" in request_args and "session_id" in request_args:
            query = request_args["query"]
            sesssion_chat_history = request_args["chat_history"]
            user = request_args["username"]
            session_id = request_args["session_id"]
        else:
            logging.info("Requried parameters are missing.")
             
        
        # calling llm to get response        
        result = get_response(
            user_query=query,
            chat_history=convert_to_langchainmsg(sesssion_chat_history),
            llm = llm_model,
        )       


        # get database connection for writing the logs    
        cursor = get_db_connection()         
        
        # writing the logs to database       
        user_id = get_user_id(user, cursor)
        write_logs(
            user=user_id,
            user_query=query,
            response=result,
            time=datetime.now(),
            session_id=session_id,
            cursor = cursor
        )           

        return {"statusCode": 200, "response": json.dumps("{}".format(result))}
    except Exception as e:
        return "Error:{}".format(e)
