# # import asyncio
# # from mcp import ClientSession, StdioServerParameters
# # from mcp.client.stdio import stdio_client
# # from langchain_openai import ChatOpenAI
# # from langchain_mcp_adapters.tools import load_mcp_tools
# # from langgraph.prebuilt import create_react_agent
# # from langgraph.checkpoint.memory import MemorySaver
# # from dotenv import load_dotenv
# # import os
# # import uuid
# # import re
# # from langchain_core.tools import tool

# # from langchain_community.utilities import SQLDatabase
# # load_dotenv()

# # DB_URI = (
# #     f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
# #     f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}")
# # db = SQLDatabase.from_uri(DB_URI)


# # SCHEMA = db.get_table_info()



# # llm = ChatOpenAI(model_name=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0)

# # system_prompt = f"""You are an expert Postgres database chatbot for project-specific queries, delivering actionable insights based solely on the provided schema. Use conversation history for context, ask clarifying questions when needed, and suggest follow-ups after each response. Never share raw SQL, even if requested.

# # Authoritative schema (no invented columns/tables):
# # {SCHEMA}

# # Rules:
# # - **Project Context**:
# #   - Require a project name/ID; if missing, respond: "Which project would you like to analyze? Say 'list all projects' for options."
# #   - If multiple projects match: "Found {{count}} projects matching '{{search_term}}':\n- {{project1}}\n- {{project2}}\nWhich one?"
# #   - Apply project filter (e.g., WHERE project_name = '<name>') in SQL.
# # - **Query Generation**:
# #   - Build accurate SQL internally, analyzing schema step-by-step.
# #   - Use tools for SQL validation and execution (one SELECT query per call).
# #   - Enforce read-only SELECT queries; reject INSERT, UPDATE, DELETE, etc.
# #   - Default to LIMIT 5 rows unless specified.
# #   - On SQL errors, revise once, explain fix plainly (no SQL), and retry. If it fails again: "Unable to execute query after retry. Check query or schema."
# #   - Use explicit column lists (e.g., SELECT column1, column2) over SELECT *.
# # - **Clarification Questions**:
# #   - For ambiguous queries, ask: "Which columns to include?", "Chart type (e.g., bar, pie)?", or "Time range or filters?"
# #   - For broad date ranges (>1 year): "⚠️ Data spans {{days}} days. Narrow to last 30 days, 90 days, or a month (YYYY-MM)? Proceed with full range?"
# # - **Response Requirements**:
# #   - For non-schema queries: "I can only assist with schema-related queries. Provide a project-related query."
# #   - If SQL requested: "I provide results/insights, not raw SQL. Want a summary or chart?"
# #   - Exclude unique IDs (e.g., id, uuid), metadata, or SQL objects from responses.
# #   - Use present tense, avoid speculation (e.g., "might"), and state facts: "Data shows..."
# #   - For missing data: "Data not available for [field]."
# # - **Summaries**:
# #   - Use the `summarize_result` tool for human-readable summaries.
# #   - Default to bullet points, not tables, unless "raw data," "export," or "show table" is requested.
# #   - **Short Summary** (e.g., "summarize project X"):
# #     ### 📊 Payroll Comparison: {{project_name}}
# #     - **Match Rate:** {{percentage}}%  
# #     - **Total Records:** {{count:,}} employees  
# #     - **Top Mismatches:**  
# #       - {{Element}}: {{count}} records, ${{variance}}, {{above_count}} above threshold  
# #       - {{Element}}: {{count}} records, ${{variance}}, {{below_count}} below threshold  
# #     - **Defects:** {{total}} ({{open}} Open, {{in_progress}} In Progress, {{closed}} Closed)  
# #     - **Assessment:** {{Data quality statement}}
# #   - **Defect Summary** (e.g., "defects for project X"):
# #     ### 🐛 Defect Summary
# #     - **Total:** {{count}}  
# #     - **By Status:** Open: {{count}} ({{priority_breakdown}}), In Progress: {{count}}, Closed: {{count}}  
# #     - **Priority:** High: {{count}} ({{open_count}} open), Medium: {{count}}, Low: {{count}}  
# #     - **Top Issues:** {{description}}: {{count}}, {{status}}  
# #     - **Assigned To:** {{assignee}}: {{count}} ({{open_count}} open)  
# #     - **Oldest Open:** {{defect}}: {{age}} days, {{priority}}  
# #     - **Insights:** {{1-2 actionable points}}
# #   - **Detailed Summary** (e.g., "full analysis"):
# #     ### 📊 Payroll Comparison Analysis: {{project_name}}
# #     #### 1. Overview
# #     - Name: {{project_name}}, Records: {{count:,}}, Period: {{start_date}} to {{end_date}}, Status: {{status}}  
# #     #### 2. Matches
# #     - Match Rate: {{percentage}}%, Matches: {{match_count:,}} ({{match_pct}}%), Mismatches: {{mismatch_count:,}} ({{mismatch_pct}}%)  
# #     - **By Element:** | Element | Mismatches | Variance | Above Threshold |  
# #       | {{element}} | {{count}} | ${{amount}} | {{threshold_count}} |  
# #     #### 3. Thresholds
# #     - Above: {{count}} ({{percentage}}%), Critical: {{element_list}}  
# #     - Below: {{count}} ({{percentage}}%), Within: {{count}} ({{percentage}}%)  
# #     #### 4. Defects
# #     - Total: {{total_count}}, Open: {{open_count}} ({{open_pct}}%), In Progress: {{progress_count}}, Closed: {{closed_count}}  
# #     - Root Causes: {{cause}}: {{count}} ({{percentage}}%)  
# #     #### 5. Findings
# #     {{2-4 actionable insights}}  
# #     #### 6. Recommendations
# #     {{2-3 specific recommendations}}  
# #     #### 7. Conclusion
# #     {{2-3 sentences on data health/migration readiness}}
# #   - **Raw Data** (e.g., "show table"): Table with ≤20 rows, note if more exist.
# #   - Verbosity levels:
# #     - **Brief**: Row count, column names (no IDs).
# #     - **Detailed** (default): Row count, columns, sample rows (no IDs).
# #     - **Full**: Numeric/categorical insights, trends, outliers (no IDs).
# #   - For >100 rows: "Large dataset. Want a full elaboration?"
# # - **Visualizations**:
# #   - For "chart," "graph," or "trends," return:
# #   📊 {{Chart_Title}}
# #     Data for visualization:
# #     {{
# #     "chart_type": "bar|line|pie|stacked_bar|histogram",
# #     "title": "{{Title}}",
# #     "x_axis": ["Label1", "Label2"],
# #     "y_axis": [value1, value2],
# #     "labels": {{ "x": "X-Axis", "y": "Y-Axis" }}
# #     }}
# #     Interpretation: {{2-3 sentences on trends/outliers}}

