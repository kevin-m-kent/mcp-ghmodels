import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import (
        AssistantMessage,
        ChatCompletionsToolDefinition,
        CompletionsFinishReason,
        FunctionDefinition,
        SystemMessage,
        ToolMessage,
        UserMessage
    )
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import json

load_dotenv()  # load environment variables from .env

MODEL="gpt-4o"

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.ghmodels = ChatCompletionsClient(endpoint="https://models.inference.ai.azure.com",
                    credential=AzureKeyCredential(os.getenv("GITHUB_TOKEN")))

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])


    async def process_query(self, query: str) -> str:
        """Process a query using GitHub Models and available tools"""
        messages = [
            UserMessage(content=query)
        ]

        response = await self.session.list_tools()

        available_tools = [ChatCompletionsToolDefinition(
            function=FunctionDefinition(
                name=tool.name,
                description=tool.description,
                parameters=tool.inputSchema
            )
        ) for tool in response.tools]

        # # Initial GH Models API call
        response = self.ghmodels.complete(
            model=MODEL,
            messages=messages,
            tools=available_tools
        )

        # # Process response and handle tool calls
        tool_results = []
        final_text = []

        #for content in response.content:
        for choice in response.choices:
            if choice.finish_reason != CompletionsFinishReason.TOOL_CALLS:
                final_text.append(choice.message.content)
            else:
                tool_call = choice.message.tool_calls[0]
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments.replace("'", '"'))
                
                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                tool_results.append({"call": tool_name, "result": result})
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                # Continue conversation with tool results
                if choice.message.content:
                    messages.append(AssistantMessage(choice.message.content))
                    
                messages.append(UserMessage(content=str(result.content)))

                # Get next response from GH Models
                response = self.ghmodels.complete(
                    model=MODEL,
                    messages=messages,
                )

                final_text.append(response.choices[0].message.content)

            return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())