#!/usr/bin/env python
"""
Run script for the Scientific Agent.
This script should be run from the root directory.
"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_core.globals import set_debug # Import the correct function

# Enable LangChain debug mode
set_debug(True) # Use the imported function

# Load environment variables from .env file
load_dotenv()

# Import after loading environment variables
from scientifc_agent.models import CoreAPIWrapper
from scientifc_agent.agent import app
from scientifc_agent.utils import print_stream

# Set the API key for CoreAPIWrapper from environment
core_api_key_env = os.environ.get("CORE_API_KEY") 
if not core_api_key_env:
    raise ValueError("CORE_API_KEY environment variable is not set. Please set it in your .env file.")
CoreAPIWrapper.api_key = core_api_key_env


async def main():
    """Run the scientific agent with a user query."""
    user_query = input("Enter your research query: ")
    if not user_query:
        user_query = "Find recent papers (2023-2024) about large language models for scientific research"
        print(f"Using default query: {user_query}")
    
    print("\n" + "-" * 50 + "\n")
    
    # Run the agent
    final_state_message = await print_stream(app, user_query)
    
    print("\n" + "-" * 50 + "\n")
    print("Final output message content:")
    if final_state_message:
        if hasattr(final_state_message, 'content'):
            print(final_state_message.content)
        else:
            print(f"Final message is of type {type(final_state_message)} and has no 'content' attribute. Full message: {final_state_message}")
    else:
        print("No answer received")

if __name__ == "__main__":
    asyncio.run(main())