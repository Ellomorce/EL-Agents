import os
from google.adk.agents import Agent
from dotenv import load_dotenv
from tools.milvustool import MilvusTool

load_dotenv()
agent_prompt = ""
milvus_tool = MilvusTool()

root_agent = Agent(
    model='gemini-2.5-flash',
    name='ask_rag_agent',
    instruction=agent_prompt,
    tools=[
        milvus_tool,
    ]
)

# Testing
if __name__ == "__main__":
    response = rag_agent.run("請問我的信用卡遺失了該怎麼辦?")
    print(response)