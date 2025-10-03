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

# from guardrails import Guard
# from guardrails.hub import ValidSQL,ExcludeSqlPredicates

# ----------------- LOAD CONFIG -----------------
load_dotenv()

# ----------------- LLM -----------------
llm = ChatOpenAI(model_name=os.getenv("OPENAI_MODEL", "gpt-4.1"), temperature=0)

# ----------------- DB URI -----------------
DB_URI = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
)
       
# ----------------- PROMPT -----------------
system_prompt = """
You are an expert pay Compare Assistant with READ-ONLY access to pay comparison data.

SECURITY RULES (CRITICAL):
- Only execute safe, read-only SELECT queries-no data modifications allowed.
- Never expose passwords, secrets, tokens, or any sensitive information.
- Automatically limit all queries to 100 rows to maintain performance and safety.
- Do not access system tables or metadata that may contain sensitive information.

INTENT AND SCOPE HANDLING:
- First, classify user request into one of: Greeting, Pay Compare Query, or Out-of-Scope.
  - If the input is a greeting, respond warmly and briefly without querying the database.
- For ambiguous or unclear requests, ask for clarification before proceeding.
- Never guess or hallucinate data or schema details.

RESPONSE FORMATTING:
- For pay compare queries:
  * Convert natural language to efficient, safe SQL queries with row limits.
  * Execute queries using the sql_query tool.
  * Summarize key insights concisely, focusing on business-relevant takeaways.
  * Do not reveal UUIDs, SQL syntax, or database internals to users.
  * Keep responses succinct, informative, and user-friendly.

User request: {input}
Always prioritize security, accuracy, and helpfulness. Strictly enforce the pay compare query scope and maintain professional, clear communication.
"""


# ----------------- LLM Summarization -----------------
def llm_summarize_result(raw_result: str) -> str:
    prompt = PromptTemplate.from_template("""
You are a business analyst. Summarize the following SQL query result in clear, concise language for a non-technical audience.

Result:
{raw_result}

Summary:
""")
    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run(raw_result=raw_result).strip()


# ----------------- MAIN -----------------
async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],  # safer path handling
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await load_mcp_tools(session)

            # ----------------- Memory -----------------
            checkpointer = MemorySaver()
            thread_id = str(uuid.uuid4())

            # ----------------- SQL Agent -----------------
            db = SQLDatabase.from_uri(DB_URI)
            toolkit = SQLDatabaseToolkit(db=db, llm=llm)
            sql_agent = create_sql_agent(llm=llm, toolkit=toolkit, verbose=False)

            def sql_agent_tool(query: str) -> str:
                return sql_agent.run(query)

            sql_tool = Tool.from_function(
                name="secure_sql_agent",
                func=sql_agent_tool,
                description="Safely generate and execute SQL queries from natural language using LangChain SQLAgent and Guardrails."
            )

            # ----------------- Hybrid summarization tool -----------------
            async def hybrid_summarize_tool(raw_result: str, verbosity: str = "detailed") -> str:
                if verbosity == "brief":
                    return await session.invoke_tool("summarize_result", {"raw_result": raw_result})
                else:
                    return llm_summarize_result(raw_result)

            summarize_tool = Tool.from_function(
                name="hybrid_summarize",
                func=hybrid_summarize_tool,
                description="Summarize SQL query results using either MCP tool (brief) or LLM (detailed/full)."
            )

            # ----------------- Combine all tools -----------------
            all_tools = [sql_tool, summarize_tool] + mcp_tools

            # ----------------- Agent -----------------
            agent = create_react_agent(
                model=llm,
                tools=all_tools,
                prompt=system_prompt,
                checkpointer=checkpointer
            )

            print("\nSQL Agent is ready! Type your questions (or 'exit' to quit)\n")
            print("This agent maintains conversation history to provide context-aware responses.\n")

            while True:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit"):
                    print("Goodbye!")
                    break

                try:
                    agent_response = await agent.ainvoke(
                        {
                            "messages": [{"role": "user", "content": user_input}],
                        },
                        config={"configurable": {"thread_id": thread_id}}
                    )
                    for m in agent_response.get("messages", []):
                        m.pretty_print()

                except Exception as e:
                    print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())





 

