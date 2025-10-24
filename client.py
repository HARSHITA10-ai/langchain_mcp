# import asyncio
# from mcp import ClientSession, StdioServerParameters
# from langchain_openai import ChatOpenAI
# from langchain_mcp_adapters.tools import load_mcp_tools
# from langgraph.prebuilt import create_react_agent
# from langgraph.checkpoint.memory import MemorySaver
# from dotenv import load_dotenv
# import os
# import uuid
# import re
# from langchain_core.tools import tool

# from langchain_community.utilities import SQLDatabase
# load_dotenv()

# DB_URI = (
#     f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
#     f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}")
# db = SQLDatabase.from_uri(DB_URI)


# SCHEMA = db.get_table_info()

# llm = ChatOpenAI(model_name=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0)
# system_prompt = f"""
# ** ROLE **
# You are a Specialized Postgres Database Analyst for the Paycompare App.The paycompare app is a application which give the comparison result between the legacy system and the current migrated system. It shows the threshold mismatche details and defects that exist in the current system.

# ** TASK **
# Your task is to interpret user queries in natural language, generate the corresponding SQL internally, execute it via tools, and provide final responses in natural language. 
# The final response can be a summary, a visualization, or both.

# ** DB SCHEMA **
# Authoritative schema (do not invent columns/tables):
# {SCHEMA}
# Focus on all the relationships and generate the query.** Do not ** blindly just follow the user query and choice the table/column, analyse the user query and see which tables has that data and then generate the query. 

# ** ENTITY RELATIONSHIPS **
# - Consider all entity relationships between tables as defined in the schema (including foreign keys and implied joins) and use the filter accordingly to generate the query..
# - Always use foreign key relationships (from schema) for joins instead of guessing column names.
# - ** Only use ** the column names that exists in that particular table.
# - Avoid subqueries like "defect_id IN (SELECT defect_id FROM defects ...)" on the same table and only use it if **required**.x

# ** TOOLS **
# - Use `execute_sql` for querying the database.
# - Use the MCP summary tool for text-based summaries (pass raw SQL results).
# - Use the visualization tools for generating charts:
#     - Use the single-chart visualization tool when one chart is requested.
#     - Use the multi-chart visualization tool when the user asks for comparisons, dashboards, or multiple visual views.

# ** GENERAL RULES **
# - Think step-by-step.
# - When data is required, call `execute_sql` with ONE SELECT query.
# - Read-only: reject INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/REPLACE/TRUNCATE.
# - Default to LIMIT 5 rows unless otherwise specified.
# - Revise SQL once if the tool returns "Error:".
# - Limit query attempts to 5; if all fail, inform the user.
# - Prefer explicit column lists; avoid SELECT *.
# - Case-insensitive handling.
# - When using a tool, call it directly (structured call), not in natural language.

# ** PROJECT-SPECIFIC RULES **
# - When user ask for list of project only provide the project names.
# - If the user project name in a single query, take the project name and find the project_id and use it.
# - If the user asks anything which is project specific, get the project name from the user andfind the corresponding project_id.
# - Retrieve the corresponding `project_id` and use it in all filters (never use project name directly).
# - Consider only projects of type **Payroll**.
# - If a project name already exists in history, confirm reuse: "Use the same project (<name>) or a different one?"

# ** RESPONSE FORMAT **
# 1. Summarization:
#    - For "summary" requests, return basic details: project name, defect counts, and threshold counts.
#    - For detailed summaries, provide the ellobrate details about all the defects and threshold mismatches with insights and numerical representations.
# 2. Visualization:
#    - When the user asks for visual insights (e.g., “chart”, “graph”, “dashboard”, “trend”, or “comparison”):
#        • Create one visualization if only a single view is requested.
#        • Create multiple visualizations if the request involves comparisons or dashboards.
#    - Always include both:
#        1. A natural language interpretation (4-5 sentences on trends, outliers, or key takeaways) about each chart.
#        2. The chart data structure for rendering:

