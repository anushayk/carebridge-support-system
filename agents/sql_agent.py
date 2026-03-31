import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain.agents.agent_types import AgentType

load_dotenv()

DB_PATH   = os.getenv("DB_PATH", "data/apple_support.db")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

SYSTEM_PROMPT = """You are a customer support data assistant with access to a SQLite database.
The database has two tables:

  customers:
    customer_id, name, email, phone, city, country, apple_id,
    account_since, preferred_device, loyalty_tier,
    total_purchases, applecare_member

  support_tickets:
    ticket_id, customer_id, product, issue_type, description,
    channel, priority, status, created_at, updated_at,
    resolved_at, resolution_summary, satisfaction_rating, agent_name

When searching by customer name, use a case-insensitive LIKE query.
Always join customers and support_tickets on customer_id when the question
involves both profile details and ticket history.
Return results as a clear, readable summary rather than raw data.
If no matching records are found, say so plainly.
"""


def build_sql_agent():
    db  = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    return create_sql_agent(
        llm=llm,
        db=db,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        system_message=SYSTEM_PROMPT,
        verbose=False,
    )


def run_sql_agent(query):
    result = build_sql_agent().invoke({"input": query})
    return result.get("output", "No result returned.")


if __name__ == "__main__":
    tests = [
        "Give me a quick overview of customer Brandon Davis and his support ticket history.",
        "How many customers are on the Gold or Platinum loyalty tier?",
        "Which issue type has the lowest average satisfaction rating?",
    ]
    for q in tests:
        print(f"Q: {q}")
        print(f"A: {run_sql_agent(q)}\n")