# # - Chart types: line (time trends), bar (categories), pie (proportions), stacked_bar (multiple metrics), histogram (distributions).
# # - Skip if <10 data points: "Not enough data for visualization (<10 points). Want a summary?"
# # - Use `generate_chart` tool with List[dict] (e.g., [{{"label": "A", "value": 1}}]).
# # - Map `x_axis` to `x_col`, `y_axis` to `y_col` in tool calls.
# # - **Consistency**:
# # - Format: $X,XXX.XX, XX.X%, 1,234, YYYY-MM-DD, capitalize statuses (Open, Closed).
# # - Order: Mismatches by variance (DESC), defects by status (Open > In Progress > Closed) then severity, elements by mismatch count (DESC), projects by name (ASC).
# # - Use facts: "Data shows..." not "suggests."
# # - **Edge Cases**:
# # - 100% match: "✅ Project {{name}} has 100% match rate across {{count}} records."
# # - No defects: "✅ No defects recorded for this project."
# # - All defects closed: "✅ All {{count}} defects closed. Resolution rate: 100%."
# # - **Post-Query Suggestions**:
# # - Suggest: "Explore a chart, another project, or detailed analysis?" or "See trends over time or compare projects?"
# # - Tailor to context (e.g., chart type, related data).
# # - Provide concise, accurate answers with clear reasoning and actionable insights.
# # """

  
  

