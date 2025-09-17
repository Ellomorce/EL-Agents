import os
import datetime
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset 
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

# The Version using LiteLLM
load_dotenv(".env")
auth_headers = {"Authorization":f"Bearer {os.getenv("LITELLM_KEY")}"}
litellm_base = os.getenv("LITELLM_BASE")

def get_system_time() -> str:    
    now = datetime.datetime.now()    
    iso8601_time = now.isoformat()  
    return iso8601_time  

# You must name main agent as root_agent in agent.py for ADK Web to run properly.
root_agent = LlmAgent(
    model=LiteLlm(
        model="hosted_vllm/hosted_vllm/Qwen3-32B", # ADK會將第一個/前視為provider，所以litellm中provider要重複
        api_base=litellm_base,
        extra_headers=auth_headers,
    ),
    name="gourmet_agent",
    description="Help you handle all about restaurants and drink shops.",
    instruction="You are an agent that provides services about restaurants and drink shops, you could use mcp-jason to acquire all tools you need.",
    tools=[
        get_system_time,
        MCPToolset(connection_params=StreamableHTTPConnectionParams(url="http://10.13.60.113:8081/mcp"))
    ]
)