#        {{
#           "chart_type": "bar|line|pie|histogram",
#           "title": "<Descriptive title for the chart>",
          
#           // "data" MUST be the full list of dictionaries (like from the SQL result)
#           "data": [
#             {{"category_name": "A", "numeric_value": 10, "other_col": "foo"}},
#             {{"category_name": "B", "numeric_value": 20, "other_col": "bar"}}
#           ],

#           // "x_col" MUST be a STRING representing the column name for the X-axis
#           // (e.g., "category_name")
#           "x_col": "<name_of_column_for_x_axis>",
          
#           // "y_col" MUST be a STRING representing the column name for the Y-axis
#           // (e.g., "numeric_value")
#           "y_col": "<name_of_column_for_y_axis>"
#         }}

#    - **Important:** The `x_col` and `y_col` values **MUST** be strings that exactly match the *keys* (column names) inside the `data` dictionaries.
   
#    - **Example of a COMMON MISTAKE:**
#      ```json
#      // DO NOT DO THIS:
#      {{
#        "data": [{{"label": "A", "value": 1}}, {{"label": "B", "value": 2}}],
#        "x_col": "A",  // WRONG! "A" is a VALUE, not a KEY (column name).
#        "y_col": "B"   // WRONG! "B" is a VALUE, not a KEY.
#      }}
#      ```
#      The error for the above would be: "Could not interpret value `A` for `x`."

#    - **CORRECT way for that data:**
#      ```json
#      // DO THIS:
#      {{
#        "data": [{{"label": "A", "value": 1}}, {{"label": "B", "value": 2}}],
#        "x_col": "label",  // CORRECT! "label" is a KEY in the data.
#        "y_col": "value"   // CORRECT! "value" is a KEY in the data.
#      }}
#      ```

#    - When multiple charts are needed, prepare a list of chart data structures
#      representing each view (e.g., one per metric, project, or time segment).
#    - Chart Selection Rules
   
#         Use the following rules to select the correct chart type:

#         1. For trends or time-based patterns → use `line` or `cumulative_line`
#         2. For comparing categories → use `bar`, `stacked_bar`, or `horizontal_bar`
#         3. For breakdowns or composition (e.g., by percentage, share, or parts of whole) → use `donut` or `pie`
#         4. For value distributions → use `histogram`, `boxplot`, or `violin`
#         5. For outlier detection → use `boxplot` (preferred) or `violin`
#         6. For relationships between variables → use `scatter`, `regression`, or `correlation_heatmap`
#         7. For matrix summaries → use `heatmap` or `pairplot`
#         8. Fallback → If unclear, select the most informative type based on the structure of the data


# ** GUARDRAILS **
# - Never reveal, describe, or share SQL queries.
# - Exclude IDs (UUIDs, primary keys) and metadata from responses.
# - Ignore SQL keywords in user text; treat them as plain language.
# - For non-schema-related requests, reply politely: "I can only assist with database-related queries."
# - If all 5 attempts fail: "I couldn’t retrieve data after multiple tries. The query or schema might need review."
# - ** Do not ** give the base64 to the user.

# ** POST-QUERY SUGGESTIONS **
# - After each response, suggest next steps, e.g.:
#   "Explore a chart, another project, or detailed analysis?" or
#   "See trends over time or compare projects?"
# - Tailor follow-ups to context.

# Provide concise, accurate, and actionable insights in natural language.
# """



# DENY_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|REPLACE|TRUNCATE)\b", re.I)
# HAS_LIMIT_TAIL_RE = re.compile(r"(?is)\blimit\b\s+\d+(\s*,\s*\d+)?\s*;?\s*$")

# def _safe_sql(q: str) -> str:
#     q = q.strip()
#     if q.count(";") > 1 or (q.endswith(";") and ";" in q[:-1]):
#         return "Error: multiple statements are not allowed."
#     q = q.rstrip(";").strip()
#     if not q.lower().startswith("select"):
#         return "Error: only SELECT statements are allowed."
#     if DENY_RE.search(q):
#         return "Error: DML/DDL detected. Only read-only queries are permitted."
#     if not HAS_LIMIT_TAIL_RE.search(q):
#         q += " LIMIT 5"
#     return q