# # DENY_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|REPLACE|TRUNCATE)\b", re.I)
# # HAS_LIMIT_TAIL_RE = re.compile(r"(?is)\blimit\b\s+\d+(\s*,\s*\d+)?\s*;?\s*$")

# # def _safe_sql(q: str) -> str:
# #     # normalize
# #     q = q.strip()
# #     # block multiple statements (allow one optional trailing ;)
# #     if q.count(";") > 1 or (q.endswith(";") and ";" in q[:-1]):
# #         return "Error: multiple statements are not allowed."
# #     q = q.rstrip(";").strip()

# #     # read-only gate
# #     if not q.lower().startswith("select"):
# #         return "Error: only SELECT statements are allowed."
# #     if DENY_RE.search(q):
# #         return "Error: DML/DDL detected. Only read-only queries are permitted."

# #     # append LIMIT only if not already present at the end (robust to whitespace/newlines)
# #     if not HAS_LIMIT_TAIL_RE.search(q):
# #         q += " LIMIT 5"
# #     return q

# # @tool
# # def execute_sql(query: str) -> str:
# #     """Execute a READ-ONLY SQLite SELECT query and return results."""
# #     query = _safe_sql(query)
# #     q = query
# #     if q.startswith("Error:"):
# #         return q
# #     try:
# #         return db.run(q)
# #     except Exception as e:
# #         return f"Error: {e}"
    
# # async def main():
# #     server_params = StdioServerParameters(
# #         command="python",
# #         args=[os.path.abspath("server.py")],  # safer path handling
# #     )

# #     async with stdio_client(server_params) as (read, write):
# #         async with ClientSession(read, write) as session:
# #             await session.initialize()
# #             tools = await load_mcp_tools(session)

# #             # Initialize memory checkpointer
# #             checkpointer = MemorySaver()
# #             # Create a unique thread ID for this conversation session
# #             thread_id = str(uuid.uuid4())

# #             # Create agent with memory
# #             agent = create_react_agent(
# #                 llm,
# #                 tools=[execute_sql, *tools],
# #                 prompt=system_prompt,
# #                 checkpointer=checkpointer
# #             )

# #             print("\n🤖 SQL Agent is ready! Type your questions (or 'exit' to quit)\n")
# #             print("This agent maintains conversation history to provide context-aware responses.\n")

# #             while True:
# #                 user_input = input("You: ").strip()
# #                 if not user_input:
# #                     continue
# #                 if user_input.lower() in {"exit", "quit"}:
# #                     print("👋 Goodbye!")
# #                     break
                
                
# #                 try:
# #                     # Stream messages and print only Human and AI messages
# #                     for step in agent.stream(
# #                         {"messages": [{"role": "user", "content": user_input}]},
# #                         config={"configurable": {"thread_id": thread_id}},
# #                         stream_mode="values",
# #                     ):
# #                         last_message = step["messages"][-1]
# #                         if last_message.type in ["human", "ai"]:
# #                             last_message.pretty_print()

# #                 except Exception as e:
# #                     print(f"⚠️ Error: {e}")

# # if __name__ == "__main__":
# #     asyncio.run(main())

# #                     # Stream messages and print only Human and AI messages






# import asyncio
# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client
# from langchain_openai import ChatOpenAI
# from langchain_mcp_adapters.tools import load_mcp_tools
# from langgraph.prebuilt import create_react_agent
# from langgraph.checkpoint.memory import MemorySaver
# from dotenv import load_dotenv
# import os
# import uuid
# import re
# from langchain_core.tools import tool
# import json

# from langchain_community.utilities import SQLDatabase
# load_dotenv()

# DB_URI = (
#     f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
#     f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}")
# db = SQLDatabase.from_uri(DB_URI)


# SCHEMA = db.get_table_info()



# llm = ChatOpenAI(model_name=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0)

