import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from agents.sql_agent import run_sql_agent
from agents.rag_agent import run_rag_agent
from agents.graph import run_graph

load_dotenv()

server = Server("apple-support")


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="query_customer_data",
            description=(
                "Query the Apple customer database using natural language. "
                "Use for questions about specific customers, support ticket history, "
                "account details, loyalty tiers, or any structured customer records."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language question about customer data."}
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="query_apple_policies",
            description=(
                "Search Apple's official policy documents using natural language. "
                "Use for questions about return policies, refund terms, AppleCare "
                "coverage, privacy practices, or accessibility services."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language question about Apple policies."}
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="ask_support_assistant",
            description=(
                "General-purpose support assistant. Automatically routes the question "
                "to the customer database, policy documents, or both and returns a "
                "synthesised answer. Use this when unsure which tool to call."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Any customer support question."}
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name, arguments):
    query = arguments.get("query", "")
    if not query:
        return [types.TextContent(type="text", text="No query provided.")]

    if name == "query_customer_data":
        result = await asyncio.to_thread(run_sql_agent, query)
        return [types.TextContent(type="text", text=result)]

    if name == "query_apple_policies":
        result  = await asyncio.to_thread(run_rag_agent, query)
        answer  = result.get("answer", "No answer returned.")
        sources = result.get("sources", [])
        text    = answer + (f"\n\nSources: {', '.join(sources)}" if sources else "")
        return [types.TextContent(type="text", text=text)]

    if name == "ask_support_assistant":
        result = await asyncio.to_thread(run_graph, query)
        text   = f"[Routed to: {result.get('route', 'unknown').upper()}]\n\n{result.get('answer', '')}"
        return [types.TextContent(type="text", text=text)]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
