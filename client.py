# import asyncio
# import os
# import uuid
# from dotenv import load_dotenv
# from mcp import StdioServerParameters, ClientSession
# from mcp.client.stdio import stdio_client

# from langchain_openai import ChatOpenAI
# from langchain_mcp_adapters.tools import load_mcp_tools
# from langgraph.prebuilt import create_react_agent
# from langgraph.checkpoint.memory import MemorySaver

# from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
# from langchain_community.agent_toolkits.sql.base import create_sql_agent
# from langchain_community.utilities import SQLDatabase

# from langchain.agents import Tool
# from langchain.prompts import PromptTemplate
# from langchain.chains import LLMChain

# # from guardrails import Guard
# # from guardrails.hub import ValidSQL,ExcludeSqlPredicates

# # ----------------- LOAD CONFIG -----------------
# load_dotenv()

# # ----------------- LLM -----------------
# llm = ChatOpenAI(model_name=os.getenv("OPENAI_MODEL", "gpt-4.1"), temperature=0)

# # ----------------- DB URI -----------------
# DB_URI = (
#     f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
#     f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
# )
       
# # ----------------- PROMPT -----------------

# system_prompt = """
# You are an **Expert Payroll Comparison Assistant** with READ-ONLY access to a secure pay comparison database.

# =================================
# 🔒 SECURITY RULES
# =================================
# - Only execute **SELECT** queries.
# - Never perform INSERT, UPDATE, DELETE, DROP, or ALTER.
# - Automatically add `LIMIT 100` to all queries.
# - Always filter data using `project_type='payroll'`.
# - Never access or expose system tables, metadata, UUIDs, or credentials.
# - Never guess schema details — ask the user for confirmation if uncertain.

# =================================
# 🎯 INTENT HANDLING
# =================================
# Classify every user request into one of:
# 1. **Greeting** → Respond briefly and warmly (no SQL).
# 2. **Pay Compare Query** → Generate and execute a safe read-only query.
# 3. **Out-of-Scope** → Reply:
#    "Hi, I can only assist with pay comparison queries. Please ask relevant pay compare related questions."

# If the request is **ambiguous or unclear**, ask for clarification before generating SQL.

# =================================
# 🧠 QUERY EXECUTION POLICY
# =================================
# - When a user asks for an **overall project summary**, combine data from **all relevant sources** automatically.
# - Filter all queries to include only `project_type='payroll'` and limit to 100 rows.
# - Never expose SQL syntax or internal structure in user responses.

# =================================
# 🔁 QUERY RETRY LOGIC (IMPORTANT)
# =================================
# If the generated SQL query:
# - Fails due to syntax or invalid assumptions, or
# - Returns zero rows,

# Then automatically:
# 1. Retry with refined query logic.
# 2. Retry up to **3 total attempts**.
# 3. If all attempts fail, stop and respond clearly:
#    "Sorry, I couldn’t retrieve valid payroll comparison data after multiple attempts. Please verify the project name or schema details."

# =================================
# 📊 SUMMARY GENERATION
# =================================
# Support two summary types:

# **Short Summary (Default)**  
# Provide concise, point-based output:
# - Match Rate (%)
# - Top Mismatches (element, count, $ difference)
# - Defect Totals and Status Split (Open, Closed, In Progress)
# - Threshold Mismatch Summary (above/below threshold)
# - One closing line on overall payroll data health

# Example:
# - Overall Match Rate: **97%**
# - Federal Tax mismatches: **14 above threshold** ($18.48)
# - Net Pay mismatches: **7 above threshold** ($28.56)
# - Total defects: **25** (12 Open, 8 Closed, 5 In Progress)
# - Threshold issues: Mostly minor
# - ✅ Payroll migration alignment is strong

# **Detailed Summary (If requested)**
# Include structured bullet-point sections:
# - Project Overview  
# - Match & Mismatch Breakdown  
# - Threshold Variance Insights  
# - Defects and Root Causes  
# - Recommendations & Key Takeaways  
# - Conclusion  

# Use factual, concise language — no narrative paragraphs.

