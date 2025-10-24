# 🤖 Conversational SQL AI Assistant for Pay Comparison

This project implements a sophisticated, secure, and conversational AI assistant that allows users to query a pay-comparison database using natural language. It leverages a client-server architecture with the Model-Centric Protocol (MCP) to ensure that database interactions are safely sandboxed.

The core of the application is a **LangGraph REACT agent** running in the client, which intelligently uses a combination of local and remote tools to answer user queries.

## ✨ Features

* **Conversational Interface**: Users can ask questions in plain English, and the agent maintains conversation history for context-aware follow-ups.
* **Natural Language to SQL**: Automatically converts user questions into safe, read-only SQL queries.
* [cite_start]**Secure, Sandboxed Execution**: Uses a client-server model where the server exclusively handles database connections and query execution, preventing the client or the LLM from having direct DB access.
* [cite_start]**Hybrid Tool Architecture**: Combines local LLM-powered tools (e.g., for detailed summarization) with remote, server-side tools (e.g., for query execution and brief summaries) via MCP.
* **Security First**: The system prompt enforces strict security rules, such as executing only `SELECT` queries, limiting rows to 100, and preventing data modification.
* [cite_start]**Environment-based Configuration**: All sensitive information like API keys and database credentials are managed securely through a `.env` file.

---

## 🏗️ Architecture

[cite_start]The application is split into two main components that communicate over `stdio` using the Model-Centric Protocol (MCP).

1.  **`client.py` (The Brains)**:
    * Manages the user-facing command-line interface.
    * Hosts the LangGraph agent, which orchestrates the entire workflow.
    * Connects to OpenAI to leverage an LLM for reasoning and generating user-friendly responses.
    * Decides which tool to use (e.g., the secure SQL agent or the summarizer).
    * Communicates with the server via an MCP client session to invoke remote tools.

2.  [cite_start]**`server.py` (The Secure Worker)**:
    * Runs as a background process managed by the client.
    * [cite_start]Establishes and holds the sole connection to the PostgreSQL database.
    * [cite_start]Exposes a set of secure tools (e.g., `run_query`, `summarize_result`) via an MCP server.
    * [cite_start]Executes SQL queries received from the client and returns the results, ensuring no direct database exposure.

# 🚀 Getting Started

Follow these instructions to set up and run the project locally.

### Prerequisites

* Python 3.9+
* PostgreSQL database running and accessible.
* An OpenAI API Key.

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <your-repository-directory>



### 2. Set Up a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

**On macOS/Linux:**

```bash
python3 -m venv venv
source venv/bin/activate

**On Windows:**

```bash
python -m venv venv
.\venv\Scripts\activate


### 3. Install Dependencies

Install all the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt

### 4. Configure Environment Variables

Create a file named `.env` in the root of the project directory. You can copy the example below and fill in your actual credentials.

**⚠️ Important:** Never commit your `.env` file to version control.

```ini
# .env file

# OpenAI Configuration
OPENAI_API_KEY="sk-..."
OPENAI_MODEL="gpt-4-turbo"

# PostgreSQL Database Configuration
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="your_database_name"
DB_USER="your_database_user"
DB_PASS="your_database_password"

### 5. Run the Application

Execute the `client.py` script to start the interactive assistant. The client will automatically start and manage the `server.py` process in the background.

```bash
python client.py


-You should see a welcome message, and you can start asking questions!

    SQL Agent is ready! Type your questions (or 'exit' to quit)

    This agent maintains conversation history to provide context-aware responses.




## 🛠️ How It Works

This section details the inner workings of the client and server components.

---

### Client (`client.py`)

* **Agent Initialization**: `create_react_agent` from LangGraph is used to create an agent that can reason and decide which tool to use next.
* **Tool Aggregation**: It combines three types of tools to give the agent a wide range of capabilities.
    * **MCP Tools**: Loaded from the server using `load_mcp_tools`, these are primarily used for database operations.
    * **SQL Agent Tool**: A LangChain `SQLDatabaseToolkit` is wrapped into a single tool, `secure_sql_agent`, for generating and running SQL from natural language.
    * **Hybrid Summarizer**: A custom tool, `hybrid_summarize`, can call a brief, rule-based summarizer on the server or a more detailed LLM-based summarizer on the client.
* **Conversation Memory**: `MemorySaver` keeps track of the conversation, allowing the agent to understand context from previous messages.
* **Main Loop**: The application enters a `while` loop, waiting for user input, invoking the agent to get a response, and then printing the final, user-friendly output.

---

### Server (`server.py`)

* **MCP Server**: A `FastMCP` instance is created to listen for tool invocation requests from the client.
* **Database Connection**: The server establishes a persistent connection to the PostgreSQL database using `psycopg2`.
* **`@mcp.tool()` Decorator**: Functions like `run_query` and `summarize_result` are exposed as tools that the client can call remotely by using this decorator.
* **Safe Query Execution**: The `run_query` tool is designed to be safe. It can inject additional filters (like `project_name`) and handles the entire query lifecycle, returning only the results and not the connection object.


## Example Usage

Here is an example of a conversation with the assistant:

```text
SQL Agent is ready! Type your questions (or 'exit' to quit)

This agent maintains conversation history to provide context-aware responses.

You: What are the average salaries for Senior Software Engineers?

================================ Human Message =================================

What are the average salaries for Senior Software Engineers?

================================== AI Message ===================================
I can help with that. The average salary for a Senior Software Engineer is $155,000 per year, based on the data from our latest pay comparison analysis.

You: How does that compare to a Staff Engineer?

================================ Human Message =================================

How does that compare to a Staff Engineer?

================================== AI Message ===================================
A Staff Engineer has an average salary of $190,000 per year, which is approximately 22.6% higher than the average for a Senior Software Engineer.