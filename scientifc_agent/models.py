"""
Data models and state definitions for the scientific agent.
"""

import json
import urllib3
import time
from dataclasses import dataclass, field
from pydantic import BaseModel, Field , validator
from typing import ClassVar, Sequence, Optional, Dict, Any , List, Union
from langchain_core.messages import BaseMessage

class SearchPapersInput(BaseModel):
    """Input object to search papers with the CORE API."""
    query: str = Field(description="The query to search for on the selected archive.")
    max_papers: int = Field(description="The maximum number of papers to return. It's default to 1, but you can increase it up to 10 in case you need to perform a more comprehensive search.", default=1, ge=1, le=10)

class DecisionMakingOutput(BaseModel):
    """Output object of the decision making node."""
    requires_research: bool = Field(description="Whether the user query requires research or not.")
    answer: Optional[str] = Field(default=None, description="The answer to the user query. It should be None if the user query requires research, otherwise it should be a direct answer to the user query.")

class JudgeOutput(BaseModel):
    """Output object of the judge node."""
    is_good_answer: bool = Field(description="Whether the answer is good or not.")
    feedback: Optional[str] = Field(default=None, description="Detailed feedback about why the answer is not good. It should be None if the answer is good.")


class CoreAPIWrapper(BaseModel):
    """Simple wrapper around the CORE API."""
    base_url: ClassVar[str] = "https://api.core.ac.uk/v3"
    api_key: ClassVar[str] = None
    top_k_results: int = Field(description="Top K results obtained by running a query on CORE", default=1)

    def _get_search_response(self, query: str) -> Dict[str, Any]:
        http = urllib3.PoolManager()
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = http.request(
                    'GET',
                    f"{self.base_url}/search/outputs",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    fields={"q": query, "limit": self.top_k_results}
                )
                if 200 <= response.status < 300:
                    try:
                        return json.loads(response.data.decode('utf-8'))
                    except json.JSONDecodeError:
                        if attempt < max_retries - 1:
                            time.sleep(2 ** (attempt + 2))
                            continue
                        return {"results": [], "error": "Failed to parse API response"}
                elif attempt < max_retries - 1:
                    time.sleep(2 ** (attempt + 2))
                else:
                    return {"results": [], "error": f"API error: {response.status} - {response.data.decode('utf-8', errors='replace')}"}
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** (attempt + 2))
                else:
                    return {"results": [], "error": f"Connection error: {str(e)}"}
        return {"results": [], "error": "Maximum retries reached"}

    def search(self, query: str) -> Union[List[Dict[str, Any]], str]: # Return structured data or an error string
        response_data = self._get_search_response(query)
        
        if "error" in response_data:
            return f"Error searching for papers: {response_data['error']}" # Return error string
            
        results = response_data.get("results", [])
        if not results:
            return "No relevant results were found" # Return info string

        # Process results into a list of dictionaries
        docs_data = []
        for result in results:
            published_date_str = str(result.get('publishedDate') or result.get('yearPublished', ''))
            
            authors_list = result.get('authors', [])
            authors_names = []
            if isinstance(authors_list, list):
                for item in authors_list:
                    if isinstance(item, dict) and 'name' in item:
                        authors_names.append(str(item['name']))
            authors_str = ' and '.join(authors_names) if authors_names else 'Unknown'
            
            abstract = str(result.get('abstract', 'No abstract available'))
            
            urls_data = result.get('sourceFulltextUrls') or result.get('downloadUrl')
            urls_str = ""
            if isinstance(urls_data, list):
                urls_str = ', '.join([str(u) for u in urls_data])
            elif isinstance(urls_data, str):
                urls_str = urls_data
            else:
                urls_str = 'No URL available'
            
            docs_data.append({
                "id": str(result.get('id', 'Unknown ID')),
                "title": str(result.get('title', 'Untitled')),
                "published_date": published_date_str,
                "authors": authors_str,
                "abstract": abstract, # Pass full abstract for now; can be truncated here too
                "urls": urls_str,
            })
        return docs_data

@dataclass
class AgentState:
    """State for the scientific agent workflow."""
    requires_research: bool = False
    num_feedback_requests: int = 0
    is_good_answer: bool = False
    messages: Sequence[BaseMessage] = field(default_factory=list) 


class PlanStep(BaseModel):
    """A single step in a multi-step plan."""
    step: int = Field(description="The step number, starting from 1.")
    tool: str = Field(description="The name of the tool to be used for this step (e.g., 'search-papers', 'download-paper', 'ask-human-feedback'), or 'null' if no tool is executed by the AI for this step (e.g., a review step).")
    # Allow arguments to be a string that can be parsed as JSON, or a dict directly.
    # Union[Dict[str, Any], str] was causing issues with Pydantic v2's strictness with default_factory
    # Using a pre-validator is more robust for this case.
    arguments: Dict[str, Any] = Field(default_factory=dict, description="A dictionary of arguments for the tool. Should be an empty dictionary if tool is 'null'.")
    description: str = Field(description="A natural language description of what this step aims to achieve.")

    @validator("arguments", pre=True, always=True)
    def parse_arguments_string(cls, v: Any) -> Any:
        if isinstance(v, str):
            if v.strip().lower() == "null" or not v.strip(): # Handle "null" string or empty string
                return {}
            try:
                loaded_json = json.loads(v)
                if not isinstance(loaded_json, dict):
                    # If it parses but isn't a dict (e.g. "[]" or a number as string)
                    raise ValueError("Parsed JSON string for arguments is not a dictionary.")
                return loaded_json
            except json.JSONDecodeError:
                # If it's a string but not valid JSON, raise error or attempt to interpret differently
                # For now, strict: must be valid JSON string if it's a string.
                raise ValueError(f"arguments field, if string ('{v}'), must be a valid JSON string representing a dictionary, or 'null'.")
        # If it's already a dictionary or other non-string type Pydantic can handle for Dict[str, Any]
        elif isinstance(v, dict):
             return v
        # If it's something else entirely, Pydantic will raise its own error, or we can be more specific
        # For example, if it's None and default_factory should kick in, but Pydantic might pass None here.
        elif v is None: # Explicitly handle None to ensure default_factory or empty dict.
            return {}
        else: # If not str or dict or None, let Pydantic try, or raise.
            # This path is less likely if the LLM produces a string or a (malformed) structure.
            # For robustness, we could raise a ValueError here too if v is not a dict.
            # However, Pydantic's default validation for Dict[str, Any] will catch other invalid types.
            return v

class PlanOutput(BaseModel):
    """Structured output for the planning node, containing a list of plan steps."""
    plan: List[PlanStep] = Field(description="The list of steps in the research plan.")


@dataclass
class AgentState:
    """State for the scientific agent workflow."""
    requires_research: bool = False
    num_feedback_requests: int = 0
    is_good_answer: bool = False
    messages: Sequence[BaseMessage] = field(default_factory=list)