# =================================
# 📈 VISUALIZATION HANDLING
# =================================
# If the user requests a visual, chart, or project summary:
# - Generate **only one** chart per response.
# - Choose chart type automatically:
#   * Trends or time-based → Line chart  
#   * Category comparison → Bar or Stacked Bar  
#   * Composition or breakdown → Pie or Donut  
#   * Distribution → Histogram or Boxplot  
# - Skip visualization if fewer than 10 rows returned.
# - Include:
#   - Chart caption  
#   - Base64 image data  
#   - Optional file path  
#   - 2–3 line interpretation of trends or implications.

# =================================
# ⚙️ CONSISTENCY & STABILITY
# =================================
# - Maintain identical bullet order and tone for identical queries.
# - Use temperature=0.0 for deterministic output.
# - Avoid stylistic drift or speculation.
# - If query fails → trigger retry logic (up to 3 times).
# - After 3 failures → show error message.
# - For project-level summaries, always combine data from **all relevant sources**.

# =================================
# USER REQUEST:
# {input}
# """







# # ----------------- LLM Summarization -----------------
# def llm_summarize_result(raw_result: str) -> str:
#     prompt = PromptTemplate.from_template("""
# You are a business analyst. Summarize the following SQL query result in clear, concise language for a non-technical audience.

# Result:
# {raw_result}

# Summary:
# """)
#     chain = LLMChain(llm=llm, prompt=prompt)
#     return chain.run(raw_result=raw_result).strip()


# # ----------------- MAIN -----------------
# async def main():
#     server_params = StdioServerParameters(
#         command="python",
#         args=["server.py"],  # safer path handling
#     )
#     async with stdio_client(server_params) as (read, write):
#         async with ClientSession(read, write) as session:
#             await session.initialize()
#             mcp_tools = await load_mcp_tools(session)

#             # ----------------- Memory -----------------
#             checkpointer = MemorySaver()
#             thread_id = str(uuid.uuid4())

#             # ----------------- SQL Agent -----------------
#             db = SQLDatabase.from_uri(DB_URI)
#             toolkit = SQLDatabaseToolkit(db=db, llm=llm)
#             sql_agent = create_sql_agent(llm=llm, toolkit=toolkit, verbose=False)

#             def sql_agent_tool(query: str) -> str:
#                 return sql_agent.run(query)

#             sql_tool = Tool.from_function(
#                 name="secure_sql_agent",
#                 func=sql_agent_tool,
#                 description="Safely generate and execute SQL queries from natural language using LangChain SQLAgent and Guardrails."
#             )

#             # ----------------- Hybrid summarization tool -----------------
#             async def hybrid_summarize_tool(raw_result: str, verbosity: str = "detailed") -> str:
#                 if verbosity == "brief":
#                     return await session.invoke_tool("summarize_result", {"raw_result": raw_result})
#                 else:
#                     return llm_summarize_result(raw_result)

#             summarize_tool = Tool.from_function(
#                 name="hybrid_summarize",
#                 func=hybrid_summarize_tool,
#                 description="Summarize SQL query results using either MCP tool (brief) or LLM (detailed/full)."
#             )

#             # ----------------- Combine all tools -----------------
#             all_tools = [sql_tool,summarize_tool] + mcp_tools

#             # ----------------- Agent -----------------
#             agent = create_react_agent(
#                 model=llm,
#                 tools=all_tools,
#                 prompt=system_prompt,
#                 checkpointer=checkpointer
#             )

#             print("\nSQL Agent is ready! Type your questions (or 'exit' to quit)\n")
#             print("This agent maintains conversation history to provide context-aware responses.\n")

#             while True:
#                 user_input = input("You: ").strip()
#                 if not user_input:
#                     continue
#                 if user_input.lower() in ("exit", "quit"):
#                     print("Goodbye!")
#                     break

#                 try:
#                     agent_response = await agent.ainvoke(
#                         {
#                             "messages": [{"role": "user", "content": user_input}],
#                         },
#                         config={"configurable": {"thread_id": thread_id}}
#                     )
#                     for m in agent_response.get("messages", []):
#                         m.pretty_print()

#                 except Exception as e:
#                     print(f"Error: {e}")


# if __name__ == "__main__":
#     asyncio.run(main())





import asyncio
import os
import uuid
from dotenv import load_dotenv
from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client

from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase

from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import warnings
from sqlalchemy.exc import SAWarning

warnings.filterwarnings("ignore", category=SAWarning)

# ----------------- LOAD CONFIG -----------------
load_dotenv()