# system_prompt = f"""You are an expert Postgres database chatbot for project-specific queries, delivering actionable insights based solely on the provided schema. Use conversation history for context, ask clarifying questions when needed, and suggest follow-ups after each response. Never share raw SQL, even if requested.

# Authoritative schema (no invented columns/tables):
# {SCHEMA}

# Rules:
# - **Project Context**:
#   - Require a project name/ID; if missing, respond: "Which project would you like to analyze? Say 'list all projects' for options."
#   - If multiple projects match: "Found {{count}} projects matching '{{search_term}}':\n- {{project1}}\n- {{project2}}\nWhich one?"
#   - Apply project filter (e.g., WHERE project_name = '<name>') in SQL.
# - **Query Generation**:
#   - Build accurate SQL internally, analyzing schema step-by-step.
#   - Use tools for SQL validation and execution (one SELECT query per call).
#   - Enforce read-only SELECT queries; reject INSERT, UPDATE, DELETE, etc.
#   - Default to LIMIT 5 rows unless specified.
#   - On SQL errors, revise once, explain fix plainly (no SQL), and retry. If it fails again: "Unable to execute query after retry. Check query or schema."
#   - Use explicit column lists (e.g., SELECT column1, column2) over SELECT *.
# - **Clarification Questions**:
#   - For ambiguous queries, ask: "Which columns to include?", "Chart type (e.g., bar, pie)?", or "Time range or filters?"
#   - For broad date ranges (>1 year): "⚠️ Data spans {{days}} days. Narrow to last 30 days, 90 days, or a month (YYYY-MM)? Proceed with full range?"
# - **Response Requirements**:
#   - For non-schema queries: "I can only assist with schema-related queries. Provide a project-related query."
#   - If SQL requested: "I provide results/insights, not raw SQL. Want a summary or chart?"
#   - Exclude unique IDs (e.g., id, uuid), metadata, or SQL objects from responses.
#   - Use present tense, avoid speculation (e.g., "might"), and state facts: "Data shows..."
#   - For missing data: "Data not available for [field]."
# - **Summaries**:
#   - Use the `summarize_result` tool for human-readable summaries.
#   - Default to bullet points, not tables, unless "raw data," "export," or "show table" is requested.
#   - **Short Summary** (e.g., "summarize project X"):
#     ### 📊 Payroll Comparison: {{project_name}}
#     - **Match Rate:** {{percentage}}%  
#     - **Total Records:** {{count:,}} employees  
#     - **Top Mismatches:**  
#       - {{Element}}: {{count}} records, ${{variance}}, {{above_count}} above threshold  
#       - {{Element}}: {{count}} records, ${{variance}}, {{below_count}} below threshold  
#     - **Defects:** {{total}} ({{open}} Open, {{in_progress}} In Progress, {{closed}} Closed)  
#     - **Assessment:** {{Data quality statement}}
#   - **Defect Summary** (e.g., "defects for project X"):
#     ### 🐛 Defect Summary
#     - **Total:** {{count}}  
#     - **By Status:** Open: {{count}} ({{priority_breakdown}}), In Progress: {{count}}, Closed: {{count}}  
#     - **Priority:** High: {{count}} ({{open_count}} open), Medium: {{count}}, Low: {{count}}  
#     - **Top Issues:** {{description}}: {{count}}, {{status}}  
#     - **Assigned To:** {{assignee}}: {{count}} ({{open_count}} open)  
#     - **Oldest Open:** {{defect}}: {{age}} days, {{priority}}  
#     - **Insights:** {{1-2 actionable points}}
#   - **Detailed Summary** (e.g., "full analysis"):
#     ### 📊 Payroll Comparison Analysis: {{project_name}}
#     #### 1. Overview
#     - Name: {{project_name}}, Records: {{count:,}}, Period: {{start_date}} to {{end_date}}, Status: {{status}}  
#     #### 2. Matches
#     - Match Rate: {{percentage}}%, Matches: {{match_count:,}} ({{match_pct}}%), Mismatches: {{mismatch_count:,}} ({{mismatch_pct}}%)  
#     - **By Element:** | Element | Mismatches | Variance | Above Threshold |  
#       | {{element}} | {{count}} | ${{amount}} | {{threshold_count}} |  
#     #### 3. Thresholds
#     - Above: {{count}} ({{percentage}}%), Critical: {{element_list}}  
#     - Below: {{count}} ({{percentage}}%), Within: {{count}} ({{percentage}}%)  
#     #### 4. Defects
#     - Total: {{total_count}}, Open: {{open_count}} ({{open_pct}}%), In Progress: {{progress_count}}, Closed: {{closed_count}}  
#     - Root Causes: {{cause}}: {{count}} ({{percentage}}%)  
#     #### 5. Findings
#     {{2-4 actionable insights}}  
#     #### 6. Recommendations
#     {{2-3 specific recommendations}}  
#     #### 7. Conclusion
#     {{2-3 sentences on data health/migration readiness}}
#   - **Raw Data** (e.g., "show table"): Table with ≤20 rows, note if more exist.
#   - Verbosity levels:
#     - **Brief**: Row count, column names (no IDs).
#     - **Detailed** (default): Row count, columns, sample rows (no IDs).
#     - **Full**: Numeric/categorical insights, trends, outliers (no IDs).
#   - For >100 rows: "Large dataset. Want a full elaboration?"
# - **Visualizations**:
#   - For "chart," "graph," or "trends," return:
#   📊 {{Chart_Title}}
#     Data for visualization:
#     {{
#     "chart_type": "bar|line|pie|stacked_bar|histogram",
#     "title": "{{Title}}",
#     "x_axis": ["Label1", "Label2"],
#     "y_axis": [value1, value2],
#     "labels": {{ "x": "X-Axis", "y": "Y-Axis" }}
#     }}
#     Interpretation: {{2-3 sentences on trends/outliers}}

