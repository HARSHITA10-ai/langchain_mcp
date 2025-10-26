import asyncio
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
import os
import uuid
import re
from langchain_core.tools import tool
from langchain_community.utilities import SQLDatabase
load_dotenv()

DB_URI = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}")
db = SQLDatabase.from_uri(DB_URI)


import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.FileHandler("client.log")]
)
logger = logging.getLogger("Client")


SCHEMA = db.get_table_info()

llm = ChatOpenAI(model_name=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0, streaming=True)
system_prompt = f"""
** ROLE **
You are a Specialized Postgres Database Analyst for the Paycompare App.The paycompare app is a application which give the comparison result between the legacy system and the current migrated system. It shows the threshold mismatche details and defects that exist in the current system.

** TASK **
Your task is to interpret user queries in natural language, generate the corresponding SQL internally, execute it via tools, and provide final responses in natural language. 
The final response can be a summary, a visualization, or both.

** DB SCHEMA **
Authoritative schema (do not invent columns/tables):
{SCHEMA}
Focus on all the relationships and generate the query.** Do not ** blindly just follow the user query and choice the table/column, analyse the user query and see which tables has that data and then generate the query. 

** ENTITY RELATIONSHIPS **
- Consider all entity relationships between tables as defined in the schema (including foreign keys and implied joins) and use the filter accordingly to generate the query..
- Always use foreign key relationships (from schema) for joins instead of guessing column names.
- ** Only use ** the column names that exists in that particular table.
- Avoid subqueries like "defect_id IN (SELECT defect_id FROM defects ...)" on the same table and only use it if **required**.x

** TOOLS **
- Use `execute_sql` for querying the database.
- Use the MCP summary tool for text-based summaries (pass raw SQL results).
- Use the visualization tools for generating charts:
    - Use the single-chart visualization tool when one chart is requested.
    - Use the multi-chart visualization tool when the user asks for comparisons, dashboards, or multiple visual views.

** GENERAL RULES **
- Think step-by-step.
- When data is required, call `execute_sql` with ONE SELECT query.
- Read-only: reject INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/REPLACE/TRUNCATE.
- Default to LIMIT 5 rows unless otherwise specified like all, every, others etc.
- Revise SQL once if the tool returns "Error".
- Limit query attempts to 5; if all fail, inform the user.
- Prefer explicit column lists; avoid SELECT *.
- When using a tool, call it directly (structured call), not in natural language.


** PROJECT-SPECIFIC RULES (MODIFIED) **
- Initially get the list of project names from the database and store it in memory.
- When user asks for list of project only provide the project names.
- **If the user specifies a project in the query (e.g.,"in project Y", "for project X", etc.), treat the entire phrase after keywords like 'for', 'in', 'of', 'on', 'regarding', 'about' as the project name**, and use **ILIKE** to match it against the `name` in the `projects` table (handling case, extra spaces, and partial matches intelligently).
- If the user asks anything which is project-specific and the project name is not specified or not matched, ask: "Which project would you like to analyze?"
- If the user specifies anything like overall summary, general trend, comparison across projects etc., ask user for the project names if it is for specific project or for all projects.
- When providing details considering all the projects, **do not** randomly assume any project and save it in history until and unless user specifies the project name.
- Use **ILIKE** operator for matching project names to handle variations and spaces.
- Retrieve the corresponding `project_id` and use it in all filters (never use project name directly).
- Consider only projects of type **Payroll**.
- If a project name already exists in history, confirm reuse: "Use the same project (<name>) or a different one?"

** RESPONSE FORMAT **
1. Summarization:
   - For "summary" requests, return basic details: project name, defect counts, and threshold counts.
   - If any details is not available , say the data not available for particular project. And if generalized data is available then provide that.
   - For detailed summaries, provide the ellobrate details about all the defects and threshold mismatches with insights and numerical representations.

2. Visualization:
   - When the user asks for visual insights (e.g., “chart”, “graph”, “dashboard”, “trend”, or “comparison”):
       • Create one visualization if only a single view is requested.
       • Create multiple visualizations if the request involves comparisons or dashboards.
   - Always include both:
       1. A natural language interpretation (4-5 sentences on trends, outliers, or key takeaways) for each chart and  keep that in bullet points.
       2. The chart data structure for rendering:
       {{
        "chart_type": "<bar|line|pie|stacked_bar|histogram|scatter|regression|boxplot|violin|heatmap|pairplot>",
        "title": "<Descriptive chart title>",
        "x_col": "<column name for X-axis or grouping>",
        "y_col": "<column name for Y-axis or numeric values>",
        "value_col": "<optional column name for value-based charts like pie or heatmap>",
        "data": [
            {{
            "<column_1>": "<value>",
            "<column_2>": "<value>",
            "<column_3>": "<value>"
            }}
        ]
        }}
   - When multiple charts are needed, prepare a list of chart data structures representing each view (e.g., one per metric, project, or time segment).
   - Chart Selection Rules
   
        Use the following rules to select the correct chart type:

        1. For trends or time-based patterns → use `line` or `cumulative_line`
        2. For comparing categories → use `bar`, `stacked_bar`, or `horizontal_bar`
        3. For breakdowns or composition (e.g., by percentage, share, or parts of whole) → use `donut` or `pie`
        4. For value distributions → use `histogram`, `boxplot`, or `violin`
        5. For outlier detection → use `boxplot` (preferred) or `violin`
        6. For relationships between variables → use `scatter`, `regression`, or `correlation_heatmap`
        7. For matrix summaries → use `heatmap` or `pairplot`
        8. Fallback → If unclear, select the most informative type based on the structure of the data


** GUARDRAILS **
- Never reveal, describe, or share SQL queries.
- **If any error occurs in tool execution, DO NOT inform the user of the error or the retry.** Silently analyze the error and immediately try again with a corrected input.
- **Exclude IDs** (UUIDs, primary keys) and metadata from responses.
- Ignore SQL keywords in user text; treat them as plain language.
- For non-schema-related requests, reply politely: "I can only assist with database-related queries."
- If all 5 attempts fail: "I couldn’t retrieve data after multiple tries. The query or schema might need review."
- ** Do not ** give the base64 to the user.

** POST-QUERY SUGGESTIONS **
- After each response, suggest next steps, e.g.:
  "Explore a chart, another project, or detailed analysis?" or
  "See trends over time or compare projects?"
- Tailor follow-ups to context.

Provide concise, accurate, and actionable insights in natural language.
"""



