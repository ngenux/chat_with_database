from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
import streamlit as st
import os, urllib

# llms
from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain.llms import OpenAI
# from langchain_openai import ChatOpenAI
# from langchain_groq import ChatGroq

load_dotenv()
def init_database() -> SQLDatabase:
    db_user = os.getenv("USER")
    db_password = urllib.parse.quote_plus(os.getenv("PASSWORD"))
    db_host = os.getenv("HOST")
    db_name = os.getenv("DB_NAME")
    db_role = os.getenv("ROLE")
    db_warehouse = os.getenv("WAREHOUSE")
    db_schema = os.getenv("SCHEMA")

    db_uri = f"snowflake://{db_user}:{db_password}@{db_host}/{db_name}/{db_schema}?warehouse={db_warehouse}&role={db_role}"
    return SQLDatabase.from_uri(db_uri)
    
def get_llm():
    gemini_api_key = os.getenv("GOOGLE_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=gemini_api_key,
                             temperature=0.3, convert_system_message_to_human=True)
    return llm

def get_sql_chain(db):
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

    llm = get_llm()

    def get_schema(_):
        return db.get_table_info()

    return (
    RunnablePassthrough.assign(schema=get_schema)
    | prompt
    | llm
    | StrOutputParser()
    )
    
def get_response(user_query: str, db: SQLDatabase, chat_history: list):
    sql_chain = get_sql_chain(db)
    # print(f'sql query is {sql_chain}')

    template = """
    You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database.
    Based on the table schema below, question, sql query, and sql response, write a natural language response.
    <SCHEMA>{schema}</SCHEMA>

    Conversation History: {chat_history}
    SQL Query: <SQL>{query}</SQL>
    User question: {question}
    SQL Response: {response}"""

    prompt = ChatPromptTemplate.from_template(template)

    llm = get_llm()

    chain = (
    RunnablePassthrough.assign(query=sql_chain).assign(
      schema=lambda _: db.get_table_info(),
      response=lambda vars: db.run(vars["query"]),
    )
    | prompt
    | llm
    | StrOutputParser()
    )

    return chain.invoke({
    "question": user_query,
    "chat_history": chat_history,
    })
    
  
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
      AIMessage(content="Hello! I'm a SQL assistant. Ask me anything about your database."),
    ]
    db = init_database()
    st.session_state.db = db


st.set_page_config(page_title="Chat with Database", page_icon=":speech_balloon:")

st.title("Chat with Database")

    
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(message.content)

user_query = st.chat_input("Type a message...")
if user_query is not None and user_query.strip() != "":
    st.session_state.chat_history.append(HumanMessage(content=user_query))
    
    with st.chat_message("Human"):
        st.markdown(user_query)
        
    with st.chat_message("AI"):
        try:
            response = get_response(user_query, st.session_state.db, st.session_state.chat_history)
        except Exception as e:
            response = "We are not able to find the response."
        st.markdown(response)
        
    st.session_state.chat_history.append(AIMessage(content=response))