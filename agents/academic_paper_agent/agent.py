"""Academic_Research: Research advice, related literature finding, research area proposals, web knowledge access."""
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from . import prompt
from .sub_agents.paper_abstractor import paper_abstract_agent
from .sub_agents.academic_websearcher import academic_websearch_agent

MODEL = "gemini-2.5-pro"

academic_coordinator = LlmAgent(
    name="academic_coordinator",
    model=MODEL,
    description=(
        "analyzing seminal papers provided by the users, "
        "providing research advice, locating current papers "
        "relevant to the seminal paper, generating suggestions "
        "for new research directions, and accessing web resources "
        "to acquire knowledge"
    ),
    instruction=prompt.COORDINATOR_PROMPT,
    output_key="seminal_paper",
    tools=[
        AgentTool(agent=academic_websearch_agent),
        AgentTool(agent=paper_abstract_agent),
    ],
)

root_agent = academic_coordinator