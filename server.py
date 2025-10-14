
# import os
# from dotenv import load_dotenv
# from mcp.server.fastmcp import FastMCP
# from collections import Counter
# import matplotlib.pyplot as plt
# import io
# import base64
# import seaborn as sns
# import pandas as pd
# from typing import List, Dict, Any
# import uuid
# import logging
# import time
# import json
# import ast

# # ----------------- SETUP LOGGING -----------------
# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
#     handlers=[logging.FileHandler("app.log")]
# )
# logger = logging.getLogger("Server")

# # ----------------- LOAD CONFIG -----------------
# load_dotenv()
# logger.debug("Loaded environment variables")
# mcp = FastMCP("sql")
# logger.debug("FastMCP initialized")

# # ----------------- TOOLS -----------------
# @mcp.tool()
# def summarize_result(raw_result: str) -> Dict[str, Any]:
#     """Summarize raw SQL query result into business-friendly language."""
#     logger.debug("summarize_result called with input type: %s, length: %d", type(raw_result), len(str(raw_result)))
#     try:
#         data = raw_result
#         if isinstance(raw_result, str):
#             try:
#                 data = json.loads(raw_result)
#             except json.JSONDecodeError:
#                 try:
#                     data = ast.literal_eval(raw_result)
#                 except (ValueError, SyntaxError):
#                     pass

#         if isinstance(data, list) and all(isinstance(item, dict) for item in data):
#             df = pd.DataFrame(data)
#             logger.debug(f"Converted input to DataFrame, shape: {df.shape}, columns: {df.columns.tolist()}")
#             id_columns = [col for col in df.columns if col.lower() in ['id', 'uuid'] or 'id' in col.lower()]
#             df = df[[col for col in df.columns if col not in id_columns]]
#             summary = [
#                 f"Total rows: {len(df)}",
#                 f"Columns: {', '.join(df.columns)}"
#             ]
#             if not df.empty:
#                 summary.append("Sample insights:")
#                 for _, row in df.head(5).iterrows():
#                     summary.append(f"- {', '.join(f'{col}: {val}' for col, val in row.items())}")
#             result = {"success": True, "summary": "\n".join(summary)}
#             logger.debug("Summarized result: %s", result["summary"])
#             return result

#         elif isinstance(data, str):
#             lines = data.strip().splitlines()
#             if not lines:
#                 return {"success": False, "summary": "No data to summarize.", "error": "Empty result provided."}
#             try:
#                 rows = ast.literal_eval(lines[0]) if lines else []
#                 if not rows:
#                     return {"success": False, "summary": "No data to summarize.", "error": "Empty result provided."}
#                 if isinstance(rows, list) and rows and isinstance(rows[0], (list, tuple)):
#                     columns = [f"col_{i}" for i in range(len(rows[0]))]
#                     df = pd.DataFrame(rows, columns=columns)
#                 else:
#                     df = pd.DataFrame(rows)
#                 id_columns = [col for col in df.columns if col.lower() in ['id', 'uuid'] or 'id' in col.lower()]
#                 df = df[[col for col in df.columns if col not in id_columns]]
#                 summary = [
#                     f"Total rows: {len(df)}",
#                     f"Columns: {', '.join(df.columns)}"
#                 ]
#                 if not df.empty:
#                     summary.append("Sample insights:")
#                     for _, row in df.head(5).iterrows():
#                         summary.append(f"- {', '.join(f'{col}: {val}' for col, val in row.items())}")
#                 result = {"success": True, "summary": "\n".join(summary)}
#                 logger.debug("Summarized result: %s", result["summary"])
#                 return result
#             except (ValueError, SyntaxError) as e:
#                 logger.error(f"Failed to parse raw string result: {e}")
#                 return {"success": False, "summary": "Unable to summarize due to invalid data format.", "error": str(e)}

#         else:
#             logger.error(f"Unsupported input type: {type(raw_result)}")
#             return {"success": False, "summary": "Unsupported input type.", "error": f"{type(raw_result)}"}

#     except Exception as e:
#         logger.error(f"summarize_result failed: {e}", exc_info=True)
#         return {"success": False, "summary": "Processing error.", "error": str(e)}

# # ----------------- CHART RENDERER -----------------
# def render_chart(data: List[Dict[str, Any]], chart_type: str, title: str, x_col: str = None, y_col: str = None, value_col: str = None) -> Dict[str, str]:
#     logger.debug("render_chart called with chart_type: %s, title: %s", chart_type, title)
#     start_time = time.perf_counter()
#     try:
#         if not data:
#             return {"error": "No data provided for chart", "summary": "Empty dataset.", "success": False}

#         df = pd.DataFrame(data)
#         id_columns = [col for col in df.columns if col.lower() in ['id', 'uuid'] or 'id' in col.lower()]
#         df = df[[col for col in df.columns if col not in id_columns]]

