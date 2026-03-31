"""
mcp_server/test_server.py

Tests the MCP server tools directly without going through the MCP protocol.
Run this to verify the server logic works before wiring it to a client.

Usage:
    python -m mcp_server.test_server
"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from mcp_server.server import list_tools, call_tool

load_dotenv()


async def main():
    print("MCP Server - tool verification")
    print("-" * 50)

    tools = await list_tools()
    print(f"\nRegistered tools ({len(tools)}):")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:60]}...")

    print("\n" + "-" * 50)
    print("Running tool calls:\n")

    test_cases = [
        ("query_customer_data",   {"query": "How many customers have AppleCare?"}),
        ("query_apple_policies",  {"query": "What is the AppleCare cancellation refund policy?"}),
        ("ask_support_assistant", {"query": "Does Brandon Davis have any unresolved tickets?"}),
    ]

    for tool_name, args in test_cases:
        print(f"Tool: {tool_name}")
        print(f"Query: {args['query']}")
        result = await call_tool(tool_name, args)
        print(f"Result: {result[0].text[:300]}...")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