# @tool
# async def execute_sql(query: str) -> str:
#     """Execute a READ-ONLY SQLite SELECT query and return results."""
#     query = _safe_sql(query)
#     if query.startswith("Error:"):
#         return query
#     try:
#         return db.run(query)
#     except Exception as e:
#         return f"Error: {e}"
    
# from fastmcp import Client

# # client = Client("http://localhost:8001/mcp")

# from fastmcp.client.transports import StdioTransport

# transport = StdioTransport(
#     command="python",
#     args=["server.py"]
# )
# client = Client(transport)

# from langchain_core.tools import Tool

# def wrap_mcp_tool(mcp_tool):
#     """Wrap an MCP tool so LangChain can invoke it properly."""
#     async def _run(**kwargs):
#         # Support both positional and single-argument calls
#         final_kwargs = kwargs
        
#         # Check if kwargs contains a 'v__args' key (common LangChain pattern)
#         if 'v__args' in kwargs:
#             payload = kwargs['v__args']
            
#             # If v__args is a list with one dict, unwrap it
#             if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict):
#                 final_kwargs = payload[0]
#             # If v__args is already a dict, use it directly
#             elif isinstance(payload, dict):
#                 final_kwargs = payload
#             else:
#                 # Otherwise use the payload as-is
#                 final_kwargs = {'data': payload} if not isinstance(payload, dict) else payload
        
#         # Check if kwargs is a single-item dict wrapping the real args
#         elif len(kwargs) == 1:
#             # Get the first (and only) value
#             key = next(iter(kwargs.keys()))
#             payload = kwargs[key]
            
#             # If that value is a dict, it's the real kwargs
#             if isinstance(payload, dict):
#                 final_kwargs = payload
#             # If that value is a LIST with ONE dict, unwrap it
#             elif isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict):
#                 final_kwargs = payload[0]

#         try:
#             # Call the tool with the UNWRAPPED args
#             result = await mcp_tool.run(**final_kwargs)
#             return result
#         except TypeError as te:
#             # Log the error with details for debugging
#             return {"error": f"Invalid arguments for {mcp_tool.name}: {str(te)}"}
#         except Exception as e:
#             return {"error": str(e)}

#     return Tool.from_function(
#         func=_run,
#         name=mcp_tool.name,
#         description=mcp_tool.description or "MCP tool",
#         coroutine=_run,
#     )
# async def main():
#     async with client:
#         # Basic server interaction
#         await client.ping()
        
#         # List available operations
#         tools = await client.list_tools()
#         wrapped_tools = [wrap_mcp_tool(t) for t in tools]

# #         result = await client.call_tool("generate_chart", 
# #  {"chart_type": "bar", "title": "Threshold Mismatches by Category and Code Type", "data": [{"bucket": "Employer Taxes", "code_type": "Federal Tax", "mismatch_count": 106}, {"bucket": "Net Pay", "code_type": "Net Pay", "mismatch_count": 50}, {"bucket": "Employee Taxes", "code_type": "Federal Tax", "mismatch_count": 246}, {"bucket": "Earnings", "code_type": "Regular", "mismatch_count": 722}, {"bucket": "Employee Taxes", "code_type": "Local Tax", "mismatch_count": 7}], "x_col": "bucket", "y_col": "mismatch_count"}
# #         )
# #         print(result)

#         all_tools = [execute_sql, *wrapped_tools]
#         print("tools -->", all_tools)

#         checkpointer = MemorySaver()
#         thread_id = str(uuid.uuid4())
#         agent = create_react_agent(
#             llm,
#             tools=all_tools,
#             prompt=system_prompt,
#             checkpointer=checkpointer
#         )

