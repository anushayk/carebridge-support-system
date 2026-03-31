"""
agents/graph.py
"""

import os
from typing import TypedDict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from agents.sql_agent import run_sql_agent
from agents.rag_agent import run_rag_agent

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")


# --- State -------------------------------------------------------------------

class AgentState(TypedDict):
    query:        str
    route:        str
    sql_result:   str
    rag_result:   dict
    final_answer: str


# --- Router ------------------------------------------------------------------

ROUTER_PROMPT = """You are a routing assistant for an Apple customer support system.
Classify the user query into exactly one of three categories:

  sql  - Needs specific customer data, ticket history, account details,
         or any structured records from the database.
         Examples:
           "Give me Brandon Davis's ticket history"
           "How many customers are on the Gold tier?"
           "List all open tickets with critical priority"

  rag  - Needs information from Apple's policy documents only.
         No customer lookup required.
         Examples:
           "What is Apple's refund policy?"
           "What does AppleCare cover?"
           "How does Apple handle data privacy?"

  both - Needs BOTH a customer lookup AND policy knowledge to give
         a complete, specific answer.
         Examples:
           "Does Jason Morris qualify for a refund under Apple's policy?"
           "What coverage does Sarah's AppleCare plan provide for her issue?"

Respond with exactly one word: sql, rag, or both.
No explanation. No punctuation. Just the single word.

Query: {query}
"""


def route_query(state: AgentState) -> AgentState:
    llm   = ChatOpenAI(model=LLM_MODEL, temperature=0,
                       openai_api_key=os.getenv("OPENAI_API_KEY"))
    route = llm.invoke(ROUTER_PROMPT.format(query=state["query"])).content.strip().lower()
    if route not in ("sql", "rag", "both"):
        route = "rag"
    return {**state, "route": route}


# --- Agent nodes -------------------------------------------------------------

def call_sql_agent(state: AgentState) -> AgentState:
    return {**state, "sql_result": run_sql_agent(state["query"])}


def call_rag_agent(state: AgentState) -> AgentState:
    return {**state, "rag_result": run_rag_agent(state["query"])}


POLICY_EXTRACTION_PROMPT = """You are helping route a customer support query.
Extract only the policy-related question from the query below, stripping out
any specific customer names or ticket details. Rephrase it as a clean
question about Apple policy that can be answered from a policy document.

Examples:
  Input:  "Does Jason Morris qualify for a refund on his iPad Air?"
  Output: "What are the conditions for a customer to qualify for a refund on an Apple product?"

  Input:  "Jennifer Rocha has an account access issue. What does Apple policy say?"
  Output: "What is Apple policy on handling account access and identity verification?"

  Input:  "Sarah has an open AppleCare claim. What does her coverage include?"
  Output: "What does AppleCare cover and what are the claim conditions?"

Query: {query}

Respond with only the rephrased policy question. No explanation.
"""


def call_rag_agent_for_both(state: AgentState) -> AgentState:
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0,
                     openai_api_key=os.getenv("OPENAI_API_KEY"))
    policy_query = llm.invoke(
        POLICY_EXTRACTION_PROMPT.format(query=state["query"])
    ).content.strip()
    return {**state, "rag_result": run_rag_agent(policy_query)}


# --- Synthesiser -------------------------------------------------------------

SYNTHESISE_PROMPT = """You are an Apple customer support assistant helping a
support agent named John answer a specific question about a customer.

You have two sources of information:

CUSTOMER DATA (from the support database):
{sql_result}

APPLE POLICY (from official Apple documents):
{rag_result}

Your job is to give a direct, specific answer to John's question using both
sources together. Follow these rules:

1. Start by stating clearly what the customer's situation is based on the data.
2. Then state what Apple's policy says about that exact situation.
3. End with a clear yes/no or recommended action where possible.
4. If the policy documents do not cover the specific situation, say what the
   policy DOES say that is most relevant, then advise John on a practical next
   step he can take as a support agent — such as escalating, checking Apple's
   internal tools, or contacting the relevant team.
5. Never tell John to "visit Apple's website" or "contact Apple Support" —
   John IS Apple Support. Give him actionable internal guidance instead.
6. Never give a vague non-answer. Be direct even when information is incomplete.
7. Keep the answer concise — no more than 4 short paragraphs.

Question: {query}
"""


def synthesise(state: AgentState) -> AgentState:
    llm    = ChatOpenAI(model=LLM_MODEL, temperature=0,
                        openai_api_key=os.getenv("OPENAI_API_KEY"))
    prompt = SYNTHESISE_PROMPT.format(
        query      = state["query"],
        sql_result = state.get("sql_result", "No customer data was found."),
        rag_result = state["rag_result"].get("answer", "No policy information found."),
    )
    answer = llm.invoke(prompt).content.strip()
    return {**state, "final_answer": answer}


def finalise_sql(state: AgentState) -> AgentState:
    return {**state, "final_answer": state["sql_result"]}


def finalise_rag(state: AgentState) -> AgentState:
    answer  = state["rag_result"].get("answer", "No answer returned.")
    sources = state["rag_result"].get("sources", [])
    footer  = f"\n\nSources: {', '.join(sources)}" if sources else ""
    return {**state, "final_answer": answer + footer}


# --- Routing edge ------------------------------------------------------------

def decide_route(state: AgentState) -> str:
    return state["route"]


# --- Graph -------------------------------------------------------------------

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("router",       route_query)
    graph.add_node("sql_agent",    call_sql_agent)
    graph.add_node("rag_agent",    call_rag_agent)
    graph.add_node("both_sql",     call_sql_agent)
    graph.add_node("both_rag",     call_rag_agent_for_both)
    graph.add_node("synthesiser",  synthesise)
    graph.add_node("finalise_sql", finalise_sql)
    graph.add_node("finalise_rag", finalise_rag)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        decide_route,
        {"sql": "sql_agent", "rag": "rag_agent", "both": "both_sql"},
    )

    graph.add_edge("sql_agent",    "finalise_sql")
    graph.add_edge("rag_agent",    "finalise_rag")
    graph.add_edge("both_sql",     "both_rag")
    graph.add_edge("both_rag",     "synthesiser")
    graph.add_edge("finalise_sql", END)
    graph.add_edge("finalise_rag", END)
    graph.add_edge("synthesiser",  END)

    return graph.compile()


def run_graph(query: str) -> dict:
    app = build_graph()
    initial_state: AgentState = {
        "query":        query,
        "route":        "",
        "sql_result":   "",
        "rag_result":   {"answer": "", "sources": []},
        "final_answer": "",
    }
    result = app.invoke(initial_state)
    return {
        "answer":  result["final_answer"],
        "route":   result["route"],
        "sources": result["rag_result"].get("sources", []),
    }


# --- Test --------------------------------------------------------------------

if __name__ == "__main__":
    test_queries = [
        "Give me an overview of customer Brandon Davis and his support history.",
        "What is Apple's policy on returning a product after 14 days?",
        "Jason Morris has an open refund request ticket. Does he qualify for a refund under Apple's policy?",
        "Jennifer Rocha has an open Account Access ticket. What does Apple's policy say about account support?",
    ]

    print("LangGraph router - test queries")
    print("-" * 50)
    for query in test_queries:
        print(f"\nQ: {query}")
        result = run_graph(query)
        print(f"Route: {result['route'].upper()}")
        print(f"A: {result['answer']}")
        print("-" * 50)
