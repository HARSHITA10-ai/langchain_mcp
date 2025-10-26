import mlflow
from dotenv import load_dotenv
import asyncio
import nest_asyncio  # pip install nest-asyncio
from client import main, initialize_agent
from mlflow.entities import Feedback, SpanType, Trace
from mlflow.genai import scorer
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import uuid

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

load_dotenv()

# Configure MLflow
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("Agent output evaluation")

# Disable auto-logging to prevent duplicate traces
mlflow.langchain.autolog(disable=False)
mlflow.openai.autolog(disable=False)

# Initialize agent once globally
print("=" * 60)
print("INITIALIZING AGENT")
print("=" * 60)
asyncio.run(initialize_agent())
print("✅ Agent ready!\n")

# Counter to track predictions
prediction_count = 0


def predict_fn_sync(user_input: str) -> str:
    """Sync wrapper that calls async agent using nested asyncio."""
    global prediction_count
    prediction_count += 1
    
    thread_id = str(uuid.uuid4())
    
    print(f"🔢 Prediction #{prediction_count}: '{user_input[:50]}...'")
    
    with mlflow.start_span(name="agent_prediction") as span:
        span.set_inputs({"user_input": user_input, "prediction_number": prediction_count})
        
        try:
            # Call async main() - nest_asyncio allows this inside MLflow's loop
            result = asyncio.run(main(thread_id=thread_id, user_input=user_input))
            prediction = result["content"]
            
            span.set_outputs({"prediction": prediction})
            span.set_attribute("status", "success")
            
            print(f"✓ Completed prediction #{prediction_count}\n")
            return str(prediction)
        except Exception as e:
            error_msg = f"Error: {e}"
            span.set_outputs({"error": error_msg})
            span.set_attribute("status", "error")
            print(f"✗ Failed prediction #{prediction_count}: {error_msg}\n")
            return error_msg


eval_dataset = [
    {
        "inputs": {"user_input": "hello"},
        "expectations": {
            "answer": "hello, how can i assist with the payroll related queries?",
            "tool_calls": []
        },
    },
    {
        "inputs": {"user_input": "List all payroll projects."},
        "expectations": {
            "answer": "%List of project names%",
            "tool_calls": ["execute_sql"]
        },
    },
    {
        "inputs": {"user_input": "give me the overall summary for all projects"},   
        "expectations": {
            "answer": "%here is the overall defect and threshold summary of the all the project%",
            "tool_calls": ["execute_sql"]
        },
    },
    {
        "inputs": {"user_input": "visualize the overall defect summary for all the projects"},
        "expectations": {
            "answer": "%The chart is generated and here is the summary about the insights%",
            "tool_calls": ["execute_sql", "generate_chart"]
        },
    },
     {
        "inputs": {"user_input": "give me the threshold mismatch for ecc to ecp upgrade"},
        "expectations": {
            "answer": "%here is threshold mismtach for the ecc to ecp upgrade and give the count of the mismatches%",
            "tool_calls": ["execute_sql"]
        },
    },
    {
        "inputs": {"user_input": "give me the threshold mismatch for ecc to ecp upgrade in detailed"},
        "expectations": {
            "answer": "%here is threshold mismtach for the ecc to ecp upgrade and give the count of the mismatches. Along wiht the detailed summary of the mismatches%",
            "tool_calls": ["execute_sql"]
        },
    },
]


judge_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

@scorer
def context_match(outputs, expectations) -> float:
    """LLM-as-a-Judge: Does the output convey the same meaning as expected?"""
    expected = expectations["answer"]
    user_query = expectations.get("inputs", {}).get("user_input", "")

    prompt = f"""
You are an evaluator. Compare the AI's response to the expected answer.

**User Query**: {user_query}
**AI Output**: {outputs}
**Expected Answer**: {expected}

Does the AI output convey the **same core meaning** as the expected answer?
- Answer only with: FULL, PARTIAL, or NONE
- FULL: same meaning, possibly rephrased
- PARTIAL: some overlap, missing key parts
- NONE: unrelated or wrong
"""

    try:
        response = judge_llm.invoke([HumanMessage(content=prompt)])
        judgment = response.content.strip().upper()

        if "FULL" in judgment:
            return 1.0
        elif "PARTIAL" in judgment:
            return 0.5
        else:
            return 0.0
    except Exception as e:
        print(f"Judge error: {e}")
        return 0.0

@scorer
def uses_correct_tools(trace: Trace, expectations: dict) -> Feedback:
    """Evaluate if agent used tools appropriately, ignoring numbered suffixes."""
    expected_tools = expectations["tool_calls"]

    # Parse the trace to get the actual tool calls
    tool_spans = trace.search_spans(span_type=SpanType.TOOL)
    tool_names = [span.name for span in tool_spans]

    # Normalize tool names: remove numeric suffixes like _1, _2, etc.
    import re
    normalized_tools = [re.sub(r"_\d+$", "", name) for name in tool_names]

    # Compare sets instead of exact list to allow duplicates or different order
    if set(normalized_tools) == set(expected_tools):
        score = "yes"
        rationale = "The agent used the correct tools (including repeated calls)."
    else:
        score = "no"
        rationale = (
            f"The agent used incorrect tools. Expected {expected_tools}, "
            f"but got {normalized_tools}"
        )

    return Feedback(value=score, rationale=rationale)


results = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=predict_fn_sync,
    scorers=[context_match, uses_correct_tools],
)
