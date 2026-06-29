import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()
from langgraph.types import Command
from langgraph_agent_lab.graph import build_graph
from langgraph_agent_lab.persistence import build_checkpointer
from langgraph_agent_lab.state import initial_state, Scenario, Route

st.set_page_config(page_title="Support Agent Lab", layout="wide")

st.title("LangGraph Support Ticket Agent")

# Setup environment if not present
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = st.sidebar.text_input("OpenAI API Key", type="password")

if not os.environ.get("OPENAI_API_KEY"):
    st.warning("Please provide your OpenAI API Key to start.")
    st.stop()

# Initialize graph and checkpointer
@st.cache_resource
def get_graph():
    # Make sure we enable interrupt for Real HITL feature
    os.environ["LANGGRAPH_INTERRUPT"] = "true"
    checkpointer = build_checkpointer("sqlite", "streamlit_checkpoints.sqlite")
    return build_graph(checkpointer)

graph = get_graph()

# Session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "st-thread-1"

thread_config = {"configurable": {"thread_id": st.session_state.thread_id}}

def display_state(state):
    st.subheader("Current State")
    st.json({k: v for k, v in state.items() if k not in ["messages", "events", "tool_results"]})
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Audit Events")
        for event in state.get("events", []):
            st.write(f"- **{event['node']}**: {event['message']}")
    
    with col2:
        st.subheader("Tool Results")
        for res in state.get("tool_results", []):
            st.code(res)

    st.subheader("Final Output")
    if state.get("final_answer"):
        st.success(state["final_answer"])
    elif state.get("pending_question"):
        st.info("Pending Question: " + state["pending_question"])

def process_query(query: str):
    # We create a dummy scenario object to get the initial state
    scenario = Scenario(id="streamlit_test", query=query, expected_route=Route.SIMPLE)
    state = initial_state(scenario)
    
    with st.spinner("Processing..."):
        for event in graph.stream(state, config=thread_config):
            pass # stream to completion or interrupt
    st.rerun()

st.sidebar.header("Submit Support Ticket")
query = st.sidebar.text_area("Enter your query (Try 'Refund this customer' to trigger HITL):")
if st.sidebar.button("Send"):
    st.session_state.thread_id = f"st-thread-{os.urandom(4).hex()}"
    thread_config["configurable"]["thread_id"] = st.session_state.thread_id
    process_query(query)

# Check graph state
current_state = graph.get_state(thread_config)

if current_state and current_state.values:
    display_state(current_state.values)
    
    if current_state.next:
        st.warning("Graph execution suspended. Waiting for approval on risky action.")
        st.info(f"Proposed Action: {current_state.values.get('proposed_action')}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve"):
                with st.spinner("Resuming (Approved)..."):
                    graph.invoke(Command(resume={"approved": True, "reviewer": "admin", "comment": "looks good"}), config=thread_config)
                st.rerun()
        with col2:
            if st.button("Reject"):
                with st.spinner("Resuming (Rejected)..."):
                    graph.invoke(Command(resume={"approved": False, "reviewer": "admin", "comment": "rejected by user"}), config=thread_config)
                st.rerun()
else:
    st.info("No active thread. Please submit a query on the left.")