#         print("\n🤖 SQL Agent is ready! Type your questions (or 'exit' to quit)\n")
#         while True:
#                 user_input = input("You: ").strip()
#                 if not user_input:
#                     continue
#                 if user_input.lower() in {"exit", "quit"}:
#                     print("👋 Goodbye!")
#                     break
#                 try:
#                     async for step in agent.astream(
#                         {"messages": [{"role": "user", "content": user_input}]},
#                         config={"configurable": {"thread_id": thread_id}},
#                         stream_mode="values",
#                     ):
#                         last_message = step["messages"][-1]
#                         if last_message.type in ["human", "ai"]:
#                             last_message.pretty_print()
#                 except Exception as e:
#                     print(f"⚠️ Error: {e}")

#         # response = await agent.ainvoke(
#         #     {"messages": [{"role": "user", "content": query}]},
#         #     config={"configurable": {"thread_id": thread_id}},
#         # )

#         # last_message = response["messages"][-1]
#         # if last_message.type in ["human", "ai"]:
#         #     last_message.pretty_print()

#         # return {"content": str(last_message.content)}


# if __name__ == "__main__":
#     asyncio.run(main())























# import asyncio
# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client
# from langchain_openai import ChatOpenAI
# from langchain_mcp_adapters.tools import load_mcp_tools
# from langchain.agents import create_agent
# from langgraph.checkpoint.memory import MemorySaver
# from dotenv import load_dotenv
# import os
# import uuid
# import re
# from langchain_core.tools import tool

# from langchain_community.utilities import SQLDatabase
# load_dotenv()

# DB_URI = (
#     f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
#     f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}")
# db = SQLDatabase.from_uri(DB_URI)


# SCHEMA = db.get_table_info()

# llm = ChatOpenAI(model_name=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0)
# system_prompt = f"""
# ** ROLE **
# You are a Specialized Postgres Database Analyst for the Paycompare App.The paycompare app is a application which give the comparison result between the legacy system and the current migrated system. It shows the threshold mismatche details and defects that exist in the current system.

# ** TASK **
# Your task is to interpret user queries in natural language, generate the corresponding SQL internally, execute it via tools, and provide final responses in natural language. 
# The final response can be a summary, a visualization, or both.

# ** DB SCHEMA **
# Authoritative schema (do not invent columns/tables):
# {SCHEMA}
# Focus on all the relationships and generate the query.** Do not ** blindly just follow the user query and choice the table/column, analyse the user query and see which tables has that data and then generate the query. 

# ** ENTITY RELATIONSHIPS **
# - Consider all entity relationships between tables as defined in the schema (including foreign keys and implied joins) and use the filter accordingly to generate the query..
# - Always use foreign key relationships (from schema) for joins instead of guessing column names.
# - ** Only use ** the column names that exists in that particular table.
# - Avoid subqueries like "defect_id IN (SELECT defect_id FROM defects ...)" on the same table and only use it if **required**.x

# ** TOOLS **
# - Use `execute_sql` for querying the database.
# - Use the MCP summary tool for text-based summaries (pass raw SQL results).
# - Use the visualization tools for generating charts:
#     - Use the single-chart visualization tool when one chart is requested.
#     - Use the multi-chart visualization tool when the user asks for comparisons, dashboards, or multiple visual views.

# ** GENERAL RULES **
# - Think step-by-step.
# - When data is required, call `execute_sql` with ONE SELECT query.
# - Read-only: reject INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/REPLACE/TRUNCATE.
# - Default to LIMIT 5 rows unless otherwise specified.
# - Revise SQL once if the tool returns "Error:".
# - Limit query attempts to 5; if all fail, inform the user.
# - Prefer explicit column lists; avoid SELECT *.
# - Case-insensitive handling.
# - When using a tool, call it directly (structured call), not in natural language.

