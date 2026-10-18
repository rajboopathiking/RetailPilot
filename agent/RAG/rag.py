from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    StorageContext,
    Settings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.groq import Groq
from llama_index.core import Document,SimpleDirectoryReader
from qdrant_client import QdrantClient,AsyncQdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore

from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from google.genai.types import EmbedContentConfig

import pandas as pd
from agent.RAG.ingestion_data import kb
from typing import Any,Optional

class RAG:
  def __init__(self,Settings):
    self.settings = Settings
    self.vector_store = QdrantVectorStore(
      collection_name="FAQ",
      aclient=AsyncQdrantClient("./data/qdrant"),
      enable_hybrid=True,
      fastembed_sparse_model="Qdrant/bm25",
    )
    self.vector_index = None
    self.desc = """ 
    all asynchoronous 
    1) query - to enquire pipeline
    2) ingestion - ingestion pipeling
    3) retrieve - retrieve pipeline with score """

  async def ingestion(self, dir: str = "data/retailpilot_case/knowledge"):
    documents = SimpleDirectoryReader(
        input_dir=dir,
        recursive=True,
        required_exts=[".md"]
    ).load_data()


    for index, doc in enumerate(documents):
        doc.metadata.update(kb.iloc[index, :3].to_dict())

    splitter = SentenceSplitter(
        separator=" ",
        chunk_size=100,
        chunk_overlap=50
    )

    split_docs = splitter.get_nodes_from_documents(documents)

    storage_context = StorageContext.from_defaults(
        vector_store=self.vector_store
    )

    vector_index = VectorStoreIndex(
        nodes=split_docs,
        embed_model=self.settings.embed_model,
        storage_context=storage_context,
        use_async=True
    )

    self.vector_index = vector_index

    return vector_index

  async def query(self,query:str,vector_index:Optional[Any]=None,top_k:int=3):
    if vector_index:
      self.query_engine = vector_index.as_query_engine(llm=Settings.llm,similarity_top_k=top_k,sparse_top_k=12, vector_store_query_mode="hybrid")
    else:
      self.query_engine = self.vector_index.as_query_engine(llm=Settings.llm,similarity_top_k=top_k,sparse_top_k=12, vector_store_query_mode="hybrid")

    response = await self.query_engine.aquery(query)
    return response.response

  async def retrieve(self,query:str,vector_index:Optional[Any]=None,top_k:int=3):
    if vector_index:
      self.query_engine = vector_index.as_query_engine(llm=Settings.llm,similarity_top_k=top_k,sparse_top_k=12, vector_store_query_mode="hybrid")
    else:
      self.query_engine = self.vector_index.as_query_engine(llm=Settings.llm,similarity_top_k=top_k,sparse_top_k=12, vector_store_query_mode="hybrid")

    response = await self.query_engine.aretrieve(query)
    return response
    
    