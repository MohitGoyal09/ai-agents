# Scientific Agent

A modular scientific research agent built with LangGraph that can search for papers, download and analyze them, and provide detailed answers to research queries.

## Structure

The agent is organized into the following modules:

- `agent.py` - Main agent workflow and graph construction
- `models.py` - Data models and state definitions
- `nodes.py` - Workflow node functions
- `prompts.py` - Prompt templates
- `tools.py` - Tool definitions and implementations
- `utils.py` - Utility functions
- `example.py` - Example usage

## Setup

1. Install dependencies:

```bash
pip install langchain langchain-community langchain-google-genai langgraph langsmith pdfplumber python-dotenv
```

Or use the requirements.txt file:

```bash
pip install -r scientifc_agent/requirements.txt
```

2. Set up environment variables:

Create a `.env` file with the following variables:

```
GOOGLE_API_KEY=your_google_api_key
CORE_API_KEY=your_core_api_key
```

## Usage

### Running the Agent

The easiest way to run the agent is using the provided run script:

```bash
python run_scientific_agent.py
```

This will prompt you to enter a research query and then run the agent with that query.

### Basic Usage in Code

```python
import asyncio
import os
from dotenv import load_dotenv

# Set up environment variables
os.environ["GOOGLE_API_KEY"] = "your_google_api_key"
os.environ["CORE_API_KEY"] = "your_core_api_key"

# Import after setting environment variables
from scientifc_agent.models import CoreAPIWrapper
from scientifc_agent.agent import app
from scientifc_agent.utils import print_stream

# Set the API key for CoreAPIWrapper
CoreAPIWrapper.api_key = os.environ["CORE_API_KEY"]

async def run_query(query):
    result = await print_stream(app, query)
    return result

# Run the agent with a query
query = "Find recent papers (2023-2024) about large language models for scientific research"
asyncio.run(run_query(query))
```

## Features

- Decision making to determine if research is needed
- Step-by-step planning for complex research tasks
- Paper search using the CORE API
- PDF downloading and text extraction
- Human feedback integration
- Quality judgment of final answers
- Streaming results display

## Customization

You can customize the agent by:

1. Modifying prompts in `prompts.py`
2. Adding new tools in `tools.py`
3. Extending the workflow in `agent.py`
4. Changing the models or LLM providers in `nodes.py`

## API Keys

The agent uses the following API keys:

- Google Gemini API for LLM capabilities
- CORE API for academic paper searches

Make sure to set these in your environment variables or `.env` file.