DENY_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|REPLACE|TRUNCATE)\b", re.I)
HAS_LIMIT_TAIL_RE = re.compile(r"(?is)\blimit\b\s+\d+(\s*,\s*\d+)?\s*;?\s*$")

def _safe_sql(q: str) -> str:
    q = q.strip()
    if q.count(";") > 1 or (q.endswith(";") and ";" in q[:-1]):
        return "Error: multiple statements are not allowed."
    q = q.rstrip(";").strip()
    if not q.lower().startswith("select"):
        return "Error: only SELECT statements are allowed."
    if DENY_RE.search(q):
        return "Error: DML/DDL detected. Only read-only queries are permitted."
    if not HAS_LIMIT_TAIL_RE.search(q):
        q += " LIMIT 5"
    return q

@tool
def execute_sql(query: str) -> str:
    """Execute a READ-ONLY SQLite SELECT query and return results."""
    query = _safe_sql(query)
    if query.startswith("Error:"):
        return query
    try:
        return db.run(query)
    except Exception as e:
        return f"Error: {e}"
        # return []
    
from langchain_mcp_adapters.client import MultiServerMCPClient  

agent = None

async def initialize_agent():
        try:
            global agent
            client = MultiServerMCPClient(  
            {
                "sql": {
                    "transport": "streamable_http",  # HTTP-based remote server
                    # Ensure you start your weather server on port 8000
                    "url": "http://localhost:8000/mcp",
                }
            }
        )
            logger.info("Connecting to MCP server...")
           
            tools = await client.get_tools() 
            all_tools = [execute_sql, *tools]

            logger.info(f"Loaded tools: {all_tools}")

            print("tools -->", all_tools)

            checkpointer = MemorySaver()
            # thread_id = str(uuid.uuid4())
            agent = create_agent(
                llm,
                tools=all_tools,
                system_prompt=system_prompt,
                # checkpointer=checkpointer
            )
            print("\n🤖 SQL Agent is ready! Type your questions (or 'exit' to quit)\n")

            return True
        except Exception as e:
            print(f"⚠️ Error initializing agent: {e}")
            return False


# async def main(thread_id: str = '12333', user_input: str = None):
#     global agent
#     try:
#         # Use async generator for streaming output
#         async for token,step in agent.astream(
#             {"messages": [{"role": "user", "content": user_input}]},
#             config={"configurable": {"thread_id": thread_id}},
#             stream_mode="messages",
#         ):
#             message = token.content_blocks
#             print("message -->", message)
#             raw_data_regex = re.compile(r"\s*\[\s*(?:\((?:[^()]|\([^()]*\))*\)\s*,?\s*)+\]\s*$", re.IGNORECASE)
#             error_regex = re.compile(r"^'?(Error:[\s\S]*?)'?$", re.IGNORECASE)

