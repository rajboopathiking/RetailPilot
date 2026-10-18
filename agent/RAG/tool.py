from agent.RAG.rag import RAG,Settings

from langchain.tools import tool

from agent.RAG.utils import Settings

rag = RAG(Settings=Settings)

@tool
async def retrieve_from_vectorDB(query:str):
  """Its llama-index based retieves return nodes in that node contain text for info"""
  print("executing rag_tool ...")
  try:
    rag = RAG(Settings=Settings)
    if not rag.vector_index:
      await rag.ingestion()
    return await rag.retrieve(query=query)
  except Exception as e:
    return {"status":"failed","msg":e}

