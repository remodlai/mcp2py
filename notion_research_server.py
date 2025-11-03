# notion_research_server.py
from fastmcp import FastMCP
from mcp2py import load
import dspy

# Initialize FastMCP
mcp = FastMCP("Notion Research Server")

# Load Notion and configure DSPy
notion = load("https://mcp.notion.com/mcp", auth="oauth")
dspy.configure(lm=dspy.LM("openai/gpt-4.1"))

class NotionResearcher(dspy.Signature):
    """Research assistant that searches Notion workspace."""
    query: str = dspy.InputField(desc="Research query")
    summary: str = dspy.OutputField(desc="Summary of findings")

researcher = dspy.ReAct(NotionResearcher, tools=notion.tools)

@mcp.tool()
def research_notion(query: str) -> str:
    """Research a topic by searching the Notion workspace.

    Args:
        query: The research question or topic to investigate

    Returns:
        A comprehensive summary of findings from Notion
    """
    result = researcher(query=query)
    return result.summary

@mcp.tool()
def get_notion_pages(search_term: str, limit: int = 5) -> dict:
    """Get a list of Notion pages matching a search term.

    Args:
        search_term: Term to search for
        limit: Maximum number of results (default: 5)

    Returns:
        Dictionary with search results
    """
    results = notion.notion_search(
        query=search_term,
        search_type="internal",
        limit=limit
    )
    return {"results": results, "count": limit}

# Run the server
if __name__ == "__main__":
    mcp.run()