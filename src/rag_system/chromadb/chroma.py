import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict

class ChromaVectorStore:
    def __init__(self, persist_directory: str = "./chroma_db", collection_name: str = "rag_docs"):
        self.client = chromadb.Client(Settings(persist_directory=persist_directory))
        self.collection = self.client.get_or_create_collection(collection_name)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    def add_documents(self, docs: List[Dict]):
        # docs: List of {"id": str, "text": str}
        texts = [doc["text"] for doc in docs]
        ids = [doc["id"] for doc in docs]
        embeddings = self.embedder.encode(texts).tolist()
        self.collection.add(documents=texts, ids=ids, embeddings=embeddings)

    def query(self, query_text: str, top_k: int = 5):
        query_emb = self.embedder.encode([query_text]).tolist()[0]
        results = self.collection.query(query_embeddings=[query_emb], n_results=top_k)
        return results
