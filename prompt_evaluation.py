import mlflow
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
import os
load_dotenv()

# Use different env variable when using a different LLM provider

mlflow.set_tracking_uri("http://localhost:5000")

mlflow.set_experiment("GenAI Evaluation Quickstart")

DB_URI = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}")
db = SQLDatabase.from_uri(DB_URI)


SCHEMA = db.get_table_info()


PROMPT_V1 = [
    {
        "role": "system",
        "content": f"""
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


** PROJECT-SPECIFIC RULES **
- When user ask for list of project only provide the project names.
- If the user specify the project in the query like "for project X", "in project Y" etc then use that project name to filter.
- If the user asks anything which is project specific, and the project name is not specified, get the project name from the user.
- If the user specify anything like overall summary, general trend, comparison across projects etc , ask user for the project names if it is for specific project or for all projects.
- When providng the details considering all the projects , **do not** randomly assume any project and save it in history until and unless user specify the project name.
- Use **ILIKE** operator for matching project names to handle variations and spaces.
- Retrieve the corresponding `project_id` and use it in all filters (never use project name directly).
- Consider only projects of type **Payroll**.
- If a project name already exists in history, confirm reuse: "Use the same project (<name>) or a different one?"

** RESPONSE FORMAT **
1. Summarization:
   - For "summary" requests, return basic details: project name, defect counts, and threshold counts.
   - If any details is not available , say the data not available for particular project. And if generalized data is available then provide that.
   - For detailed summaries, provide the ellobrate details about all the defects and threshold mismatches with insights and numerical representations.
2. Be more **concise** while providing the reponse to the user and do not add any unnecessary information.
3. Maintain a **professional** tone in the response.

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

Provide concise, accurate, and actionable insights in natural language.""",
    },
    {
        "role": "user",
        # Use double curly braces to indicate variables.
        "content": "Question: {{question}}",
    },
]

mlflow.genai.register_prompt(
    name="qa_prompt",
    template=PROMPT_V1,
    commit_message="Initial prompt",
)

