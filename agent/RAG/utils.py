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


import os
from typing import Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Embedding model: use Gemini embedding if key is available, else local HuggingFace
if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
    Settings.embed_model = GoogleGenAIEmbedding(
        model="gemini-embedding-001",
        embedding_config=EmbedContentConfig(
            output_dimensionality=768
        )
    )
else:
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

# LLM: use Groq if available, else Google GenAI
if os.getenv("GROQ_API_KEY"):
    from llama_index.llms.groq import Groq
    Settings.llm = Groq(
        model="openai/gpt-oss-120b",
        api_key=os.environ["GROQ_API_KEY"],
        temperature=0
    )
elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
    from llama_index.llms.google_genai import GoogleGenAI
    Settings.llm = GoogleGenAI(
        model="models/gemini-2.5-flash",
        temperature=0
    )


# client = QdrantClient(path="./data/qdrant_data")
# aclient = AsyncQdrantClient(path="./data/qdrant_data")

aclient = AsyncQdrantClient(":memory:")
# create our vector store with hybrid indexing enabled
# batch_size controls how many nodes are encoded with sparse vectors at once
vector_store = QdrantVectorStore(
    "FAQ",
    # client=client,
    aclient=aclient,
    enable_hybrid=True,
    fastembed_sparse_model="Qdrant/bm25",
    batch_size=20,
)

Settings.chunk_size = 108
