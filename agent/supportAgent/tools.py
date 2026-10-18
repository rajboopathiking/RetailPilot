from langchain.tools import tool
from sqlalchemy import create_engine,text

engine = create_engine(
"sqlite:///data/retailpilot_case/retailpilot.db"
)

@tool
async def get_sql_collections():
  """get an sql collection names from db """
  print("executing get sql collections tool")
  try:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';")
        )
        response = []

        for row in result:
            response.append(row[0])
    return response
  except Exception as e:
    return {"status":"failed","msg":e}


from datetime import datetime
from datetime import timezone,timedelta

@tool
async def datetime_now():
  """Find a date and time now in india and utc"""
  print("executing datetime now tool")
  try:
    utc = datetime.now()
    ist = utc+timedelta(hours=5,minutes=30)
    return {"indian":ist,
            "global":utc}
  except Exception as e:
    return {"status":"failed","msg":e}




@tool
async def get_schema_(collection_name : str):
  """  get_schema details based on collection name"""
  print("executing get_schema tool")
  try:
    with engine.begin() as conn:
      results = conn.execute(
        text(f"PRAGMA table_info({collection_name})"),
      )
      response = []
      for row in results:
        response.append(f"{row[1]} : {row[2]}")
    return response
  except Exception as e:
    return {"status":"failed","msg":e}

import json

def normalize_tool_result(result):
    if result is None:
        return "No data found."

    if isinstance(result, str):
        return result if result.strip() else "No data found."

    if isinstance(result, list) and not result:
        return "No matching records found."

    return json.dumps(result, default=str)


import json
from sqlalchemy import text
from langchain_core.tools import tool

@tool
async def execute_sql(query: str) -> str:
    """Execute read-only SQL SELECT queries and return JSON."""

    try:
        query = query.strip()

        if not query.upper().startswith("SELECT"):
            return json.dumps({
                "status": "forbidden",
                "message": "Only SELECT queries are allowed."
            })

        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = [dict(row._mapping) for row in result.fetchall()]

        return json.dumps({
            "status": "success",
            "data": rows
        }, default=str)

    except Exception as e:
        return json.dumps({
            "status": "failed",
            "message": str(e)
        })
