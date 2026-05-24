from llama_index.core import VectorStoreIndex, Document
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from infrastructure.qdrant_store import qdrant, aqdrant # <--- IMPORT aqdrant
from infrastructure.logger import logger

# Connect LlamaIndex using BOTH sync and async clients
vector_store = QdrantVectorStore(
    client=qdrant, 
    aclient=aqdrant, # <--- ADD THIS LINE
    collection_name="internal_knowledge"
)

embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")

# ... [Keep the rest of the file exactly the same] ...

# Connect LlamaIndex directly to our existing Qdrant infrastructure
embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")

index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store, 
    embed_model=embed_model
)

async def query_internal_documents(query: str) -> str:
    """RAG tool for the Agent to search internal databases/documents."""
    logger.info(f"📚 [LlamaIndex] Searching internal docs for: '{query}'")
    
    # 1. Use a raw retriever instead of the query_engine
    retriever = index.as_retriever(similarity_top_k=3)
    nodes = await retriever.aretrieve(query)
    
    if not nodes:
        return "No relevant internal documents found."
        
    # 2. Return the raw text chunks so your 70B Supervisor can read them!
    return "\n\n".join([n.node.text for n in nodes])

# Utility to ingest files (Run this separately when adding PDFs/Txts)
def ingest_text_to_rag(text: str):
    doc = Document(text=text)
    index.insert(doc)
    logger.info("Inserted document into Qdrant Knowledge Base.")
