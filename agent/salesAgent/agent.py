from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from agent.salesAgent.prompt import system_prompt_sales
from agent.llm_models import google_llm, groq_llm, get_active_llm
from agent.RAG import retrieve_from_vectorDB
from agent.supportAgent import get_schema_,get_sql_collections,execute_sql,datetime_now
from langchain.agents.middleware import (
    ToolCallLimitMiddleware,
    ModelCallLimitMiddleware,
)

from dotenv import load_dotenv
import os

load_dotenv()

def get_sales_agent():
    return create_agent(
        model=get_active_llm(),
        tools=[
            get_schema_,
            get_sql_collections,
            execute_sql,
            retrieve_from_vectorDB,
            datetime_now
        ],
        system_prompt=system_prompt_sales,
    )

sales_agent = get_sales_agent()