#         valid_chart_types = ["bar", "horizontal_bar", "line", "scatter", "regression", "hist", "boxplot", "violin", "pie", "heatmap", "pairplot"]
#         if chart_type not in valid_chart_types:
#             return {"error": f"Invalid chart type: {chart_type}", "summary": "Invalid chart type.", "success": False}

#         fig, ax = None, None
#         if chart_type != "pairplot":
#             fig, ax = plt.subplots(figsize=(10, 6))

#         summary = f"The {chart_type} chart '{title}' visualizes {len(df)} data points. "
#         if x_col and y_col:
#             summary += f"It shows the relationship between {x_col} and {y_col}. "

#         try:
#             if chart_type == "bar":
#                 sns.barplot(data=df, x=x_col, y=y_col, ax=ax)
#             elif chart_type == "horizontal_bar":
#                 sns.barplot(data=df, x=y_col, y=x_col, ax=ax)
#             elif chart_type == "line":
#                 sns.lineplot(data=df, x=x_col, y=y_col, ax=ax)
#             elif chart_type == "scatter":
#                 sns.scatterplot(data=df, x=x_col, y=y_col, ax=ax)
#             elif chart_type == "regression":
#                 sns.regplot(data=df, x=x_col, y=y_col, ax=ax)
#             elif chart_type == "hist":
#                 sns.histplot(data=df, x=x_col, y=y_col, ax=ax)
#             elif chart_type == "boxplot":
#                 sns.boxplot(data=df, x=x_col, y=y_col, ax=ax)
#             elif chart_type == "violin":
#                 sns.violinplot(data=df, x=x_col, y=y_col, ax=ax)
#             elif chart_type == "pie":
#                 fig, ax = plt.subplots(figsize=(8, 6))
#                 pie_data = df.groupby(x_col)[y_col].sum() if y_col else df[x_col].value_counts()
#                 ax.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%")
#                 summary = f"The pie chart '{title}' shows the distribution of {x_col}.\n{pie_data.to_string()}"
#             elif chart_type == "heatmap":
#                 if not (x_col and y_col and value_col):
#                     return {"error": "Heatmap requires x_col, y_col, and value_col.", "summary": "Missing columns.", "success": False}
#                 pivot_data = df.pivot_table(index=y_col, columns=x_col, values=value_col, aggfunc="sum", fill_value=0)
#                 sns.heatmap(pivot_data, annot=True, fmt=".1f", cmap="YlGnBu", ax=ax)
#             elif chart_type == "pairplot":
#                 g = sns.pairplot(df.select_dtypes(include="number"))
#                 g.fig.suptitle(title, fontsize=16, weight="bold")
#                 buf = io.BytesIO()
#                 g.savefig(buf, format="png")
#                 buf.seek(0)
#                 encoded = base64.b64encode(buf.read()).decode("utf-8")
#                 buf.close()
#                 plt.close(g.fig)
#                 os.makedirs("charts", exist_ok=True)
#                 file_name = f"chart_{uuid.uuid4().hex[:8]}.png"
#                 file_path = os.path.abspath(os.path.join("charts", file_name))
#                 with open(file_path, "wb") as f:
#                     f.write(base64.b64decode(encoded))
#                 logger.info("Chart generated: %s in %.3f seconds", file_name, time.perf_counter() - start_time)
#                 return {"title": title, "image_base64": f"data:image/png;base64,{encoded}", "file_path": file_path, "summary": summary, "success": True}

#             ax.set_title(title)
#             if x_col:
#                 ax.set_xlabel(x_col)
#             if y_col:
#                 ax.set_ylabel(y_col)
#             plt.tight_layout()

#             buf = io.BytesIO()
#             plt.savefig(buf, format="png")
#             buf.seek(0)
#             encoded = base64.b64encode(buf.read()).decode("utf-8")
#             buf.close()
#             plt.close(fig)

#             os.makedirs("charts", exist_ok=True)
#             file_name = f"chart_{uuid.uuid4().hex[:8]}.png"
#             file_path = os.path.abspath(os.path.join("charts", file_name))
#             with open(file_path, "wb") as f:
#                 f.write(base64.b64decode(encoded))

#             logger.info("Chart generated: %s in %.3f seconds", file_name, time.perf_counter() - start_time)
#             return {"title": title, "image_base64": f"data:image/png;base64,{encoded}", "file_path": file_path, "summary": summary, "success": True}

#         except Exception as e:
#             logger.error(f"Plotting failed: {e}", exc_info=True)
#             return {"error": f"Chart plotting error: {e}", "summary": "Plotting failed.", "success": False}

#     except Exception as e:
#         logger.error(f"Chart rendering failed: {e}", exc_info=True)
#         return {"error": f"Chart rendering failed: {e}", "summary": "Rendering error.", "success": False}

