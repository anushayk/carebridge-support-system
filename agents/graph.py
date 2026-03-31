import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from agents.sql_agent import run_sql_agent
from agents.rag_agent import run_rag_agent

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")


class AgentState(TypedDict):
    query:        str
    route:        str
    sql_result:   str
    rag_result:   dict
    final_answer: str


ROUTER_PROMPT = """You are a routing assistant for a customer support system.
Classify the query into exactly one of three categories:

  sql  - Requires looking up specific customer data, ticket history, or
         structured records from the database.

  rag  - Requires information from Apple policy documents only.
         No customer lookup needed.

  both - Requires both a customer lookup and policy information to give
         a complete answer.

Examples of each:
  sql:  "Give me Brandon Davis's ticket history"
  sql:  "How many customers are on the Gold tier?"
  rag:  "What is Apple's refund policy?"
  rag:  "What does AppleCare cover?"
  both: "Does Jason Morris qualify for a refund under Apple's policy?"
  both: "What coverage applies to Sarah's open AppleCare claim?"

Respond with exactly one word: sql, rag, or both.

Query: {query}
"""

POLICY_EXTRACTION_PROMPT = """Extract only the policy-related question from the query below.
Strip out any customer names or ticket details and rephrase it as a clean question
about Apple policy that can be answered from a policy document.

Examples:
  Input:  "Does Jason Morris qualify for a refund on his iPad Air?"
  Output: "What are the conditions for a customer to qualify for a refund on an Apple product?"

  Input:  "Jennifer Rocha has an account access issue. What does Apple policy say?"
  Output: "What is Apple's policy on handling account access and identity verification?"

Query: {query}

Respond with only the rephrased policy question.
"""

SYNTHESISE_PROMPT = """You are a customer support assistant helping a customer support executive
answer a specific question about a customer.

You have two sources of information:

CUSTOMER DATA:
{sql_result}

APPLE POLICY:
{rag_result}

Give a direct, specific answer using both sources. Follow these rules:
1. Start with the customer's situation based on the data.
2. State what Apple's policy says about that situation.
3. End with a clear recommended action.
4. If the policy documents don't cover the specific situation, use the most
   relevant policy available and advise on a practical next step such as
   escalating or checking internal tools.
5. Never tell the executive to visit Apple's website or contact Apple Support —
   they are already Apple Support. Give actionable internal guidance instead.
6. Be direct even when information is incomplete. No vague non-answers.
7. Keep the response to 4 short paragraphs maximum.

Question: {query}
"""


def route_query(state):
    llm   = ChatOpenAI(model=LLM_MODEL, temperature=0, openai_api_key=os.getenv("OPENAI_API_KEY"))
    route = llm.invoke(ROUTER_PROMPT.format(query=state["query"])).content.strip().lower()
    if route not in ("sql", "rag", "both"):
        route = "rag"
    return {**state, "route": route}


def call_sql_agent(state):
    return {**state, "sql_result": run_sql_agent(state["query"])}


def call_rag_agent(state):
    return {**state, "rag_result": run_rag_agent(state["query"])}


def call_rag_agent_for_both(state):
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0, openai_api_key=os.getenv("OPENAI_API_KEY"))
    policy_query = llm.invoke(
        POLICY_EXTRACTION_PROMPT.format(query=state["query"])
    ).content.strip()
    return {**state, "rag_result": run_rag_agent(policy_query)}


def synthesise(state):
    llm    = ChatOpenAI(model=LLM_MODEL, temperature=0, openai_api_key=os.getenv("OPENAI_API_KEY"))
    prompt = SYNTHESISE_PROMPT.format(
        query      = state["query"],
        sql_result = state.get("sql_result", "No customer data found."),
        rag_result = state["rag_result"].get("answer", "No policy information found."),
    )
    return {**state, "final_answer": llm.invoke(prompt).content.strip()}


def finalise_sql(state):
    return {**state, "final_answer": state["sql_result"]}


def finalise_rag(state):
    answer  = state["rag_result"].get("answer", "No answer returned.")
    sources = state["rag_result"].get("sources", [])
    footer  = f"\n\nSources: {', '.join(sources)}" if sources else ""
    return {**state, "final_answer": answer + footer}


def decide_route(state):
    return state["route"]


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
    graph.add_conditional_edges("router", decide_route, {
        "sql":  "sql_agent",
        "rag":  "rag_agent",
        "both": "both_sql",
    })
    graph.add_edge("sql_agent",    "finalise_sql")
    graph.add_edge("rag_agent",    "finalise_rag")
    graph.add_edge("both_sql",     "both_rag")
    graph.add_edge("both_rag",     "synthesiser")
    graph.add_edge("finalise_sql", END)
    graph.add_edge("finalise_rag", END)
    graph.add_edge("synthesiser",  END)

    return graph.compile()


def run_graph(query):
    result = build_graph().invoke({
        "query":        query,
        "route":        "",
        "sql_result":   "",
        "rag_result":   {"answer": "", "sources": []},
        "final_answer": "",
    })
    return {
        "answer":  result["final_answer"],
        "route":   result["route"],
        "sources": result["rag_result"].get("sources", []),
    }


if __name__ == "__main__":
    tests = [
        "Give me an overview of customer Brandon Davis and his support history.",
        "What is Apple's refund policy?",
        "Jason Morris has an open refund request. Does he qualify under Apple's policy?",
    ]
    for q in tests:
        result = run_graph(q)
        print(f"Q: {q}")
        print(f"Route: {result['route'].upper()}")
        print(f"A: {result['answer']}\n")
