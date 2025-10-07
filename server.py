import os
import psycopg2
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from collections import Counter
import matplotlib.pyplot as plt
import io
import base64
import seaborn as sns
import pandas as pd
from typing import List, Dict, Any
import uuid

# ----------------- LOAD CONFIG -----------------
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT", "5432")

# ----------------- CONNECT TO DB -----------------
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=DB_PORT,
)

mcp = FastMCP("sql")

# ----------------- TOOLS -----------------

# @mcp.tool()
# def run_query(query: str, project_name: str = None, verbosity: str = "detailed") -> str:
#     """
#     Execute a SQL query and return a summary with controllable verbosity.
#     """
#     try:
#         cursor = conn.cursor()

#         # inject project_name filter if provided
#         if project_name:
#             if "where" in query.lower():
#                 query = query.rstrip(";") + f" AND project_name = '{project_name}'"
#             else:
#                 query = query.rstrip(";") + f" WHERE project_name = '{project_name}'"
        
#         cursor.execute(query)

#         try:
#             rows = cursor.fetchall()
#             colnames = [desc[0] for desc in cursor.description]
#         except psycopg2.ProgrammingError:
#             rows = []
#             colnames = []
        
#         cursor.close()

#         if not rows:
#             return f"Query executed successfully, but returned no results{' for project ' + project_name if project_name else ''}."

#         summary_lines = []
#         summary_lines.append(f"Query executed successfully. Total rows: {len(rows)}")
#         summary_lines.append(f"Columns: {', '.join(colnames)}")

#         if verbosity in ("detailed", "full"):
#             summary_lines.append("\nSample rows:")
#             for row in rows[:5]:
#                 summary_lines.append("  ".join(f"{col}: {val}" for col, val in zip(colnames, row)))
        
#         if verbosity == "full":
#             numeric_cols = [idx for idx, desc in enumerate(cursor.description) if desc.type_code in (20, 21, 23, 700, 701)]
#             if numeric_cols:
#                 summary_lines.append("\nNumeric column insights:")
#                 for idx in numeric_cols:
#                     col_vals = [row[idx] for row in rows if row[idx] is not None]
#                     if col_vals:
#                         col_min = min(col_vals)
#                         col_max = max(col_vals)
#                         col_avg = sum(col_vals)/len(col_vals)
#                         summary_lines.append(f"{colnames[idx]} -> min: {col_min}, max: {col_max}, avg: {col_avg:.2f}")
            
#             text_cols = [i for i in range(len(colnames)) if i not in numeric_cols]
#             if text_cols:
#                 summary_lines.append("\nCategorical/text column insights:")
#                 for idx in text_cols:
#                     col_vals = [row[idx] for row in rows if row[idx] is not None]
#                     if col_vals:
#                         unique_vals = set(col_vals)
#                         summary_lines.append(f"{colnames[idx]} -> unique values: {len(unique_vals)}; sample: {list(unique_vals)[:5]}{'...' if len(unique_vals) > 5 else ''}")

#         return "\n".join(summary_lines)
#     except Exception as e:
#         return f"Error executing query: {str(e)}"

@mcp.tool()
def run_query(query: str, project_name: str = None) -> list:
    """
    Execute a SQL query and return structured rows as a list of dictionaries.
    Each dict maps column names to their corresponding values.
    """
    try:
        cursor = conn.cursor()

        # Inject project_name filter if provided
        if project_name:
            if "where" in query.lower():
                query = query.rstrip(";") + f" AND project_name = '{project_name}'"
            else:
                query = query.rstrip(";") + f" WHERE project_name = '{project_name}'"

        cursor.execute(query)

        # Fetch column names and rows
        try:
            rows = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
        except psycopg2.ProgrammingError:
            rows = []
            colnames = []

        cursor.close()

        # Return structured result
        result = [dict(zip(colnames, row)) for row in rows]
        return result

    except Exception as e:
        # Return structured error object for LLM parsing
        return [{"error": str(e)}]


@mcp.tool()
def summarize_result(raw_result: str) -> str:
    """
    Summarize raw SQL query result into business-friendly language.
    Assumes input is a string with rows and columns.
    """
    lines = raw_result.strip().splitlines()
    if not lines:
        return "No data to summarize."
    
    summary = []
    summary.append(f"Total lines: {len(lines)}")
    columns = lines[1].replace("Columns: ", "").split(", ") if "Columns:" in lines[1] else []
    summary.append(f"Columns: {', '.join(columns)}")
    samples = [line for line in lines if ":" in line]
    if samples:
        summary.append("Sample insights:")
        for s in samples[1:5]:
            summary.append(f"- {s}")
    
    return "\n".join(summary)