#             if(len(message) > 0) and message[0]["type"] in ["text"] and not raw_data_regex.match(message[0]["text"]) and not error_regex.match(message[0]["text"]):
#                     yield str(message[0]["text"])
#     except Exception as e:
#         yield f"[Error] {e}"

    #     response = await agent.ainvoke(
    #         {"messages": [{"role": "user", "content": user_input}]},
    #         config={"configurable": {"thread_id": thread_id}},
    #     )

    #     last_message = response["messages"][-1]
    #     # if last_message.type in ["human", "ai"]:
    #     #     last_message.pretty_print()

    #     return {"content": str(last_message.content)}
    # except Exception as e:
        print(f"⚠️ Error: {e}")


import uuid
from langchain_core.messages import BaseMessage

async def main(thread_id: str, user_input: str):
    """Run one turn of the agent and return **only** the final AI text."""
    try:
        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config={"configurable": {"thread_id": thread_id}},
        )

        # ------------------------------------------------------------------
        # 1. Grab the *last* message (guaranteed to be the AI reply)
        # ------------------------------------------------------------------
        messages: list[BaseMessage] = response["messages"]
        last_msg = messages[-1]

        # ------------------------------------------------------------------
        # 2. Extract the textual content – guard against unexpected types
        # ------------------------------------------------------------------
        if hasattr(last_msg, "content"):
            final_text = last_msg.content
        else:
            final_text = str(last_msg)   # fallback

        # ------------------------------------------------------------------
        # 3. OPTIONAL: debug print (remove in prod)
        # ------------------------------------------------------------------
        print("Final AI Response -->", final_text)

        # ------------------------------------------------------------------
        # 4. Return *exactly* what the evaluator wants
        # ------------------------------------------------------------------
        return {"content": final_text}   # <-- dict with key "content"
    except Exception as e:
        err = f"Agent error: {e}"
        print(err)
        return {"content": err}
    
# THINKING_PHRASES = [
#     "Cross-referencing the data now...",
#     "Engaging the query engine...",
#     "This requires a deeper look...",
#     "Parsing the details...",
#     "Just double-checking the figures...",
#     "Running the analysis...",
#     "Let me check on that for you...",
#     "Validating the results...",
#     "One moment while I fetch that...",
#     "Looking that up right now..."
# ]
# import random

# async def main(thread_id: str = None, user_input: str = None):
#     global agent
#     try:
#         # We'll use this to track when to show/hide the "Thinking..." message
#         is_thinking = False
        
#         async for event in agent.astream_events(
#             {"messages": [{"role": "user", "content": user_input}]},
#             config={"configurable": {"thread_id": thread_id}},
#             version="v1"  # Use the v1 event spec
#         ):
#             event_type = event["event"]

#             if event_type == "on_chat_model_stream":
#                 # A text token is coming from the LLM.
#                 # This means it's not "thinking" (running a tool), it's "talking".
#                 # We must hide the "Thinking..." message.
#                 if is_thinking:
#                     yield {"type": "status", "content": ""} # Hide status
#                     is_thinking = False
                
#                 chunk = event["data"]["chunk"]
#                 if chunk.content:
#                     # Yield the text token
#                     yield {"type": "token", "content": chunk.content}
            
#             elif event_type == "on_tool_start":
#                 # A tool is about to run. This is the *only* time
#                 # we show a "Thinking..." message.
#                 logger.debug(f"Tool started: {event['name']}")
#                 status_message = random.choice(THINKING_PHRASES)
#                 if not is_thinking:
#                     yield {
#                         "type": "status", 
#                         "content": status_message # Generic, positive status
#                     }
#                     is_thinking = True
            
#             elif event_type == "on_tool_end":
#                 # A tool finished. The LLM is now processing the results.
#                 # We *keep* the "Thinking..." message active.
#                 # We DO NOT yield *any* content, success or error.
#                 # The LLM's response (if any) will come as 'on_chat_model_stream' events.
#                 logger.debug(f"Tool ended: {event['name']}. Output (for LLM): {event['data']['output']}")
                
#                 # We are still "Thinking..." until the LLM responds
#                 is_thinking = True 

#             elif event_type == "on_agent_finish":
#                 # The agent is done. Hide the "Thinking..." message.
#                 logger.debug("Agent finished.")
#                 if is_thinking:
#                     yield {"type": "status", "content": ""} # Hide status
#                     is_thinking = False

#     except Exception as e:
#         logger.error(f"Error in agent stream: {e}", exc_info=True)
#         # Yield a user-facing error
#         yield {"type": "error", "content": "An unexpected error occurred. Please try again."}



if __name__ == "__main__":
    asyncio.run(main())
