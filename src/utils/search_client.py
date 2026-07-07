import traceback
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

from ddgs import DDGS
from src.utils.logger import log_event

def search_duckduckgo(query: str, max_results: int = 5) -> str:
    """
    Queries DuckDuckGo Search and formats the results as a string.
    """
    if not query or not query.strip():
        return ""
        
    log_event("Search Client", f"Querying DuckDuckGo search for: '{query}'")
    try:
        results_str = []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=max_results)
                if results:
                    for i, r in enumerate(results):
                        title = r.get("title", "No Title")
                        url = r.get("href", "")
                        snippet = r.get("body", "")
                        results_str.append(f"Source {i+1}:\nTitle: {title}\nURL: {url}\nSnippet: {snippet}\n")
        
        if results_str:
            return "DuckDuckGo Grounding Sources:\n\n" + "\n".join(results_str)
        return "DuckDuckGo Grounding Sources: No results found."
    except Exception as e:
        log_event("Search Client", f"DuckDuckGo search error: {str(e)}")
        # Return empty context gracefully instead of crashing
        return f"DuckDuckGo Grounding Sources: Error retrieving search results ({str(e)})."