"""
Workflow node functions for the scientific agent.
"""

import json
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from scientifc_agent.models import AgentState, DecisionMakingOutput, JudgeOutput, PlanOutput
from scientifc_agent.prompts import DECISION_MAKING_PROMPT, PLANNING_PROMPT, AGENT_PROMPT, JUDGE_PROMPT
from scientifc_agent.tools import TOOLS, TOOLS_DICT
from scientifc_agent.utils import format_tools_description

# Initialize LLMs - Update to use Gemini 2.0 model with correct name
base_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)


decision_making_llm = base_llm.with_structured_output(DecisionMakingOutput)
agent_llm = base_llm.bind_tools(TOOLS)
planning_llm = base_llm.with_structured_output(PlanOutput)
judge_llm = base_llm.with_structured_output(JudgeOutput)

def decision_making_node(state: AgentState):
    """Entry point of the workflow. Based on the user query, the model can either respond directly or perform a full research, routing the workflow to the planning node"""
    system_prompt = SystemMessage(content=DECISION_MAKING_PROMPT)
    response: DecisionMakingOutput = decision_making_llm.invoke([system_prompt] + state.messages)
    output = {"requires_research": response.requires_research}
    if response.answer is not None:
        output["answer"] = response.answer
    return output

def router(state: AgentState):
    """Router directing the user query to the appropriate branch of the workflow."""
    if state.requires_research:
        return "planning"
    else:
        return "end"

def planning_node(state: AgentState):
    """Planning node that creates a step by step plan to answer the user query."""
    system_prompt_content = PLANNING_PROMPT.format(tools=format_tools_description(TOOLS))
    
    # Construct messages for the planning_llm.
    messages_for_planner = [SystemMessage(content=system_prompt_content)] + list(state.messages) 
    
    try:
        plan_object: PlanOutput = planning_llm.invoke(messages_for_planner)
        plan_json_str = plan_object.model_dump_json(indent=2)
        ai_message_with_plan = AIMessage(content=f"```json\n{plan_json_str}\n```")
        return {"messages": [ai_message_with_plan]}
    except Exception as e:
        error_message = f"Error during planning: Failed to generate a structured plan. {str(e)}"
        return {"messages": [AIMessage(content=error_message)]}

def tools_node(state: AgentState):
    """
    Tool call node that executes tools and summarizes their output for history.
    This is CRITICAL to keep the message history concise.
    """
    outputs = []
    ai_message_with_tool_calls = state.messages[-1]
    
    if not isinstance(ai_message_with_tool_calls, AIMessage) or not ai_message_with_tool_calls.tool_calls:
        return {"messages": [AIMessage(content="Error: No tool calls found in the last AI message.")]}

    for tool_call in ai_message_with_tool_calls.tool_calls:
        tool_output_raw = TOOLS_DICT[tool_call["name"]].invoke(tool_call["args"])

        tool_message_content = "" # This will be our final, summarized content

        if tool_call["name"] == "search-papers":
            # If the tool returned a list of paper dictionaries
            if isinstance(tool_output_raw, list) and tool_output_raw:
                summary_parts = [f"Search successful. Found {len(tool_output_raw)} papers."]
                summary_parts.append("Top 3 results:")
                
                # Create a concise summary of the top 3 papers
                for i, paper in enumerate(tool_output_raw[:3]):
                    title = paper.get('title', 'N/A')
                    authors = paper.get('authors', 'N/A')
                    # Truncate abstract here for conciseness
                    abstract_snippet = (paper.get('abstract', 'N/A')[:300] + '...') if paper.get('abstract') else 'N/A'
                    summary_parts.append(f"  {i+1}. Title: {title}\n     Authors: {authors}\n     Abstract Snippet: {abstract_snippet}")
                
                if len(tool_output_raw) > 3:
                    summary_parts.append("\nMore results are available for detailed analysis if needed.")

                tool_message_content = "\n".join(summary_parts)
            
            # If the tool returned a simple string (e.g., error or "No results")
            elif isinstance(tool_output_raw, str):
                tool_message_content = tool_output_raw
            else:
                tool_message_content = "Search tool returned an unexpected data format."

        elif tool_call["name"] == "download-paper":
            if isinstance(tool_output_raw, str) and len(tool_output_raw) > 1500:
                print(f"TOOLS_NODE: 'download-paper' returned long text ({len(tool_output_raw)} chars). Creating a summary placeholder for ToolMessage.")
                # In a real scenario, you'd call `base_llm` to summarize `tool_output_raw`.
                # For now, a placeholder is sufficient to avoid the API error.
                tool_message_content = f"Paper content has been downloaded (length: {len(tool_output_raw)}). The agent should now proceed to analyze this content (which is not fully in history). Start of content: {tool_output_raw[:500]}..."
            else:
                tool_message_content = str(tool_output_raw) # For short text or error messages
        else: # For other tools like ask-human-feedback
            tool_message_content = str(tool_output_raw)

        # Final check for safety, but the specific handlers above are better
        if len(tool_message_content) > 3000:
            tool_message_content = tool_message_content[:3000] + "... (content truncated)"

        outputs.append(
            ToolMessage(
                content=tool_message_content, 
                name=tool_call["name"],
                tool_call_id=tool_call["id"]
            )
        )
    return {"messages": outputs}




def agent_node(state: AgentState):
    """Agent call node that uses the LLM with tools to answer the user query."""
    system_prompt = SystemMessage(content=AGENT_PROMPT) # AGENT_PROMPT uses the new version
    
    # The plan and conversation history (including tool outputs) are in state.messages
    response = agent_llm.invoke([system_prompt] + state.messages)
    return {"messages": [response]}

def should_continue(state: AgentState):
    """Check if the agent should continue or end."""
    messages = state.messages
    last_message = messages[-1]

    # End execution if there are no tool calls
    if last_message.tool_calls:
        return "continue"
    else:
        return "end"

def judge_node(state: AgentState):
    """Node to let the LLM judge the quality of its own final answer."""
    num_feedback_requests = getattr(state, "num_feedback_requests", 0)
    if num_feedback_requests >= 2:
        return {"is_good_answer": True}

    system_prompt = SystemMessage(content=JUDGE_PROMPT)
    response: JudgeOutput = judge_llm.invoke([system_prompt] + state.messages)
    output = {
        "is_good_answer": response.is_good_answer,
        "num_feedback_requests": num_feedback_requests + 1
    }
    if response.feedback:
        output["messages"] = [AIMessage(content=response.feedback)]
    return output

def final_answer_router(state: AgentState):
    """Router to end the workflow or improve the answer."""
    if state.is_good_answer:
        return "end"
    else:
        return "planning" 