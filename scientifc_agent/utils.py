"""
Utility functions for the scientific agent.
"""

import json
from typing import Optional
from langchain_core.messages import BaseMessage, HumanMessage # Import HumanMessage
from langchain_core.tools import BaseTool
from IPython.display import display, Markdown
from langgraph.graph.state import CompiledStateGraph

def format_tools_description(tools: list[BaseTool]) -> str:
    """Format the tools description for use in prompts.
    
    Args:
        tools: List of tools
        
    Returns:
        Formatted string with tool descriptions
    """
    return "\n\n".join([f"- {tool.name}: {tool.description}\n Input arguments: {tool.args}" for tool in tools])

async def print_stream(app: CompiledStateGraph, user_input_str: str) -> Optional[BaseMessage]: # Renamed 'input' to 'user_input_str'
    """Stream the results of the agent's execution.
    
    Args:
        app: The compiled state graph
        user_input_str: The user input string
        
    Returns:
        The last message from the agent's execution
    """
    display(Markdown("## New research running"))
    display(Markdown(f"### Input:\n\n{user_input_str}\n\n"))
    display(Markdown("### Stream:\n\n"))

    all_messages = []
    # Wrap the initial user input string in a HumanMessage
    initial_messages_for_graph = [HumanMessage(content=user_input_str)]
    try:
        async for chunk in app.astream({"messages": initial_messages_for_graph}, stream_mode="updates"):
            for component_name, updates_from_component in chunk.items(): # Iterate through components in the chunk
                if messages := updates_from_component.get("messages"):
                    # messages here are the new messages *from this update step*
                    # all_messages should store the complete sequence from the state if needed,
                    # or just the messages printed. For returning the last message, this is fine.
                    all_messages.extend(messages) 
                    for message in messages:
                        if isinstance(message, BaseMessage):
                            message.pretty_print()
                        else:
                            # This case should ideally not happen
                            print(f"Streaming a non-BaseMessage object: {message}")
                        print("\n\n")
    except Exception as e:
        print(f"Error during streaming: {str(e)}")
        print("This could be due to API issues or model configuration problems.")
        
    if not all_messages:
        return None
    
    # Return the very last message object that was part of the stream's updates
    # Note: If the error happens mid-LLM call, this might not be the "final AI answer"
    # but the last piece of state updated.
    return all_messages[-1]