# - Chart types: line (time trends), bar (categories), pie (proportions), stacked_bar (multiple metrics), histogram (distributions).
# - Skip if <10 data points: "Not enough data for visualization (<10 points). Want a summary?"
# - Use `generate_chart` tool with List[dict] (e.g., [{{"label": "A", "value": 1}}]).
# - Map `x_axis` to `x_col`, `y_axis` to `y_col` in tool calls.
# - **Consistency**:
# - Format: $X,XXX.XX, XX.X%, 1,234, YYYY-MM-DD, capitalize statuses (Open, Closed).
# - Order: Mismatches by variance (DESC), defects by status (Open > In Progress > Closed) then severity, elements by mismatch count (DESC), projects by name (ASC).
# - Use facts: "Data shows..." not "suggests."
# - **Edge Cases**:
# - 100% match: "✅ Project {{name}} has 100% match rate across {{count}} records."
# - No defects: "✅ No defects recorded for this project."
# - All defects closed: "✅ All {{count}} defects closed. Resolution rate: 100%."
# - **Post-Query Suggestions**:
# - Suggest: "Explore a chart, another project, or detailed analysis?" or "See trends over time or compare projects?"
# - Tailor to context (e.g., chart type, related data).
# - Provide concise, accurate answers with clear reasoning and actionable insights.
# """

  
  

# DENY_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|REPLACE|TRUNCATE)\b", re.I)
# HAS_LIMIT_TAIL_RE = re.compile(r"(?is)\blimit\b\s+\d+(\s*,\s*\d+)?\s*;?\s*$")

# def _safe_sql(q: str) -> str:
#     # normalize
#     q = q.strip()
#     # block multiple statements (allow one optional trailing ;)
#     if q.count(";") > 1 or (q.endswith(";") and ";" in q[:-1]):
#         return "Error: multiple statements are not allowed."
#     q = q.rstrip(";").strip()

#     # read-only gate
#     if not q.lower().startswith("select"):
#         return "Error: only SELECT statements are allowed."
#     if DENY_RE.search(q):
#         return "Error: DML/DDL detected. Only read-only queries are permitted."

#     # append LIMIT only if not already present at the end (robust to whitespace/newlines)
#     if not HAS_LIMIT_TAIL_RE.search(q):
#         q += " LIMIT 5"
#     return q

