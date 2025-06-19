"""
Main scientific agent workflow using LangGraph.
"""

import os
import urllib3
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

# Change from relative to absolute imports
from scientifc_agent.models import AgentState, CoreAPIWrapper
from scientifc_agent.nodes import (
    decision_making_node,
    router,
    planning_node,
    tools_node,
    agent_node,
    should_continue,
    judge_node,
    final_answer_router
)
from scientifc_agent.utils import print_stream

# Disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()


def create_agent_workflow():
    """Create the scientific agent workflow.
    
    Returns:
        The compiled workflow graph
    """
    # Create the workflow
    workflow = StateGraph(AgentState)
    
    # Add nodes to the graph
    workflow.add_node("decision_making", decision_making_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("tools", tools_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("judge", judge_node)
    
    # Set the entry point of the graph
    workflow.set_entry_point("decision_making")
    
    # Add edges between nodes
    workflow.add_conditional_edges(
        "decision_making",
        router,
        {
            "planning": "planning",
            "end": END,
        }
    )
    workflow.add_edge("planning", "agent")
    workflow.add_edge("tools", "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "tools",
            "end": "judge",
        },
    )
    workflow.add_conditional_edges(
        "judge",
        final_answer_router,
        {
            "planning": "planning",
            "end": END,
        }
    )
    
    # Compile the graph
    return workflow.compile()

# Create the agent workflow
app = create_agent_workflow()

# Sample test inputs
test_inputs = [
    "Download and summarize the findings of this paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC11379842/pdf/11671_2024_Article_4070.pdf",
    "Can you find 8 papers on quantum machine learning?",
    """Find recent papers (2023-2024) about CRISPR applications in treating genetic disorders,
    focusing on clinical trials and safety protocols""",
    """Find and analyze papers from 2023-2024 about the application of transformer architectures in protein folding prediction,
    specifically looking for novel architectural modifications with experimental validation."""
]

async def run_test_inputs():
    """Run the agent on the test inputs."""
    outputs = []
    for test_input in test_inputs:
        final_answer = await print_stream(app, test_input)
        outputs.append(final_answer.content)
    return outputs

# This allows running the agent directly or importing it as a module
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_test_inputs())

