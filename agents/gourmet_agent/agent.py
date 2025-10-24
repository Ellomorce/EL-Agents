import os
import datetime
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset 
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

load_dotenv(".env")
MODEL = os.getenv('TOOLUSE_MODEL')

def get_system_time() -> str:    
    now = datetime.datetime.now()    
    iso8601_time = now.isoformat()  
    return iso8601_time

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="gourmet_agent",
    description="Help you handle all about restaurants and drink shops.",
    instruction="You are an agent that provides services about restaurants and drink shops, you could use mcp-jason to acquire all tools you need.",
    tools=[
        get_system_time,
        MCPToolset(connection_params=StreamableHTTPConnectionParams(url="http://localhost:8081/mcp"))
    ]
)