# # ----------------- FIXED generate_chart -----------------
# @mcp.tool()
# def generate_chart(
#     data: List[Dict[str, Any]] | str,
#     chart_type: str,
#     title: str = "Chart",
#     x_col: str = None,
#     y_col: str = None,
#     value_col: str = None
# ) -> Dict[str, str]:
#     """Generate a single chart. Accepts List[Dict] or JSON string."""
#     logger.debug("generate_chart called with data type: %s, chart_type: %s, title: %s", type(data), chart_type, title)
#     logger.debug("Raw data input: %s", data)
#     logger.debug(f"[DEBUG] RAW DATA TYPE: {type(data)} | VALUE: {repr(data)}")

#     try:
#         # ✅ Robust parsing (handles JSON or Python literals)
#         if isinstance(data, str):
#             try:
#                 data = json.loads(data)
#             except json.JSONDecodeError:
#                 try:
#                     data = ast.literal_eval(data)
#                 except (ValueError, SyntaxError):
#                     logger.error("Invalid data format for chart.")
#                     return {
#                         "error": "Invalid data format: must be JSON or list of dicts.",
#                         "summary": "Unable to generate chart due to invalid input.",
#                         "success": False,
#                     }

#         if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
#             return {
#                 "error": f"Data must be a List[Dict], got {type(data)}",
#                 "summary": "Invalid data format.",
#                 "success": False,
#             }

#         return render_chart(data, chart_type, title, x_col, y_col, value_col)

#     except Exception as e:
#         logger.error(f"generate_chart failed: {e}", exc_info=True)
#         return {"error": f"Chart generation error: {e}", "summary": "Processing error.", "success": False}

# # ----------------- FIXED generate_charts -----------------
# @mcp.tool()
# def generate_charts(charts: List[Dict[str, Any]]) -> List[Dict[str, str]]:
#     """Generate multiple charts in one call."""
#     logger.debug("generate_charts called with %d charts", len(charts))
#     logger.debug(f"[DEBUG] RAW DATA TYPE: {type(data)} | VALUE: {repr(data)}")
#     results = []
#     for chart in charts:
#         data = chart.get("data", [])
#         try:
#             if isinstance(data, str):
#                 try:
#                     data = json.loads(data)
#                 except json.JSONDecodeError:
#                     try:
#                         data = ast.literal_eval(data)
#                     except (ValueError, SyntaxError):
#                         results.append({
#                             "error": "Invalid data format for chart.",
#                             "summary": "Invalid chart input format.",
#                             "success": False,
#                         })
#                         continue

#             if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
#                 results.append({
#                     "error": f"Data must be a List[Dict], got {type(data)}",
#                     "summary": "Invalid data format.",
#                     "success": False,
#                 })
#                 continue

#             result = render_chart(
#                 data=data,
#                 chart_type=chart.get("chart_type"),
#                 title=chart.get("title", "Chart"),
#                 x_col=chart.get("x_col"),
#                 y_col=chart.get("y_col"),
#                 value_col=chart.get("value_col"),
#             )
#             results.append(result)

#         except Exception as e:
#             logger.error(f"generate_charts failed for one chart: {e}", exc_info=True)
#             results.append({"error": str(e), "summary": "Chart processing error.", "success": False})

#     return results

# # ----------------- MAIN ENTRY -----------------
# if __name__ == "__main__":
#     logger.info("Starting test server")
#     mcp.run(transport="stdio")



import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import matplotlib.pyplot as plt
import io
import base64
import seaborn as sns
import pandas as pd
from typing import List, Dict, Any
import uuid
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.FileHandler("app.log")]
)
logger = logging.getLogger("Server")

load_dotenv()
logger.debug("Loaded environment variables")
mcp = FastMCP("sql")
logger.debug("FastMCP initialized")

mcp = FastMCP("sql")

# @mcp.tool()
# def summarize_result(raw_result: str) -> str:
#     """
#     Summarize raw SQL query result into business-friendly language.
        
#     Args:
#     raw_result - String of raw data from database.
#     """
#     lines = raw_result.strip().splitlines()
#     if not lines:
#         return "No data to summarize."
    
#     summary = []
#     summary.append(f"Total lines: {len(lines)}")
#     columns = lines[1].replace("Columns: ", "").split(", ") if "Columns:" in lines[1] else []
#     summary.append(f"Columns: {', '.join(columns)}")
#     samples = [line for line in lines if ":" in line]
#     if samples:
#         summary.append("Sample insights:")
#         for s in samples[1:5]:
#             summary.append(f"- {s}")
    