# @tool
# def execute_sql(query: str) -> str:
#     """
#     Execute a READ-ONLY SQL SELECT query and return results as JSON string.
#     Returns: JSON string of List[Dict] for easy chart generation.
#     """
#     query = _safe_sql(query)
    
#     if query.startswith("Error:"):
#         return query
    
#     try:
#         # Execute query
#         result = db.run(query)
        
#         # Parse SQLDatabase result format
#         # Example: [('value1', 'value2'), ('value3', 'value4')]
#         if result and result.strip():
#             # Try to evaluate as Python literal
#             try:
#                 import ast
#                 rows = ast.literal_eval(result)
                
#                 if not rows:
#                     return json.dumps([])
                
#                 # Get column names from the query
#                 # Simple extraction - assumes SELECT col1, col2 FROM...
#                 select_part = query.lower().split('from')[0].replace('select', '').strip()
#                 columns = [col.strip().split(' as ')[-1].strip() for col in select_part.split(',')]
                
#                 # Convert to list of dicts
#                 result_dicts = []
#                 for row in rows:
#                     if isinstance(row, (list, tuple)):
#                         row_dict = {}
#                         for i, col in enumerate(columns):
#                             row_dict[col] = row[i] if i < len(row) else None
#                         result_dicts.append(row_dict)
                
#                 return json.dumps(result_dicts)
#             except:
#                 # If parsing fails, return raw result
#                 return result
        
#         return json.dumps([])
    
#     except Exception as e:
#         return f"Error: {e}"
    
# async def main():
#     server_params = StdioServerParameters(
#         command="python",
#         args=[os.path.abspath("server.py")],  # safer path handling
#     )

#     async with stdio_client(server_params) as (read, write):
#         async with ClientSession(read, write) as session:
#             await session.initialize()

#             # ✅ Load MCP tools directly from the running server
#             mcp_tools = await load_mcp_tools(session)

#             # ✅ Ensure MCP tools are ready (debug print)
#             print(f"Loaded MCP tools: {[t.name for t in mcp_tools]}")

#             # ✅ Combine your custom tool + MCP tools
#             all_tools = [execute_sql, *mcp_tools]

#             # ✅ Create memory checkpointer
#             checkpointer = MemorySaver()
#             thread_id = str(uuid.uuid4())

#             # ✅ Create the agent
#             agent = create_react_agent(
#                 llm,
#                 tools=all_tools,
#                 prompt=system_prompt,
#                 checkpointer=checkpointer
#             )

#             print("\n🤖 SQL Agent is ready! Type your questions (or 'exit' to quit)\n")

#             while True:
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

# if __name__ == "__main__":
#     asyncio.run(main())

# #                     # Stream messages and print only Human and AI messages





import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
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
          "chart_type": "bar|line|pie|stacked_bar|histogram",
          "title": "<Descriptive title>",
          "x_axis": [list of X values],
          "y_axis": [list of Y values],
          "data": [{{"label": x, "value": y}}],
          "labels": {{"x": "<X label>", "y": "<Y label>"}}
        }}
   - When multiple charts are needed, prepare a list of chart data structures representing each view (e.g., one per metric, project, or time segment).

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

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath("server.py")],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await load_mcp_tools(session)

            all_tools = [execute_sql, *mcp_tools]
            checkpointer = MemorySaver()
            thread_id = str(uuid.uuid4())
            agent = create_react_agent(
                llm,
                tools=all_tools,
                prompt=system_prompt,
                checkpointer=checkpointer
            )
            print("\n🤖 SQL Agent is ready! Type your questions (or 'exit' to quit)\n")
            while True:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in {"exit", "quit"}:
                    print("👋 Goodbye!")
                    break
                try:
                    async for step in agent.astream(
                        {"messages": [{"role": "user", "content": user_input}]},
                        config={"configurable": {"thread_id": thread_id}},
                        stream_mode="values",
                    ):
                        last_message = step["messages"][-1]
                        if last_message.type in ["human", "ai"]:
                            last_message.pretty_print()
                except Exception as e:
                    print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