# ----------------- LLM -----------------
llm = ChatOpenAI(
    model_name=os.getenv("OPENAI_MODEL", "gpt-4o"),  # gpt-4.1 doesn't exist yet
    temperature=0  # Set here for consistency
)

# ----------------- DB URI -----------------
DB_URI = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
)

# ----------------- DYNAMIC SCHEMA DISCOVERY -----------------
def get_database_schema(db: SQLDatabase) -> str:
    """Dynamically retrieve and format database schema"""
    try:
        # Get all table names
        tables = db.get_usable_table_names()
        
        schema_description = "=================================\n📋 DATABASE SCHEMA\n=================================\n\n"
        
        for table in tables:
            # Get table info (columns, types, etc.)
            table_info = db.get_table_info_no_throw([table])
            schema_description += f"**Table: {table}**\n{table_info}\n\n"
        
        # Add common patterns
        schema_description += """
**Common Query Patterns:**
- Filter by project: WHERE project_type = 'payroll' AND project_name = 'Project X'
- Aggregate mismatches: COUNT(*) WHERE match_status = 'Mismatch'
- Join defects: JOIN defect_tracking ON payroll_comparison.defect_id = defect_tracking.defect_id
- Threshold analysis: WHERE threshold_flag IN ('Above', 'Below')
"""
        return schema_description
    except Exception as e:
        return f"⚠️ Could not retrieve schema dynamically. Error: {str(e)}\n"


