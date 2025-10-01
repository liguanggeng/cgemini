import streamlit as st
import uuid
from typing import List, Dict, Any, Optional

# --- Import Orchestrator Components ---
# Assuming the src directory is in the python path.
# In a real project, this would be a proper package.
from src.orchestrator.top_level import (
    TopLevelOrchestrator,
    TaskContext,
    TaskState,
    KnowledgeSnapshot,
    ConversationTurn,
)
from src.orchestrator.gemini_gateway import GeminiAgentGateway

# --- In-Memory Collaborators for Demo ---
# These are simple, non-persistent implementations for the Streamlit app.

class InMemoryTaskRegistry:
    """A simple in-memory store for task states."""
    def __init__(self):
        self._tasks = {}
    def register(self, user_request: str) -> str:
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {"user_request": user_request, "state": "pending"}
        st.session_state.last_task_id = task_id
        return task_id
    def update_state(self, task_id: str, state: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["state"] = state

class InMemoryKnowledgeService:
    """A simple in-memory knowledge source."""
    def load_snapshot(self) -> KnowledgeSnapshot:
        return KnowledgeSnapshot()
    def commit_updates(self, updates: Any) -> None:
        print(f"Knowledge updates would be committed here: {updates}")

class SimpleFeedbackRouter:
    """A simple feedback router based on Agent3's decision."""
    def route(self, review_payload: Any, context: TaskContext) -> None:
        decision = review_payload.get("decision", "revise")
        if decision == "approve":
            context.mark_state(TaskState.CODING)
        elif decision == "reject":
            context.mark_state(TaskState.FAILED)
        else:
            context.mark_state(TaskState.BUILDING)

from src.worker import worker

# --- Orchestrator Initialization ---

def get_orchestrator() -> TopLevelOrchestrator:
    """Initializes and returns a cached instance of the orchestrator."""
    if 'orchestrator' not in st.session_state:
        st.session_state.orchestrator = TopLevelOrchestrator(
            task_registry=InMemoryTaskRegistry(),
            knowledge_service=InMemoryKnowledgeService(),
            agent_gateway=GeminiAgentGateway(),
            feedback_router=SimpleFeedbackRouter(),
            worker=worker,  # Pass the worker module
        )
    return st.session_state.orchestrator

# --- UI Rendering Functions ---

def render_chat_history(context: Optional[TaskContext]):
    """Renders the conversation history from the TaskContext."""
    if not context:
        return
    for turn in context.history:
        # We only want to show user and model messages in the chat window
        if turn.role in ["user", "model"]:
            # Map 'model' role to 'assistant' for Streamlit's chat_message
            display_role = "assistant" if turn.role == "model" else turn.role
            with st.chat_message(display_role):
                st.markdown(turn.content)

def render_orchestrator_log(context: Optional[TaskContext]):
    """Renders a structured log from the TaskContext history and artifacts."""
    if not context:
        return
    st.write(f"**Task ID:** `{context.task_id}`")
    st.write(f"**Status:** `{context.task_state.value}`")
    
    for turn in context.history:
        if turn.role == "system":
            with st.expander(f":gear: **SYSTEM**: {turn.content}"):
                if turn.metadata:
                    st.json(turn.metadata)
        elif turn.role.startswith("agent"):
            with st.expander(f":robot_face: **{turn.role.upper()}** says: {turn.content}"):
                if turn.metadata:
                    st.json(turn.metadata)
        elif turn.role == "user":
            # User messages are already in the chat panel
            pass
        else: # Errors, etc.
             with st.expander(f":warning: **{turn.role.upper()}**: {turn.content}"):
                if turn.metadata:
                    st.json(turn.metadata)

# --- Main Application Logic ---

st.set_page_config(page_title="AI Collaboration Control Room", layout="wide")
st.title("AI Collaboration Control Room")

# Initialize orchestrator and context in session state
orchestrator = get_orchestrator()
if "context" not in st.session_state:
    st.session_state.context = None

# Define UI layout
col1, col2 = st.columns(2)

# --- Left Panel: Chat ---
with col1:
    st.header("Chat")
    render_chat_history(st.session_state.context)

    # Handle chat input
    if prompt := st.chat_input("Ask the agent to do something..."):
        context = st.session_state.context
        
        # If there is no active context or the last task is finished, start a new one.
        if context is None or context.task_state in [TaskState.DONE, TaskState.FAILED]:
            with st.spinner("Agent1 is processing your new request..."):
                st.session_state.context = orchestrator.handle_new_task(prompt)
        
        # If the conversation is ongoing, handle the user's reply.
        elif context.task_state == TaskState.CLARIFYING:
            with st.spinner("Agent1 is processing your reply..."):
                st.session_state.context = orchestrator.handle_user_reply(context, prompt)
        
        # Re-run the script to update the UI
        st.rerun()

# --- Right Panel: Orchestrator Log ---
with col2:
    st.header("Orchestrator Log")
    render_orchestrator_log(st.session_state.context)