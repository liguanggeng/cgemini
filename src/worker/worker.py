from typing import Any, Dict

def calculate(expression: str) -> float:
    """
    Calculates the result of a mathematical expression.
    Supports division by zero to test error handling.

    Args:
        expression: The mathematical expression to evaluate, e.g., "2+2" or "10/0".

    Returns:
        The result of the calculation.
    """
    # This is a safe way to evaluate a simple mathematical expression.
    # For a real application, a more robust parsing library should be used.
    # We are intentionally not handling all edge cases to test error handling.
    return eval(expression, {"__builtins__": {}}, {})

# --- Function Registry ---
# A simple dictionary to map function names to the actual Python functions.
# In a real system, this could be populated dynamically by scanning a directory.
_FUNCTIONS = {
    "calculate": calculate,
}

def execute_function(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a function by name with the given arguments and returns the result.
    Includes error handling.

    Args:
        name: The name of the function to execute.
        args: A dictionary of arguments to pass to the function.

    Returns:
        A dictionary containing the result or an error.
    """
    if name not in _FUNCTIONS:
        return {"error": f"Function '{name}' not found."}

    func = _FUNCTIONS[name]
    try:
        # Call the function with the provided arguments
        result = func(**args)
        return {"result": result}
    except Exception as e:
        # Catch any exception and return it as a structured error
        return {
            "error": {
                "type": e.__class__.__name__,
                "message": str(e),
            }
        }