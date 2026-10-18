from langchain.tools import tool
from sqlalchemy import text
from sqlalchemy import create_engine
from typing import List
import asyncio

from agent.supportAgent import support_agent, get_support_agent
from agent.salesAgent import sales_agent, get_sales_agent

@tool
async def sales_agent_tool(query:str|List[str]):
    """Sales Agent will Handle Sales Related queries"""
    print("executing sales agent tool")
    if isinstance(query, list):
        query = " ".join(query)
        print("Query List to str")
    try:
        current_agent = get_sales_agent()
        result = await current_agent.ainvoke({
            "messages":[
                "user",query
            ]
        })

        content = result["messages"][-1].content
        return content if isinstance(content, str) and content else "No support result found."
    except Exception as e:
        return {"status":"failed","msg":e}

@tool
async def support_agent_tool(query:str|List[str]):
    """Sales Agent will Handle support Related queries"""
    print("executing support agent tool")
    if isinstance(query, list):
        query = " ".join(query)
        print("Query List to str")
    try:
        current_agent = get_support_agent()
        result = await current_agent.ainvoke({
            "messages":[
                "user",query
            ]
        })

        content = result["messages"][-1].content
        return content if isinstance(content, str) and content else "No support result found."
    except Exception as e:
        return {"status":"failed","msg":e}


engine = create_engine("sqlite:///./customers.db")

@tool
async def get_details(user_name: str, phone_number: str, needed_response : List[str]):
    """Retrieve customer details using username and phone number. needed_response - only needed response infos like provent information like email pil detection """

    query = text("""
        SELECT *
        FROM customers
        WHERE "name" = :name
          AND "phone_number" = :phone_number
    """)

    with engine.connect() as conn:
        result = conn.execute(
            query,
            {
                "name": user_name,
                "phone_number": phone_number
            }
        )

        rows = result.mappings().all()

        results = [dict(row) for row in rows]

        output = []

        for r in results:
            
            output.append({res:r[res] for res in needed_response})
        return output

@tool
async def get_columns_list(user_name:str,phone_number:str):
    """columns details get help to send to needed response to get_details tools """
    query = text("""
            SELECT *
            FROM customers
            WHERE "name" = :name
              AND "phone_number" = :phone_number
        """)
    
    with engine.connect() as conn:
        result = conn.execute(
                query,
                {
                    "name": user_name,
                    "phone_number": phone_number
                }
            )
    
        rows = result.mappings().all()
    
        results = [dict(row) for row in rows]

        return results[0].keys()



@tool
async def invoice_generator(user_name:str,price:str,product:str,date:str):
    """Invoice for the purchased product if user wants"""
    return f"""
Hi {user_name} , Recently You purchase {product} for {price} at {date}, Its a Receipt for that, Thank you Have a nice day

"""

async def main():
  result = await get_details.ainvoke({
        "user_name": 'Arun Kumar', 
        "phone_number": '+1-202-555-0100',
        "needed_response":["item","price"]
    })
  print(result)
    


if __name__ == "__main__":
    asyncio.run(
        main()
    )
    