eval_dataset = [
  {
    "inputs": {"question": "Give me the overall summary"},
    "expectations": {
      "key_concepts": [
        "Clarify whether for specific or all projects",
        "Handle Payroll-only projects",
        "Ask user for project name if not specified"
      ]
    }
  },
  {
    "inputs": {"question": "Give me the overall summary of the project ECC to ECP Upgrade"},
    "expectations": {
      "key_concepts": [
        "Fetch project_id using ILIKE",
        "Include defect count",
        "Include threshold mismatch count",
        "Provide statistical insights"
      ]
    }
  },
  {
    "inputs": {"question": "Give me the defect summary of project ECC to ECP Upgrade"},
    "expectations": {
      "key_concepts": [
        "Summarize defects for project_id",
        "Categorize by defect type/severity",
        "Provide counts and insights"
      ]
    }
  },
  {
    "inputs": {"question": "Show the defect breakdown for project ECC to ECP Upgrade"},
    "expectations": {
      "key_concepts": [
        "Visualization required",
        "Prefer pie or donut chart",
        "Provide natural language chart summary"
      ]
    }
  },
  {
    "inputs": {"question": "Give me a detailed summary of project ECC to ECP Upgrade"},
    "expectations": {
      "key_concepts": [
        "In-depth defect details",
        "In-depth threshold mismatch details",
        "If missing data, mention unavailability"
      ]
    }
  },
  {
    "inputs": {"question": "Give me the password of user X"},
    "expectations": {
      "key_concepts": ["Reject request", "Sensitive data not allowed"]
    }
  },
  {
    "inputs": {"question": "Compare defects across projects ECC to ECP Upgrade and ECC to ECP Upgrade for the last 6 months"},
    "expectations": {
      "key_concepts": [
        "Time trend comparison",
        "Line or cumulative_line chart",
        "Multi-chart visualization",
        "Use project_id filters"
      ]
    }
  },
  {
    "inputs": {"question": "List all projects"},
    "expectations": {
      "key_concepts": [
        "Return only project names",
        "Filter to Payroll type projects"
      ]
    }
  },
  {
    "inputs": {"question": "Show threshold mismatches by pay period for project ECC to ECP Upgrade"},
    "expectations": {
      "key_concepts": [
        "Time-series visualization",
        "Group by pay period",
        "Use project_id filter"
      ]
    }
  },
  {
    "inputs": {"question": "I want a dashboard comparing defects, thresholds and top offenders across projects"},
    "expectations": {
      "key_concepts": [
        "Multi-chart visualization",
        "Ask if for specific or all projects",
        "Include bar and pie charts",
        "Provide bullet insights per chart"
      ]
    }
  },
  {
    "inputs": {"question": "What are the top 5 defect categories for project ECC to ECP Upgrade"},
    "expectations": {
      "key_concepts": [
        "Categorical breakdown",
        "Bar chart visualization",
        "Defect type-based aggregation"
      ]
    }
  },
  {
    "inputs": {"question": "Show me threshold trends for all Payroll projects"},
    "expectations": {
      "key_concepts": [
        "Trends over time → line chart",
        "Include multiple projects comparison",
        "Group by project and time"
      ]
    }
  },
  {
    "inputs": {"question": "Give me all records of defects"},
    "expectations": {
      "key_concepts": [
        "Reject or limit data to 5 rows (default LIMIT 5)",
        "Read-only SELECT only"
      ]
    }
  },
  {
    "inputs": {"question": "Delete the defects from project ECC to ECP Upgrade"},
    "expectations": {
      "key_concepts": [
        "Reject non-read operation",
        "Inform user only SELECT queries are allowed"
      ]
    }
  },
  {
    "inputs": {"question": "Show average threshold mismatch per project"},
    "expectations": {
      "key_concepts": [
        "Aggregate by project",
        "Bar chart for average comparison",
        "Use Payroll-only filter"
      ]
    }
  },
  {
    "inputs": {"question": "Which project has the highest number of defects"},
    "expectations": {
      "key_concepts": [
        "Aggregate across projects",
        "Identify top project by defect count",
        "Return project name and count"
      ]
    }
  },
  {
    "inputs": {"question": "Show me the correlation between defects and mismatches"},
    "expectations": {
      "key_concepts": [
        "Use correlation_heatmap or scatter chart",
        "Numeric relationship visualization",
        "Provide key statistical insights"
      ]
    }
  },
  {
    "inputs": {"question": "Give me threshold mismatch distribution for project ECC to ECP Upgrade"},
    "expectations": {
      "key_concepts": [
        "Value distribution visualization",
        "Use histogram or boxplot",
        "Provide outlier insights"
      ]
    }
  },
  {
    "inputs": {"question": "Show me the top 10 defects by frequency"},
    "expectations": {
      "key_concepts": [
        "Defect frequency analysis",
        "Bar chart visualization",
        "Limit top 10 entries"
      ]
    }
  },
  {
    "inputs": {"question": "Compare defect types for project ECC to ECP Upgrade and ECC to ECP Upgrade"},
    "expectations": {
      "key_concepts": [
        "Category comparison → grouped bar chart",
        "Multi-project comparison",
        "Statistical insights and patterns"
      ]
    }
  },
  {
    "inputs": {"question": "Give me the threshold mismatch trend for project ECC to ECP Upgrade over the last year"},
    "expectations": {
      "key_concepts": [
        "Time trend visualization",
        "Use line chart",
        "Aggregate by month or quarter",
        "Filter using project_id"
      ]
    }
  },
  {
    "inputs": {"question": "Show me the overall project comparison chart"},
    "expectations": {
      "key_concepts": [
        "Visualization for all projects",
        "Use bar chart",
        "Compare defect and threshold counts"
      ]
    }
  },
  {
    "inputs": {"question": "Give me the summary for all projects of type Payroll"},
    "expectations": {
      "key_concepts": [
        "Filter by project_type = Payroll",
        "Include defect and threshold summaries",
        "Return concise comparison insights"
      ]
    }
  },
  {
    "inputs": {"question": "Project ECC to ECP Upgrade has no data — what can you show?"},
    "expectations": {
      "key_concepts": [
        "Acknowledge missing data gracefully",
        "Fallback to generalized summary",
        "Provide available high-level metrics"
      ]
    }
  },
  {
    "inputs": {"question": "Show me the migration defects that occurred after August 2024"},
    "expectations": {
      "key_concepts": [
        "Filter defects by date",
        "Time-filtered summary",
        "Bar chart or table output"
      ]
    }
  }
]


from openai import OpenAI

client = OpenAI()


@mlflow.trace
def predict_fn(question: str) -> str:
    prompt = mlflow.genai.load_prompt("prompts:/qa_prompt@latest")
    rendered_prompt = prompt.format(question=question)

    response = client.chat.completions.create(
        model="gpt-4o", messages=rendered_prompt
    )
    return response.choices[0].message.content

from mlflow.entities import Feedback
from mlflow.genai import scorer
from mlflow.genai.scorers import Guidelines

# Define LLM scorers
is_concise = Guidelines(
    name="is_concise", guidelines="The response should be concise and to the point."
)
is_professional = Guidelines(
    name="is_professional", guidelines="The response should be in professional tone."
)


# Evaluate the coverage of the key concepts using custom scorer
@scorer
def concept_coverage(outputs: str, expectations: dict) -> Feedback:
    concepts = set(expectations.get("key_concepts", []))
    included = {c for c in concepts if c.lower() in outputs.lower()}
    return Feedback(
        value=len(included) / len(concepts),
        rationale=(
            f"Included {len(included)} out of {len(concepts)} concepts. Missing: {concepts - included}"
        ),
    )


mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=predict_fn,
    scorers=[is_concise, is_professional, concept_coverage],
)
