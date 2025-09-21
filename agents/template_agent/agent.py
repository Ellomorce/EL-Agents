import os
from google.adk.agents import Agent
from .prompt import return_instructions

root_agent = Agent(
    model='gemini-2.5-flash',
    name='template_agent',
    instruction=return_instructions(),
    tools=[]
)