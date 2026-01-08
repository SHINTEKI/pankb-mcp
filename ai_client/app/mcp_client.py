"""
MCP Client: Connect to MCP Server, convert tools to OpenAI function calling format
"""
import os
import json
import logging
from typing import AsyncGenerator
from dataclasses import dataclass
from fastmcp import Client
from fastmcp.utilities.logging import configure_logging
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# Configure logging: FastMCP's RichHandler for console + FileHandler for file
configure_logging(level="INFO")

# Add file handler for persistent logs
os.makedirs('logs', exist_ok=True)
file_handler = logging.FileHandler('logs/mcp_client.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(file_handler)

# Silence noisy third-party modules
for module in ['mcp', 'httpx', 'httpcore']:
    logging.getLogger(module).setLevel(logging.WARNING)


@dataclass
class Message:
    role: str  # "user", "assistant", "tool"
    content: str
    tool_call_id: str | None = None
    tool_calls: list | None = None


class MCPClient:
    def __init__(
        self,
        mcp_server_url: str | None = None,
        model: str = "gpt-4o-mini",
        mcp_token: str | None = None,
    ):
        if mcp_server_url is None:
            mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
        if mcp_token is None:
            mcp_token = os.getenv("MCP_API_KEY", "")

        self.mcp_server_url = mcp_server_url
        self.model = model
        self.mcp_token = mcp_token

        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.tools_cache: list[dict] = []
        self.messages: list[dict] = []

    def _create_mcp_client(self) -> Client:
        """Create a new MCP client instance"""
        if self.mcp_token:
            from fastmcp.client.auth import BearerAuth
            return Client(self.mcp_server_url, auth=BearerAuth(self.mcp_token))
        else:
            return Client(self.mcp_server_url)

    async def connect(self):
        """Connect to MCP Server and fetch tools"""
        async with self._create_mcp_client() as client:
            await self._load_tools(client)

    async def _load_tools(self, client: Client):
        """Load tools from MCP Server and convert to OpenAI format"""
        mcp_tools = await client.list_tools()
        self.tools_cache = []

        for tool in mcp_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema if tool.inputSchema else {"type": "object", "properties": {}}
                }
            }
            self.tools_cache.append(openai_tool)

    async def _call_mcp_tool(self, name: str, arguments: dict) -> str:
        """Call MCP tool with a fresh connection"""
        try:
            async with self._create_mcp_client() as client:
                result = await client.call_tool(name, arguments)
                # Process return result
                if hasattr(result, 'content') and result.content:
                    contents = []
                    for item in result.content:
                        if hasattr(item, 'text'):
                            contents.append(item.text)
                        else:
                            contents.append(str(item))
                    return "\n".join(contents)
                return str(result)
        except Exception as e:
            return f"Error calling tool {name}: {str(e)}"

    async def chat(self, user_message: str) -> str:
        """Send message and get response (non-streaming)"""
        self.messages.append({"role": "user", "content": user_message})

        while True:
            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tools_cache if self.tools_cache else None,
                tool_choice="auto" if self.tools_cache else None
            )

            assistant_message = response.choices[0].message

            # If there are tool calls, execute them
            if assistant_message.tool_calls:
                self.messages.append(assistant_message.model_dump())

                for tool_call in assistant_message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)

                    # Call MCP tool
                    result = await self._call_mcp_tool(func_name, func_args)

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

                # Continue loop to let model process tool results
                continue

            # No tool calls, return final response
            final_content = assistant_message.content or ""
            self.messages.append({"role": "assistant", "content": final_content})
            return final_content

    async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        """Send message and get streaming response"""
        self.messages.append({"role": "user", "content": user_message})

        while True:
            stream = await self.openai.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tools_cache if self.tools_cache else None,
                tool_choice="auto" if self.tools_cache else None,
                stream=True
            )

            collected_content = ""
            tool_calls_data: dict[int, dict] = {}

            async for chunk in stream:
                delta = chunk.choices[0].delta

                # Collect text content
                if delta.content:
                    collected_content += delta.content
                    yield delta.content

                # Collect tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_data:
                            tool_calls_data[idx] = {
                                "id": tc.id or "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            }
                        if tc.id:
                            tool_calls_data[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_data[idx]["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_data[idx]["function"]["arguments"] += tc.function.arguments

            # If there are tool calls
            if tool_calls_data:
                tool_calls_list = [tool_calls_data[i] for i in sorted(tool_calls_data.keys())]
                self.messages.append({
                    "role": "assistant",
                    "content": collected_content or None,
                    "tool_calls": tool_calls_list
                })

                for tc in tool_calls_list:
                    func_name = tc["function"]["name"]
                    func_args = json.loads(tc["function"]["arguments"])

                    yield f"\n\n🔧 Calling tool: {func_name}\n"

                    result = await self._call_mcp_tool(func_name, func_args)

                    yield f"📋 Result: {result}\n\n"

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result
                    })

                # Continue loop to process tool results
                continue

            # No tool calls, end
            if collected_content:
                self.messages.append({"role": "assistant", "content": collected_content})
            break

    def clear_history(self):
        """Clear conversation history"""
        self.messages = []

    def get_available_tools(self) -> list[str]:
        """Get list of available tools"""
        return [t["function"]["name"] for t in self.tools_cache]

    # ===== Resources =====
    async def list_resources(self) -> list:
        """List all available resources"""
        return await self.mcp.list_resources()

    async def read_resource(self, uri: str) -> str:
        """Read resource content"""
        result = await self.mcp.read_resource(uri)
        if result and len(result) > 0:
            item = result[0]
            if hasattr(item, 'text'):
                return item.text
            return str(item)
        return ""

    # ===== Prompts =====
    async def list_prompts(self) -> list:
        """List all available prompt templates"""
        return await self.mcp.list_prompts()

    async def get_prompt(self, name: str, arguments: dict | None = None) -> str:
        """Get prompt template content"""
        result = await self.mcp.get_prompt(name, arguments or {})
        if hasattr(result, 'messages') and result.messages:
            # Extract all message contents
            contents = []
            for msg in result.messages:
                if hasattr(msg, 'content'):
                    if hasattr(msg.content, 'text'):
                        contents.append(msg.content.text)
                    else:
                        contents.append(str(msg.content))
            return "\n".join(contents)
        return str(result)

    async def chat_with_prompt(self, prompt_name: str, prompt_args: dict | None = None) -> str:
        """Chat using preset prompt template"""
        # Get prompt content
        prompt_content = await self.get_prompt(prompt_name, prompt_args)
        # Send prompt content as user message
        return await self.chat(prompt_content)

    async def chat_stream_with_prompt(
        self, prompt_name: str, prompt_args: dict | None = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat using preset prompt template"""
        prompt_content = await self.get_prompt(prompt_name, prompt_args)
        async for chunk in self.chat_stream(prompt_content):
            yield chunk


# Convenience function
async def create_client(
    mcp_server_url: str = "http://localhost:8000/mcp",
    model: str = "gpt-4o-mini"
) -> MCPClient:
    """Create and connect client"""
    client = MCPClient(mcp_server_url, model)
    await client.connect()
    return client
