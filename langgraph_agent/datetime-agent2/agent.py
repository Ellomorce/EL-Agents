import os
import langchain
from datetime import datetime
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    BaseMessage,
    ToolCall,
)
# from langchain.chat_models import init_chat_model
from langchain_litellm import ChatLiteLLM
from langgraph.func import entrypoint, task
from langgraph.graph import add_messages

load_dotenv(".env")
model = os.getenv("MODEL")
api_base = os.getenv("LITELLM_BASE")
api_key = os.getenv("LITELLM_KEY")

# llm = init_chat_model(
#     "anthropic:claude-sonnet-4-5-20250929",
#     temperature=0
# )

llm = ChatLiteLLM(
    # model=model,
    # api_base=api_base,
    # api_key=api_key,
    model="hosted_vllm/gpt-oss-120b",
    api_base="http://10.13.60.113:9098/v1",
    api_key="Jason666",
    temperature=0.7,
    top_p=1.0,
    streaming=True)

# Define tools
@tool
def get_current_datetime():
    """Get current system datetime and return datetime in ISO8601 format.
    """
    return datetime.now().isoformat()

# Augment the LLM with tools
tools = [get_current_datetime]
tools_by_name = {tool.name: tool for tool in tools}
llm_with_tools = llm.bind_tools(tools)

# Step 2: define model node
@task
def call_llm(messages: list[BaseMessage]):
    """LLM decides whether to call a tool or not"""
    return llm_with_tools.invoke(
        [
            SystemMessage(
                content="You are accurate datetime info extractor, your task is to extract datetime information form user query then convert it into ISO8601 format, and output the datatime string only. To analysis the time information in user query, sometimes you will need to know the current dateime, if so, you could call the tool get_current_datetime to get the current datetime."
            )
        ]
        + messages
    )


# Step 3: define tool node
@task
def call_tool(tool_call: ToolCall):
    """Performs the tool call"""
    tool = tools_by_name[tool_call["name"]]
    return tool.invoke(tool_call)


# Step 4: define agent
@entrypoint()
def agent(messages: list[BaseMessage]):
    llm_response = call_llm(messages).result()

    while True:
        if not llm_response.tool_calls:
            break

        # Execute tools
        tool_result_futures = [
            call_tool(tool_call) for tool_call in llm_response.tool_calls
        ]
        tool_results = [fut.result() for fut in tool_result_futures]
        messages = add_messages(messages, [llm_response, *tool_results])
        llm_response = call_llm(messages).result()

    messages = add_messages(messages, llm_response)
    return messages

# Invoke
messages = [HumanMessage(content="我的生日是")]
for chunk in agent.stream(messages, stream_mode="updates"):
    print(chunk)
    print("\n")