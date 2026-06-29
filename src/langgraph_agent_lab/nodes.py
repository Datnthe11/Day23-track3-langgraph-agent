"""Node functions for the LangGraph workflow.

Each function receives AgentState and returns a partial state update dict.
Do NOT mutate input state — return new values only.
"""

from __future__ import annotations

from .state import AgentState, make_event, Route
from .llm import get_llm
from pydantic import BaseModel, Field
import os
from langgraph.types import interrupt

def intake_node(state: AgentState) -> dict:
    """Normalize raw query. This node is provided as a working example."""
    query = state.get("query", "").strip()
    return {
        "query": query,
        "messages": [f"intake:{query[:40]}"],
        "events": [make_event("intake", "completed", "query normalized")],
    }

def classify_node(state: AgentState) -> dict:
    class RouteClassification(BaseModel):
        route: Route = Field(description="The classified route for the query.")
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(RouteClassification)
    
    prompt = f"""You are a support agent intent classifier.
Classify the following query into one of these routes:
- risky: Actions with side effects like refunds, deletions, sending emails, cancellations.
- tool: Information lookups like order status, tracking, search queries.
- missing_info: Vague or incomplete queries lacking actionable context.
- error: System failures, timeouts, crashes, service unavailable.
- simple: General questions answerable without tools or actions.

Priority: risky > tool > missing_info > error > simple

Query: {state.get('query', '')}
"""
    result = structured_llm.invoke(prompt)
    route = result.route
    risk_level = "high" if route == Route.RISKY else "low"
    
    return {
        "route": route, 
        "risk_level": risk_level, 
        "events": [make_event("classify_node", "completed", f"Classified as {route}")]
    }

def tool_node(state: AgentState) -> dict:
    attempt = state.get("attempt", 0)
    route = state.get("route", "")
    
    if route == Route.ERROR and attempt < 2:
        result_string = "ERROR: Timeout failure while processing request"
    else:
        result_string = "Success: Tool executed successfully"
        
    return {
        "tool_results": [result_string], 
        "events": [make_event("tool_node", "completed", "Tool executed")]
    }

def evaluate_node(state: AgentState) -> dict:
    class Evaluation(BaseModel):
        evaluation_result: str = Field(description="Must be 'needs_retry' or 'success'")
        
    tool_results = state.get("tool_results", [])
    latest_result = tool_results[-1] if tool_results else ""
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(Evaluation)
    prompt = f"""Evaluate the following tool result.
If the result contains an error or failure, return 'needs_retry'.
Otherwise, return 'success'.

Tool Result: {latest_result}
"""
    eval_res = structured_llm.invoke(prompt)
    result_str = eval_res.evaluation_result
    
    return {
        "evaluation_result": result_str, 
        "events": [make_event("evaluate_node", "completed", f"Evaluated as {result_str}")]
    }

def answer_node(state: AgentState) -> dict:
    llm = get_llm()
    query = state.get("query", "")
    tool_results = state.get("tool_results", [])
    approval = state.get("approval", {})
    
    context = []
    if tool_results:
        context.append(f"Tool Results: {tool_results}")
    if approval:
        context.append(f"Approval Decision: {approval}")
        
    prompt = f"""You are a helpful support agent.
Answer the user's query using the provided context.

Query: {query}
Context: {context}
"""
    response = llm.invoke(prompt)
    answer = response.content if hasattr(response, "content") else str(response)
    
    return {
        "final_answer": answer, 
        "events": [make_event("answer_node", "completed", "Answer generated")]
    }

def ask_clarification_node(state: AgentState) -> dict:
    llm = get_llm()
    query = state.get("query", "")
    prompt = f"""The following user query is vague or incomplete.
Ask a short, specific clarification question.

Query: {query}
"""
    response = llm.invoke(prompt)
    question = response.content if hasattr(response, "content") else str(response)
    
    return {
        "pending_question": question, 
        "final_answer": question, 
        "events": [make_event("ask_clarification_node", "completed", "Asked clarification")]
    }

def risky_action_node(state: AgentState) -> dict:
    llm = get_llm()
    query = state.get("query", "")
    prompt = f"""The user wants to perform a risky action.
Describe the proposed action based on the query.

Query: {query}
"""
    response = llm.invoke(prompt)
    action = response.content if hasattr(response, "content") else str(response)
    
    return {
        "proposed_action": action, 
        "events": [make_event("risky_action_node", "completed", "Prepared risky action")]
    }

def approval_node(state: AgentState) -> dict:
    if os.getenv("LANGGRAPH_INTERRUPT", "").lower() == "true":
        # Suspend execution and wait for input
        approval_decision = interrupt({"action": state.get("proposed_action", "")})
    else:
        approval_decision = {"approved": True, "reviewer": "mock", "comment": ""}
        
    return {
        "approval": approval_decision, 
        "events": [make_event("approval_node", "completed", "Approval processed")]
    }

def retry_or_fallback_node(state: AgentState) -> dict:
    attempt = state.get("attempt", 0) + 1
    return {
        "attempt": attempt, 
        "errors": ["Transient error encountered"], 
        "events": [make_event("retry_or_fallback_node", "completed", f"Attempt {attempt}")]
    }

def dead_letter_node(state: AgentState) -> dict:
    answer = "System failure cannot recover after multiple attempts"
    return {
        "final_answer": answer, 
        "events": [make_event("dead_letter_node", "completed", "Max retries exceeded")]
    }

def finalize_node(state: AgentState) -> dict:
    return {
        "events": [make_event("finalize", "completed", "workflow finished")]
    }