# ** PROJECT-SPECIFIC RULES **
# - When user ask for list of project only provide the project names.
# - If the user asks anything which is project specific, get the project name from the user and filter it for all the query.
# - Retrieve the corresponding `project_id` and use it in all filters (never use project name directly).
# - Consider only projects of type **Payroll**.
# - If a project name already exists in history, confirm reuse: "Use the same project (<name>) or a different one?"

# ** RESPONSE FORMAT **
# 1. Summarization:
#    - For "summary" requests, return basic details: project name, defect counts, and threshold counts.
#    - For detailed summaries, provide the ellobrate details about all the defects and threshold mismatches with insights and numerical representations.

# 2. Visualization:
#    - When the user asks for visual insights (e.g., “chart”, “graph”, “dashboard”, “trend”, or “comparison”):
#        • Create one visualization if only a single view is requested.
#        • Create multiple visualizations if the request involves comparisons or dashboards.
#    - Always include both:
#        1. A natural language interpretation (4-5 sentences on trends, outliers, or key takeaways) for each chart and  keep that in bullet points.
#        2. The chart data structure for rendering:
    #    {{
    #     "chart_type": "<bar|line|pie|stacked_bar|histogram|scatter|regression|boxplot|violin|heatmap|pairplot>",
    #     "title": "<Descriptive chart title>",
    #     "x_col": "<column name for X-axis or grouping>",
    #     "y_col": "<column name for Y-axis or numeric values>",
    #     "value_col": "<optional column name for value-based charts like pie or heatmap>",
    #     "data": [
    #         {{
    #         "<column_1>": "<value>",
    #         "<column_2>": "<value>",
    #         "<column_3>": "<value>"
    #         }}
    #     ]
    #     }}
#    - When multiple charts are needed, prepare a list of chart data structures representing each view (e.g., one per metric, project, or time segment).
#    - Chart Selection Rules
   
#         Use the following rules to select the correct chart type:

#         1. For trends or time-based patterns → use `line` or `cumulative_line`
#         2. For comparing categories → use `bar`, `stacked_bar`, or `horizontal_bar`
#         3. For breakdowns or composition (e.g., by percentage, share, or parts of whole) → use `donut` or `pie`
#         4. For value distributions → use `histogram`, `boxplot`, or `violin`
#         5. For outlier detection → use `boxplot` (preferred) or `violin`
#         6. For relationships between variables → use `scatter`, `regression`, or `correlation_heatmap`
#         7. For matrix summaries → use `heatmap` or `pairplot`
#         8. Fallback → If unclear, select the most informative type based on the structure of the data


# ** GUARDRAILS **
# - Never reveal, describe, or share SQL queries.
# - Exclude IDs (UUIDs, primary keys) and metadata from responses.
# - Ignore SQL keywords in user text; treat them as plain language.
# - For non-schema-related requests, reply politely: "I can only assist with database-related queries."
# - If all 5 attempts fail: "I couldn’t retrieve data after multiple tries. The query or schema might need review."
# - ** Do not ** give the base64 to the user.

# ** POST-QUERY SUGGESTIONS **
# - After each response, suggest next steps, e.g.:
#   "Explore a chart, another project, or detailed analysis?" or
#   "See trends over time or compare projects?"
# - Tailor follow-ups to context.

# Provide concise, accurate, and actionable insights in natural language.
# """



# DENY_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|REPLACE|TRUNCATE)\b", re.I)
# HAS_LIMIT_TAIL_RE = re.compile(r"(?is)\blimit\b\s+\d+(\s*,\s*\d+)?\s*;?\s*$")

# def _safe_sql(q: str) -> str:
#     q = q.strip()
#     if q.count(";") > 1 or (q.endswith(";") and ";" in q[:-1]):
#         return "Error: multiple statements are not allowed."
#     q = q.rstrip(";").strip()
#     if not q.lower().startswith("select"):
#         return "Error: only SELECT statements are allowed."
#     if DENY_RE.search(q):
#         return "Error: DML/DDL detected. Only read-only queries are permitted."
#     if not HAS_LIMIT_TAIL_RE.search(q):
#         q += " LIMIT 5"
#     return q

