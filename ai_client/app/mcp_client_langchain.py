"""
MCP Client (LangChain version): Simplified code using langchain-mcp-adapters
"""
import os
from typing import AsyncGenerator

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

load_dotenv()


class MCPClientLangChain:
    def __init__(
        self,
        mcp_server_url: str | None = None,
        model: str = "gpt-4o-mini"
    ):
        if mcp_server_url is None:
            mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
        self.mcp_server_url = mcp_server_url
        self.model = model
        self.mcp_client: MultiServerMCPClient | None = None
        self.agent = None
        self.messages: list = []

    async def connect(self):
        """Connect to MCP Server"""
        self.mcp_client = MultiServerMCPClient({
            "pankb": {
                "url": self.mcp_server_url,
                "transport": "streamable_http",
            }
        })
        await self.mcp_client.__aenter__()

        # Get tools and create agent
        tools = self.mcp_client.get_tools()
        llm = ChatOpenAI(model=self.model)
        self.agent = create_react_agent(llm, tools)

    async def disconnect(self):
        """Disconnect from server"""
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)

    async def chat(self, user_message: str) -> str:
        """Send message and get response"""
        self.messages.append({"role": "user", "content": user_message})

        response = await self.agent.ainvoke({"messages": self.messages})

        # Extract the last AI response
        ai_message = response["messages"][-1]
        content = ai_message.content if hasattr(ai_message, 'content') else str(ai_message)

        self.messages.append({"role": "assistant", "content": content})
        return content

    async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        """Send message and get streaming response"""
        self.messages.append({"role": "user", "content": user_message})

        collected_content = ""

        async for event in self.agent.astream_events(
            {"messages": self.messages},
            version="v2"
        ):
            kind = event["event"]

            # Stream output LLM generated text
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, 'content') and chunk.content:
                    collected_content += chunk.content
                    yield chunk.content

            # Display tool calls
            elif kind == "on_tool_start":
                tool_name = event["name"]
                yield f"\n\n🔧 Calling tool: {tool_name}\n"

            elif kind == "on_tool_end":
                tool_output = event["data"]["output"]
                yield f"📋 Result: {tool_output}\n\n"

        if collected_content:
            self.messages.append({"role": "assistant", "content": collected_content})

    def clear_history(self):
        """Clear conversation history"""
        self.messages = []

    def get_available_tools(self) -> list[str]:
        """Get list of available tools"""
        if self.mcp_client:
            return [t.name for t in self.mcp_client.get_tools()]
        return []


# Convenience function
async def create_client(
    mcp_server_url: str = "http://localhost:8000/mcp",
    model: str = "gpt-4o-mini"
) -> MCPClientLangChain:
    """Create and connect client"""
    client = MCPClientLangChain(mcp_server_url, model)
    await client.connect()
    return client
