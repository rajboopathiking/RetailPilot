from agent.graph import app

async def chat_resonse(query:str,thread_id:str):

  res = await app.ainvoke({
    "messages":[("user",query)]
  },config={
    # "recursion_limit": 6,
    "configurable":{
      "thread_id":thread_id
    }
  })

  return res["messages"][-1].content

async def chat_resonse_stream(query:str,thread_id:str):

  res = await app.astream({
    "messages":[("user",query)]
  },config={
    # "recursion_limit": 6,
    "configurable":{
      "thread_id":thread_id
    }
  })

  return res["messages"][-1].content