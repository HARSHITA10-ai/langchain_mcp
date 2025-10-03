import os
import psycopg2
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from collections import Counter
import matplotlib.pyplot as plt
import io
import base64

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

@mcp.tool()
def run_query(query: str, project_name: str = None, verbosity: str = "detailed") -> str:
    """
    Execute a SQL query and return a summary with controllable verbosity.
    """
    try:
        cursor = conn.cursor()

        # inject project_name filter if provided
        if project_name:
            if "where" in query.lower():
                query = query.rstrip(";") + f" AND project_name = '{project_name}'"
            else:
                query = query.rstrip(";") + f" WHERE project_name = '{project_name}'"
        
        cursor.execute(query)

        try:
            rows = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
        except psycopg2.ProgrammingError:
            rows = []
            colnames = []
        
        cursor.close()

        if not rows:
            return f"Query executed successfully, but returned no results{' for project ' + project_name if project_name else ''}."

        summary_lines = []
        summary_lines.append(f"Query executed successfully. Total rows: {len(rows)}")
        summary_lines.append(f"Columns: {', '.join(colnames)}")

        if verbosity in ("detailed", "full"):
            summary_lines.append("\nSample rows:")
            for row in rows[:5]:
                summary_lines.append("  ".join(f"{col}: {val}" for col, val in zip(colnames, row)))
        
        if verbosity == "full":
            numeric_cols = [idx for idx, desc in enumerate(cursor.description) if desc.type_code in (20, 21, 23, 700, 701)]
            if numeric_cols:
                summary_lines.append("\nNumeric column insights:")
                for idx in numeric_cols:
                    col_vals = [row[idx] for row in rows if row[idx] is not None]
                    if col_vals:
                        col_min = min(col_vals)
                        col_max = max(col_vals)
                        col_avg = sum(col_vals)/len(col_vals)
                        summary_lines.append(f"{colnames[idx]} -> min: {col_min}, max: {col_max}, avg: {col_avg:.2f}")
            
            text_cols = [i for i in range(len(colnames)) if i not in numeric_cols]
            if text_cols:
                summary_lines.append("\nCategorical/text column insights:")
                for idx in text_cols:
                    col_vals = [row[idx] for row in rows if row[idx] is not None]
                    if col_vals:
                        unique_vals = set(col_vals)
                        summary_lines.append(f"{colnames[idx]} -> unique values: {len(unique_vals)}; sample: {list(unique_vals)[:5]}{'...' if len(unique_vals) > 5 else ''}")

        return "\n".join(summary_lines)
    except Exception as e:
        return f"Error executing query: {str(e)}"

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


    
if __name__ == "__main__":
    mcp.run(transport="stdio")