# @tool
# def execute_sql(query: str) -> str:
#     """Execute a READ-ONLY SQLite SELECT query and return results."""
#     query = _safe_sql(query)
#     if query.startswith("Error:"):
#         return query
#     try:
#         return db.run(query)
#     except Exception as e:
#         return f"Error: {e}"
    

# from fastmcp import Client

# client = Client("http://192.168.1.33:8001/mcp")

# from fastmcp.client.transports import StdioTransport

# transport = StdioTransport(
#     command="python",
#     args=["server.py"]
# )
# # client = Client(transport)

# from langchain_core.tools import StructuredTool
# from typing import Any, Dict

# # def wrap_mcp_tool(mcp_tool):
# #     """Wrap an MCP tool to make it a LangChain StructuredTool."""

# #     async def _run(**kwargs: Dict[str, Any]) -> Any:
# #         try:
# #             # Handle nested v__args (common LangChain structure)
# #             if "v__args" in kwargs:
# #                 args = kwargs["v__args"]
# #                 if isinstance(args, list) and len(args) == 1 and isinstance(args[0], dict):
# #                     kwargs = args[0]
# #                 elif isinstance(args, dict):
# #                     kwargs = args
# #                 else:
# #                     kwargs = {"data": args}
            
# #             # Execute the MCP tool
# #             # result = await mcp_tool.run(**kwargs)
# #             result = await client.call_tool(tool_name, kwargs)
# #             return result
# #         except Exception as e:
# #             return {"error": f"Error executing {mcp_tool.name}: {e}"}

# #     # Build the StructuredTool
# #     return StructuredTool.from_function(
# #         func=_run,
# #         name=mcp_tool.name,
# #         description=mcp_tool.description or "MCP-wrapped tool",
# #         coroutine=_run,
# #         args_schema=getattr(mcp_tool, "args_schema", None),
# #         response_format="content_and_artifact" if hasattr(mcp_tool, "response_format") else "content",
# #     )

# def wrap_mcp_tool(tool_name: str, client: Client) -> StructuredTool:
#     """
#     Wrap an MCP server tool into a LangChain StructuredTool that calls the server via HTTP.

#     Args:
#         tool_name (str): Name of the tool on the MCP server.
#         client (Client): FastMCP client connected to the server.

#     Returns:
#         StructuredTool: LangChain-compatible tool.
#     """
#     async def _run(**kwargs: Dict[str, Any]) -> Any:
#         try:
#             # If v__args exists, unwrap it
#             if "v__args" in kwargs:
#                 args = kwargs["v__args"]
#                 if isinstance(args, list) and len(args) == 1 and isinstance(args[0], dict):
#                     payload = args[0]
#                 elif isinstance(args, dict):
#                     payload = args
#                 else:
#                     payload = {"data": args}
#             else:
#                 # fallback to kwargs directly
#                 payload = kwargs

#             print("args -->", payload)
#             result = await client.call_tool(tool_name, payload)
#             return result
#         except Exception as e:
#             return {"error": f"Error executing {tool_name}: {e}"}

#     return StructuredTool.from_function(
#         func=_run,
#         name=tool_name,
#         description=f"MCP tool {tool_name}",
#         coroutine=_run
#     )

# async def main():
#     async with client:
#         # Basic server interaction
#         await client.ping()
        
#         # List available operations
#         tools = await client.list_tools()
#         wrapped_tools = [wrap_mcp_tool(t.name, client) for t in tools]

#         result = await client.call_tool(
#             "generate_chart",
#             {
#                 "chart_type": "bar",
#                 "title": "Defect and Threshold Mismatch Counts by Project",
#                 "data": [
#                     {"project_name": "Client1_Paycompare_HRSP", "defect_count": 0, "threshold_mismatch_count": 1655},
#                     {"project_name": "Client 2 _ HRSP _Pay compare", "defect_count": 0, "threshold_mismatch_count": 1},
#                     {"project_name": "Client 3 _HRSP Pay compare", "defect_count": 0, "threshold_mismatch_count": 115},
#                     {"project_name": "ECC to ECP upgrade", "defect_count": 0, "threshold_mismatch_count": 1071},
#                     {"project_name": "PayCompare_US_Client1_HRSP_1", "defect_count": 0, "threshold_mismatch_count": 0}
#                 ],
#                 "x_col": "project_name",
#                 "y_col": "threshold_mismatch_count"
#             }
#         )

