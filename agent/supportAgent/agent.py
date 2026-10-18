from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from agent.supportAgent.tools import get_schema_,get_sql_collections,execute_sql,datetime_now
from agent.supportAgent.prompt import system_prompt_support
from agent.llm_models import google_llm, groq_llm, get_active_llm
from agent.RAG import retrieve_from_vectorDB

from langchain.agents.middleware import (
    ToolCallLimitMiddleware,
    ModelCallLimitMiddleware,
)

from dotenv import load_dotenv
import os

load_dotenv()

def get_support_agent():
    return create_agent(
        model=get_active_llm(),
        tools=[
            get_schema_,
            get_sql_collections,
            execute_sql,
            retrieve_from_vectorDB,
            datetime_now
        ],
        system_prompt=system_prompt_support,
    )

support_agent = get_support_agent()