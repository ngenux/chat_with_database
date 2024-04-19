import urllib.parse
from src.utils.snowflakeutils import get_snowflake_engine
from langchain_openai import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain.agents import AgentType, create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from src.utils.llmutils import get_gemini_llm
import os
from dotenv import load_dotenv
import urllib


load_dotenv()


def get_sql_reponse_with_agent(query):

    db_engine = get_snowflake_engine(
        username=os.getenv("username1"),
        password=urllib.parse.quote_plus(os.getenv("password")),
        hostname=os.getenv("hostname"),
        port=os.getenv("port"),
        database=os.getenv("database"),
        schema=os.getenv("schema"),
        warehouse=os.getenv("warehouse"),
        role=os.getenv("role"),
    )

    llm = ChatOpenAI(
        model_name="gpt-3.5-turbo-1106",
        temperature=0.2,
        openai_api_key=os.getenv("openai_api_key"),
    )

    final_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
          You are a helpful AI assistant expert in querying SQL Database to find answers to user's questions.
          Return the response to the query.
         Use following context to create the SQL query. 
         Context:
         1.Product table contains information about products including product name, and product price.
         2.Transactions table contains information about transactions made by customers including 
         product id of products ordered, transaction amount, transaction date, and customer id.
         3.Customers table contains information about customers including their name and email address.
         4.Shipping table contains the shipping status of each transaction.
        
        Perform join where necessary when the information needed is spread across multiple tables.
          """,
            ),
            ("user", "{question}\n ai: "),
        ]
    )

    db = SQLDatabase(db_engine)

    sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    sql_toolkit.get_tools()

    sqldb_agent = create_sql_agent(
        llm=llm,
        toolkit=sql_toolkit,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
    )

    response = sqldb_agent.run(final_prompt.format(question=query))
    return response


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

    llm = get_gemini_llm()

    def get_schema(_):
        return db.get_table_info()

    return (
        RunnablePassthrough.assign(schema=get_schema) | prompt | llm | StrOutputParser()
    )


def get_response(user_query: str, db: SQLDatabase, chat_history: list):
    try:
        sql_chain = get_sql_chain(db)

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
        return f"Sorry, I am not able to find the response to your query in the database.\n{e}"
