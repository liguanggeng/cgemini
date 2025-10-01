from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any

app = FastAPI()

# Allow CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data for the UI
mock_chat_history = [
    {"sender": "user", "message": "I need you to call a function to implement the calculation of 1+1"},
    {"sender": "agent", "message": "I can do that. I will call the calculate function."},
]

mock_orchestrator_log = [
    {
        "type": "decision",
        "agent": "Agent1",
        "content": "User wants to perform a calculation. I should use the 'calculate' tool.",
    },
    {
        "type": "function_call",
        "agent": "Agent1",
        "content": {
            "name": "calculate",
            "args": {"expression": "1+1"}
        },
    },
    {
        "type": "execution",
        "source": "Worker",
        "content": "Function 'calculate' returned: 2",
    },
     {
        "type": "final_response",
        "agent": "Agent1",
        "content": "The result of 1+1 is 2.",
    },
]

@app.get("/api/state")
def get_state() -> Dict[str, Any]:
    """
    This endpoint returns the current state of the conversation and orchestrator log.
    """
    return {
        "chatHistory": mock_chat_history,
        "orchestratorLog": mock_orchestrator_log,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