def render_chart(
    data: List[Dict[str, Any]],
    chart_type: str,
    title: str,
    x_col: str = None,
    y_col: str = None,
    value_col: str = None
) -> Dict[str, str]:
    """Internal chart rendering logic used by both single and multi-chart tools."""
    df = pd.DataFrame(data)
    # Pie and Pairplot handle their own figures, others use a shared one.
    if chart_type not in ["pie", "pairplot"]:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig, ax = None, None # Initialize to None

    try:
        if chart_type == "bar":
            sns.barplot(data=df, x=x_col, y=y_col, ax=ax)
        elif chart_type == "horizontal_bar":
            sns.barplot(data=df, x=y_col, y=x_col, ax=ax)
        elif chart_type == "line":
            sns.lineplot(data=df, x=x_col, y=y_col, ax=ax)
        elif chart_type == "scatter":
            sns.scatterplot(data=df, x=x_col, y=y_col, ax=ax)
        elif chart_type == "regression":
            sns.regplot(data=df, x=x_col, y=y_col, ax=ax)
        elif chart_type == "hist":
            sns.histplot(data=df, x=x_col, y=y_col, ax=ax)
        elif chart_type == "boxplot":
            sns.boxplot(data=df, x=x_col, y=y_col, ax=ax)
        elif chart_type == "violin":
            sns.violinplot(data=df, x=x_col, y=y_col, ax=ax)
        elif chart_type == "pie":
            fig, ax = plt.subplots(figsize=(10, 6)) # Create figure for pie
            pie_data = df.groupby(x_col)[y_col].sum() if y_col else df[x_col].value_counts()
            ax.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%')
        elif chart_type == "heatmap":
            if not x_col or not y_col:
                return {"error": "Heatmap requires x_col and y_col."}
            pivot_data = df.pivot_table(index=y_col, columns=x_col, values=value_col, aggfunc="sum", fill_value=0)
            sns.heatmap(pivot_data, annot=True, fmt=".1f", cmap="YlGnBu", ax=ax)
        elif chart_type == "pairplot":
            g = sns.pairplot(df.select_dtypes(include="number"))
            g.fig.suptitle(title, fontsize=16, weight="bold")
            buf = io.BytesIO()
            g.savefig(buf, format="png")
            buf.seek(0)
            encoded = base64.b64encode(buf.read()).decode('utf-8')
            buf.close()
            plt.close(g.fig)

            os.makedirs("charts", exist_ok=True)
            file_name = f"chart_{uuid.uuid4().hex[:8]}.png"
            file_path = os.path.abspath(os.path.join("charts", file_name))
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(encoded))
            
            return {
                "title": title,
                "image_base64": f"data:image/png;base64,{encoded}",
                "file_path": file_path,
                "summary": f"Pairplot showing relationships among numeric columns in the dataset."
            }

        # Finalize and save non-pairplot charts
        ax.set_title(title)
        if x_col: ax.set_xlabel(x_col.replace("_", " ").title())
        if y_col: ax.set_ylabel(y_col.replace("_", " ").title())
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close(fig)

        file_name = f"chart_{uuid.uuid4().hex[:8]}.png"
        file_path = os.path.abspath(os.path.join("charts", file_name))
        os.makedirs("charts", exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(encoded))
        
        summary = f"The chart '{title}' visualizes data using a {chart_type} format. It highlights key patterns and distributions based on the selected columns."

        return {
            "title": title,
            "image_base64": f"data:image/png;base64,{encoded}",
            "file_path": file_path,
            "summary": summary
        }

    except Exception as e:
        if fig:
            plt.close(fig)
        return {"error": f"Error generating chart: {e}"}


@mcp.tool()
def generate_chart(
    data: List[Dict[str, Any]],
    chart_type: str,
    title: str = "Chart",
    x_col: str = None,
    y_col: str = None,
    value_col: str = None
) -> Dict[str, str]:
    """Generate a single chart."""
    return render_chart(data, chart_type, title, x_col, y_col, value_col)


@mcp.tool()
def generate_charts(charts: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Generate multiple charts in one call.
    Each chart config should include: data, chart_type, title, x_col, y_col, value_col.
    """
    results = []
    for chart in charts:
        result = render_chart(
            data=chart.get("data", []),
            chart_type=chart.get("chart_type"),
            title=chart.get("title", "Chart"),
            x_col=chart.get("x_col"),
            y_col=chart.get("y_col"),
            value_col=chart.get("value_col")
        )
        results.append(result)
    return results

if __name__ == "__main__":
    mcp.run(transport="stdio")