#     return "\n".join(summary)
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
                # "image_base64": f"data:image/png;base64,{encoded}",
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
            # "image_base64": f"data:image/png;base64,{encoded}",
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
    """
    Generate a single visualization chart from structured data.

    This tool converts tabular or aggregated data into a chart visualization based
    on the specified chart type. It uses the internal `render_chart()` utility
    to render and format the chart, returning a structured representation
    (e.g., JSON or base64) suitable for UI display.

    It is primarily used after database query execution (e.g., payroll summaries,
    defect counts, threshold trends) to visually present insights.

    Args:
        data (List[Dict[str, Any]]):
            A list of dictionaries representing the dataset to visualize.
            Each dictionary should map column names to their values.
            Example:
                [
                    {"month": "Jan", "revenue": 12000},
                    {"month": "Feb", "revenue": 15000}
                ]

        chart_type (str):
            The type of chart to generate. Supported values include:
            - `"bar"`: Compare categories (e.g., defects by status)
            - `"line"`: Show trends or time-based metrics
            - `"pie"`: Display proportional distributions
            - `"stacked_bar"`: Compare grouped subcategories
            - `"histogram"`: Show data distribution or frequency

        title (str, optional):
            The chart title. Defaults to `"Chart"`.
            Used in UI captions or chart headers.

        x_col (str, optional):
            Column name for the X-axis. Typically categorical or date-based.

        y_col (str, optional):
            Column name for the Y-axis. Typically numeric or aggregated.

        value_col (str, optional):
            Column used for representing the key numeric value when the chart type requires a single primary metric (e.g., pie chart slices).

    Returns:
        Dict[str, Any]:
            A dictionary containing the rendered chart data or metadata, including:
            - `"chart_type"`: Type of chart created
            - `"title"`: Chart title
            - `"rendered_chart"`: Visualization payload (e.g., base64, HTML, or JSON)
            - `"config"`: Optional configuration details used during rendering

    Example:
        ```python
        data = [
            {"month": "Jan", "revenue": 12000},
            {"month": "Feb", "revenue": 15000}
        ]

        chart = generate_chart(
            data=data,
            chart_type="bar",
            title="Monthly Revenue",
            x_col="month",
            y_col="revenue"
        )
        ```
        This produces a bar chart titled "Monthly Revenue" showing revenue by month.

    Notes:
        - Ensure the dataset includes meaningful X and Y columns.
        - The tool is read-only and non-destructive.
        - If fewer than 10 data points are provided, a summary may be preferable to visualization.
    """
    return render_chart(data, chart_type, title, x_col, y_col, value_col)

@mcp.tool()
def generate_charts(charts: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Generate multiple visualization charts in a single call.

    This tool allows the creation of multiple charts (e.g., bar, line, pie)
    from independent datasets, typically used for dashboards or comparative
    analysis. It accepts a list of chart configurations, each describing
    the data and chart parameters required by `render_chart()`.

    The charts are rendered sequentially, and the resulting visualizations
    are returned as a list of serialized chart representations.

    Args:
        charts (List[Dict[str, Any]]):
            A list of chart configurations, where each item is a dictionary
            containing the following keys:

            - **data** (`List[Dict[str, Any]]`):  
              The dataset to visualize. Each dictionary maps column names to
              values, for example:  
              `[{"month": "Jan", "revenue": 12000}, {"month": "Feb", "revenue": 15000}]`

            - **chart_type** (`str`):  
              The type of chart to generate. Supported values include:
              `"bar"`, `"line"`, `"pie"`, `"stacked_bar"`, and `"histogram"`.

            - **title** (`str`, optional):  
              A descriptive title for the chart. Defaults to `"Chart"`.

            - **x_col** (`str`, optional):  
              Column name to use for the X-axis (categorical or date-based).

            - **y_col** (`str`, optional):  
              Column name to use for the Y-axis (typically numeric).

            - **value_col** (`str`, optional):  
              Column name used as the primary value for certain chart types.

    Returns:
        List[Dict[str, str]]:
            A list of chart render outputs. Each item corresponds to the
            result of one chart, typically containing serialized visualization.

    Example:
        ```python
        charts = [
            {
                "data": [{"month": "Jan", "revenue": 12000}, {"month": "Feb", "revenue": 15000}],
                "chart_type": "bar",
                "title": "Monthly Revenue",
                "x_col": "month",
                "y_col": "revenue"
            },
            {
                "data": [{"status": "Open", "count": 5}, {"status": "Closed", "count": 8}],
                "chart_type": "pie",
                "title": "Defect Status Distribution",
                "x_col": "status",
                "value_col": "count"
            }
        ]

        results = generate_charts(charts)
        ```

        This would produce two charts — a bar chart and a pie chart —
        and return their rendered outputs as a list.

    Notes:
        - Use this tool when multiple related visualizations are requested.
        - Each chart configuration is processed independently.
        - The function is read-only and does not alter input data.
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
    logger.info("Starting test server")
    mcp.run(transport="stdio")
