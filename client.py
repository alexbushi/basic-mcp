import asyncio
import json
import nest_asyncio
from typing import Any, Dict, List, Optional
from contextlib import AsyncExitStack
from openai import AsyncOpenAI

from mcp import ClientSession
from mcp.client.sse import sse_client
from dotenv import load_dotenv

load_dotenv()

nest_asyncio.apply()

class MCPOpenAIClient:
    """Client for interacting with OpenAI models using MCP tools."""

    def __init__(self, model: str = "gpt-4o"):
        """Initialize the OpenAI MCP client.

        Args:
            model: The OpenAI model to use.
        """
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = AsyncOpenAI()
        self.model = model
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None

    async def connect_to_server(self, session: ClientSession):
        """Connect to an MCP server using an existing session."""
        await session.initialize()
        self.session = session

        tools_result = await self.session.list_tools()
        print("\nConnected to server with tools:")
        for tool in tools_result.tools:
            print(f"  - {tool.name}: {tool.description}")

    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get available tools from the MCP server in OpenAI format.

        Returns:
            A list of tools in OpenAI format.
        """
        tools_result = await self.session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools_result.tools
        ]
    
    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available MCP tools."""
        tools = await self.get_mcp_tools()

        response = await self._send_to_openai(query, [], tools, True)
        assistant_message = response.choices[0].message
        messages = [{"role": "user", "content": query}, assistant_message]

        if not assistant_message.tool_calls:
            return assistant_message.content
        else:
            print(f"Tool calling: {assistant_message.tool_calls}")

        # Process tool calls and augment messages
        await self._handle_tool_calls(assistant_message.tool_calls, messages)

        final_response = await self._send_to_openai("", messages=messages, tools=tools, allow_tool_calls=False)
        return final_response.choices[0].message.content


    async def _send_to_openai(
        self,
        query: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        allow_tool_calls: bool = True,
    ):
        """Send message(s) to OpenAI with optional tool call support."""
        if not messages and not query:
            raise ValueError("Either 'query' or 'messages' must be provided.")

        if not messages:
            messages = [{"role": "user", "content": query}]

        return await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto" if allow_tool_calls else "none",
        )


    async def _handle_tool_calls(self, tool_calls, messages):
        """Process tool calls and append results to messages."""
        for tool_call in tool_calls:
            result = await self.session.call_tool(
                tool_call.function.name,
                arguments=json.loads(tool_call.function.arguments),
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result.content[0].text,
            })
    
    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    client = MCPOpenAIClient()

    async with sse_client("http://localhost:8050/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await client.connect_to_server(session)

            query = "What's 1 plus 1?"
            print(f"\nQuery: {query}")

            response = await client.process_query(query)
            print(f"\nResponse: {response}")


if __name__ == "__main__":
    asyncio.run(main())