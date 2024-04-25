import urllib.parse
from src.utils.snowflakeutils import get_snowflake_engine

# from langchain.chat_models.vertexai import ChatVertexAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain.sql_database import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from src.utils.llmutils import get_gemini_llm
import os
from dotenv import load_dotenv
import urllib


load_dotenv()


def get_sql_chain(db, schema_info):

    template = """
    You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database.
    Based on the table schema below, write a SQL query that would answer the user's question. Take the conversation history into account.
    Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table. Perform joins wherever necessary.
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

    llm = get_gemini_llm()

    # def get_schema(_):
    #     return db.get_table_info()

    return (
        RunnablePassthrough.assign(schema=lambda x: schema_info) | prompt | llm | StrOutputParser()
    )


def get_response(user_query: str, db: SQLDatabase, schema_info: str,chat_history: list):
    try:
        sql_chain = get_sql_chain(db, schema_info)

        template = """
        You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database.
        Based on the table schema below, question, sql query, and sql response, write a natural language response.
        <SCHEMA>{schema}</SCHEMA>

        Conversation History: {chat_history}
        SQL Query: <SQL>{query}</SQL>
        User question: {question}
        SQL Response: {response}"""

        prompt = ChatPromptTemplate.from_template(template)

        llm = get_gemini_llm()

        chain = (
            RunnablePassthrough.assign(query=sql_chain).assign(
                schema=lambda x: schema_info,
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
        return f"Sorry, I am not able to find the response to your query in the database."