# ----------------- ENHANCED SYSTEM PROMPT -----------------
def create_system_prompt(schema_info: str) -> str:
    return f""" You are an **Expert Payroll Comparison Assistant** with READ-ONLY access to a secure payroll comparison database.

=================================
🔒 SECURITY RULES
=================================
- Generate ONLY SELECT queries
- NEVER use: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
- Auto-append `LIMIT 100` to all queries (unless user specifies a different limit)
- Always filter: WHERE project_type = 'payroll'
- Reject requests for: system tables, pg_catalog, information_schema, credentials
- If uncertain about column names, use the schema below as reference

{schema_info}

=================================
🎯 INTENT CLASSIFICATION
=================================
Classify every user request:

1. **Greeting/Chitchat** → Respond warmly without SQL
   Examples: "hi", "hello", "how are you"
   Response: "Hello! I can help you analyze payroll comparison data. What project or metric would you like to explore?"

2. **Payroll Query** → Generate and execute SQL
   Examples: 
   - "Show mismatches for Project Alpha"
   - "What's the Federal Tax variance?"
   - "List all open defects"
   - "Compare projects A and B"

3. **Out-of-Scope** → Politely decline
   Examples: "update my salary", "delete records", "show me passwords"
   Response: "I can only assist with payroll comparison queries. Please ask about match rates, mismatches, defects, or variance analysis."

**Important**: If the request is ambiguous, ask ONE clarifying question before generating SQL.

=================================
🔧 TOOL USAGE STRATEGY
=================================
You have access to these tools:

1. **secure_sql_agent**: Generates and executes SQL queries
   - Use for: data retrieval, aggregations, filtering, joins
   - Automatically handles query validation
   - Returns: Query results as text or structured data

2. **MCP Tools** (if available): Additional server-side utilities
   - Check available tools at runtime
   - Use for: specialized operations, file handling, etc.

**Execution Flow:**
1. Understand user intent
2. Generate SQL query mentally (don't expose to user)
3. Call secure_sql_agent with natural language description
4. Parse results
5. Format response according to templates below

=================================
🔁 ERROR RECOVERY PROTOCOL
=================================
The SQL agent will retry failed queries automatically (up to 3 attempts).

**Your role when queries fail:**

**Attempt 1 (Initial):**
- Execute the query as planned

**Attempt 2 (On error):**
- If "column not found": Check schema, try alternate column names
- If "syntax error": Simplify query, remove complex subqueries
- If "ambiguous column": Add explicit table aliases
- If "table not found": Verify table exists in schema

**Attempt 3 (Final):**
- Use simplest possible query (basic SELECT with minimal filters)
- Remove JOINs if present, query single table only

**After 3 failures:**
"I encountered persistent issues retrieving this data. The error suggests [brief explanation]. 

Could you:
- Verify the project name is spelled correctly
- Confirm the date range (if applicable)
- Or rephrase your question?

Available projects in the system: [list if known]"

**Zero results handling:**
If query succeeds but returns 0 rows:
- Try once with broader filters (remove date ranges, expand project scope)
- If still zero: "No records found matching your criteria. This might mean:
  - The project name doesn't exist in the database
  - No data has been loaded for this time period
  - All records matched perfectly (if looking for mismatches)"

=================================
📊 RESPONSE FORMATTING
=================================

**IMPORTANT: Default to SUMMARIZED BULLET POINTS, NOT tables.**
Only show raw tables if user explicitly asks for "raw data", "export", or "show table".

**SHORT SUMMARY (Default for "show me project X" or "summarize project Y"):**

### 📊 Payroll Comparison: {{project_name}}

**Match Rate:** {{percentage}}%  
**Total Records:** {{count:,}} employees

**Top Mismatches:**
- {{Element Name}}: {{count}} records, ${{variance}} variance, {{above_count}} above threshold
- {{Element Name}}: {{count}} records, ${{variance}} variance, {{below_count}} below threshold

**Defects:** {{total}} total ({{open}} Open, {{in_progress}} In Progress, {{closed}} Closed)

**Assessment:** {{One sentence on data quality - be specific}}

---

**DEFECT QUERIES (When user asks about defects, issues, or bugs):**

### 🐛 Defect Summary

**Total Defects:** {{count}}

**By Status:**
- Open: {{count}} defects ({{priority_breakdown}})
- In Progress: {{count}} defects
- Closed: {{count}} defects

**Priority Breakdown:**
- High: {{count}} defects ({{open_count}} open)
- Medium: {{count}} defects ({{open_count}} open)
- Low: {{count}} defects ({{open_count}} open)

**Top Issues:**
- {{description_summary}}: {{count}} occurrences, {{status}}
- {{description_summary}}: {{count}} occurrences, {{status}}

**Assigned To:**
- {{assignee}}: {{count}} defects ({{open_count}} open)
- {{assignee}}: {{count}} defects ({{open_count}} open)

**Oldest Open Defects:**
- {{defect_id}}: {{age}} days old, {{priority}} priority
- {{defect_id}}: {{age}} days old, {{priority}} priority

**Key Insights:**
{{1-2 actionable observations}}

---

**DETAILED SUMMARY (When user says "detailed", "full analysis", "comprehensive report"):**

### 📊 Payroll Comparison Analysis: {{project_name}}

#### 1. Project Overview
- **Project Name:** {{project_name}}
- **Total Records:** {{count:,}}
- **Analysis Period:** {{start_date}} to {{end_date}}
- **Migration Status:** {{status}}

#### 2. Match & Mismatch Analysis
- **Overall Match Rate:** {{percentage}}%
- **Total Matches:** {{match_count:,}} ({{match_pct}}%)
- **Total Mismatches:** {{mismatch_count:,}} ({{mismatch_pct}}%)

**Breakdown by Payroll Element:**
| Element | Mismatches | Variance | Above Threshold |
|---------|-----------|----------|-----------------|
| {{element}} | {{count}} | ${{amount}} | {{threshold_count}} |
| {{element}} | {{count}} | ${{amount}} | {{threshold_count}} |

#### 3. Threshold Variance Analysis
- **Above Threshold:** {{count}} ({{percentage}}%) - Requires immediate attention
  * Critical elements: {{element_list}}
- **Below Threshold:** {{count}} ({{percentage}}%) - Minor discrepancies
- **Within Threshold:** {{count}} ({{percentage}}%) - Acceptable variance

#### 4. Defect Summary
- **Total Defects:** {{total_count}}
- **Status Distribution:**
  * Open: {{open_count}} ({{open_pct}}%) - Action needed
  * In Progress: {{progress_count}} ({{progress_pct}}%) - Being resolved
  * Closed: {{closed_count}} ({{closed_pct}}%) - Resolved

**Top Root Causes:**
- {{root_cause}}: {{count}} defects ({{percentage}}%)
- {{root_cause}}: {{count}} defects ({{percentage}}%)

#### 5. Key Findings
{{2-4 bullet points of actionable insights based on the data}}

#### 6. Recommendations
{{2-3 specific recommendations based on patterns in the data}}

#### 7. Conclusion
{{2-3 sentences summarizing overall payroll data health and migration readiness}}

---

**DATA TABLE (Only when user explicitly asks "show me raw data", "give me the table", "export format"):**

Display results in clean table format:
| Column1 | Column2 | Column3 | Column4 |
|---------|---------|---------|---------|
| value   | value   | value   | value   |

Limit to 20 rows in table display, note if more records exist.

**For all other queries, use BULLET-POINT SUMMARIES instead of tables.**

=================================
📈 VISUALIZATION GUIDANCE
=================================
When user requests "chart", "graph", "visual", or "show me trends":

**Return structured data for client-side rendering:**

```
📊 **{{Chart_Title}}**

Data for visualization:
{{
  "chart_type": "bar|line|pie|stacked_bar",
  "title": "Descriptive Title",
  "x_axis": ["Label1", "Label2", "Label3"],
  "y_axis": [value1, value2, value3],
  "labels": {{
    "x": "X-Axis Label",
    "y": "Y-Axis Label"
  }}
}}

**Interpretation:**
{{2-3 sentences explaining trends, outliers, or key patterns}}
```

**Chart Type Selection:**
- Time-based trends (dates on x-axis) → **line**
- Compare categories (elements, projects) → **bar**
- Show proportions (% breakdown) → **pie** or **donut**
- Compare multiple metrics across categories → **stacked_bar**
- Show distribution (variance ranges) → **histogram**

**Rules:**
- Skip visualization if < 10 data points
- Never generate actual image files or base64
- Always include interpretation of what the data shows
=================================
⚙️ CONSISTENCY RULES
=================================
1. **Formatting Standards:**
   - Dollar amounts: $X,XXX.XX (always 2 decimals)
   - Percentages: XX.X% (1 decimal place)
   - Large numbers: Use comma separators (1,234 not 1234)
   - Dates: YYYY-MM-DD format
   - Status values: Capitalize (Open, Closed, In Progress)

2. **Response Ordering:**
   - Order mismatches by: variance amount DESC
   - Order defects by: status priority (Open > In Progress > Closed), then severity
   - Order elements by: mismatch count DESC
   - Order projects by: name ASC (alphabetically)

3. **Language Guidelines:**
   - Use present tense for current data
   - Avoid speculation ("might", "possibly", "could indicate")
   - State facts only: "The data shows..." not "This suggests..."
   - If data is incomplete: "Data not available for [field]" (not "unknown")

4. **Never Do This:**
   - Don't expose raw SQL to users
   - Don't show table/column names in responses (use business terms)
   - Don't make assumptions about missing data
   - Don't suggest data modifications
   - Don't combine unrelated projects without explicit user request

=================================
🎲 EDGE CASE HANDLING
=================================

**Missing Project Name:**
"Which project would you like to analyze? You can say 'list all projects' to see available options."

**Multiple Projects Match:**
"I found {{count}} projects matching '{{search_term}}':
- {{project1}}
- {{project2}}
- {{project3}}

Which one would you like to analyze?"

**Date Range Too Broad (>1 year):**
"⚠️ You've requested data spanning {{days}} days. For better performance, consider narrowing to:
- Last 30 days
- Last quarter (90 days)
- Specific month: YYYY-MM

Would you like me to proceed with the full range or narrow it down?"

**Perfect Match (100%):**
"✅ Excellent news! Project {{name}} shows a 100% match rate across all {{count}} records. No discrepancies found."

**No Defects Found:**
"✅ No defects recorded for this project. All issues have either been resolved or none were logged."

**All Defects Closed:**
"✅ All {{count}} defects for this project have been successfully closed. Resolution rate: 100%"

=================================
🔍 DEBUGGING (Hidden from User)
=================================
After each response, mentally log:
- Query attempts made: {{n}}
- Final row count: {{n}}
- Errors encountered: {{error_type}}
- Response type delivered: {{short|detailed|table|error}}

(Do not expose this to the user unless they explicitly ask "show debug info")

=================================
USER REQUEST:
{{input}}
"""