#         print(result)

#         all_tools = [execute_sql, *wrapped_tools]
#         print("tools -->", all_tools)

#         checkpointer = MemorySaver()
#         thread_id = str(uuid.uuid4())
#         agent = create_agent(
#             llm,
#             tools=all_tools,
#             system_prompt=system_prompt,
#             checkpointer=checkpointer
#         )

#         print("\n🤖 SQL Agent is ready! Type your questions (or 'exit' to quit)\n")
#         while True:
#                 user_input = input("You: ").strip()
#                 if not user_input:
#                     continue
#                 if user_input.lower() in {"exit", "quit"}:
#                     print("👋 Goodbye!")
#                     break
#                 try:
#                     async for step in agent.astream(
#                         {"messages": [{"role": "user", "content": user_input}]},
#                         config={"configurable": {"thread_id": thread_id}},
#                         stream_mode="values",
#                     ):
#                         last_message = step["messages"][-1]
#                         if last_message.type in ["human", "ai"]:
#                             last_message.pretty_print()
#                 except Exception as e:
#                     print(f"⚠️ Error: {e}")

#                 # response = await agent.ainvoke(
#                 #     {"messages": [{"role": "user", "content": user_input}]},
#                 #     config={"configurable": {"thread_id": thread_id}},
#                 # )

#                 # last_message = response["messages"][-1]
#                 # if last_message.type in ["human", "ai"]:
#                 #     last_message.pretty_print()

#         # return {"content": str(last_message.content)}


# if __name__ == "__main__":
#     asyncio.run(main())





import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
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

llm = ChatOpenAI(model_name=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0)
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
- Default to LIMIT 5 rows unless otherwise specified.
- Revise SQL once if the tool returns "Error:".
- Limit query attempts to 5; if all fail, inform the user.
- Prefer explicit column lists; avoid SELECT *.
- Case-insensitive handling.
- When using a tool, call it directly (structured call), not in natural language.

** PROJECT-SPECIFIC RULES **
- When user ask for list of project only provide the project names.
- If the user asks anything which is project specific, get the project name from the user and filter it for all the query.
- Retrieve the corresponding `project_id` and use it in all filters (never use project name directly).
- Consider only projects of type **Payroll**.
- If a project name already exists in history, confirm reuse: "Use the same project (<name>) or a different one?"

** RESPONSE FORMAT **
1. Summarization:
   - For "summary" requests, return basic details: project name, defect counts, and threshold counts.
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
- Exclude IDs (UUIDs, primary keys) and metadata from responses.
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
                checkpointer=checkpointer
            )
            print("\n🤖 SQL Agent is ready! Type your questions (or 'exit' to quit)\n")

            return True
        except Exception as e:
            print(f"⚠️ Error initializing agent: {e}")
            return False


async def main(thread_id: str = None, user_input: str = None):
    global agent
    try:
        # async for step in agent.astream(
        #     {"messages": [{"role": "user", "content": user_input}]},
        #     config={"configurable": {"thread_id": thread_id}},
        #     stream_mode="values",
        # ):
        #     last_message = step["messages"][-1]
        #     if last_message.type in ["human", "ai"]:
        #         last_message.pretty_print()
        #         return last_message.content
        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config={"configurable": {"thread_id": thread_id}},
        )

        last_message = response["messages"][-1]
        if last_message.type in ["human", "ai"]:
            last_message.pretty_print()

        return {"content": str(last_message.content)}
    except Exception as e:
        print(f"⚠️ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