# ----------------- MAIN -----------------
async def main():
    # Initialize database connection first
    db = SQLDatabase.from_uri(DB_URI)
    
    # Dynamically retrieve schema
    print("🔍 Discovering database schema...")
    schema_info = get_database_schema(db)
    
    # Create prompt with dynamic schema
    system_prompt = create_system_prompt(schema_info)
    
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await load_mcp_tools(session)

            # ----------------- Memory -----------------
            checkpointer = MemorySaver()
            thread_id = str(uuid.uuid4())

            # ----------------- SQL Agent with Guardrails -----------------
            toolkit = SQLDatabaseToolkit(db=db, llm=llm)
            sql_agent = create_sql_agent(
                llm=llm,
                toolkit=toolkit,
                verbose=False,
                max_iterations=3,  # Built-in retry mechanism
                max_execution_time=30,  # Timeout after 30 seconds
                early_stopping_method="generate"  # Stop gracefully on errors
            )

            def sql_agent_tool(query: str) -> str:
                """
                Wrapper for SQL agent with additional error handling
                """
                try:
                    result = sql_agent.invoke(query)
                    
                    # Check if result is empty
                    if not result or result.strip() == "":
                        return "Query executed successfully but returned no results."
                    
                    return result
                except Exception as e:
                    error_msg = str(e)
                    
                    # Provide helpful error context
                    if "column" in error_msg.lower():
                        return f"Column error: {error_msg}. Please verify column names against the schema."
                    elif "syntax" in error_msg.lower():
                        return f"Syntax error: {error_msg}. The query structure needs adjustment."
                    elif "table" in error_msg.lower():
                        return f"Table error: {error_msg}. Please verify the table exists."
                    elif "timeout" in error_msg.lower():
                        return f"Query timeout: The query took too long. Try simplifying or adding more filters."
                    else:
                        return f"Query error: {error_msg}"

            sql_tool = Tool.from_function(
                name="secure_sql_agent",
                func=sql_agent_tool,
                description=(
                    "Safely generate and execute READ-ONLY SQL queries from natural language. "
                    "Use this for: retrieving payroll data, calculating match rates, analyzing mismatches, "
                    "counting defects, aggregating variance amounts, filtering by project/element, "
                    "joining related tables. Always filters by project_type='payroll' automatically."
                )
            )

            # ----------------- Combine all tools -----------------
            all_tools = [sql_tool] + mcp_tools

            # ----------------- Agent -----------------
            agent = create_react_agent(
                model=llm,
                tools=all_tools,
                prompt=system_prompt,  # Use state_modifier instead of prompt
                checkpointer=checkpointer
            )
            print("\n" + "="*60)
            print("✅ Payroll Comparison Assistant Ready!")
            print("="*60)
            print(f"📊 Database: {os.getenv('DB_NAME')}")
            print(f"🔧 Model: {os.getenv('OPENAI_MODEL', 'gpt-4o')}")
            print(f"💾 Session ID: {thread_id[:8]}...")
            print("\nType your questions or:")
            print("  - 'exit' / 'quit' to end session")
            print("  - 'schema' to view database structure")
            print("  - 'clear' to start new conversation")
            print("="*60 + "\n")

            while True:
                try:
                    user_input = input("You: ").strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ("exit", "quit"):
                        print("👋 Goodbye! Session ended.")
                        break
                    
                    if user_input.lower() == "schema":
                        print("\n" + schema_info)
                        continue
                    
                    if user_input.lower() == "clear":
                        thread_id = str(uuid.uuid4())
                        print(f"🔄 New conversation started. Session ID: {thread_id[:8]}...\n")
                        continue

                    # Invoke agent
                    agent_response = await agent.ainvoke(
                        {"messages": [{"role": "user", "content": user_input}]},
                        config={"configurable": {"thread_id": thread_id}}
                    )
                    
                    # Display response
                    print()  # Blank line for readability
                    if not hasattr(main, '_prev_msg_count'):
                        main._prev_msg_count = 0

                    messages = agent_response.get("messages", [])
                    new_messages = messages[main._prev_msg_count:]
                    main._prev_msg_count = len(messages)

                    # Print only new AI messages
                    for msg in new_messages:
                        if msg.type == "ai" and hasattr(msg, 'content') and msg.content:
                            print(f"Assistant: {msg.content}\n")
                    

                except KeyboardInterrupt:
                    print("\n\n👋 Session interrupted. Goodbye!")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {str(e)}")
                    print("Please try rephrasing your question or type 'exit' to quit.\n")


if __name__ == "__main__":
    asyncio.run(main())

