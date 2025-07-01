from src.rag_system.chromadb.chroma import ChromaVectorStore
from typing import List

# Placeholder LLM call functions
def call_ollama(prompt: str, lang: str) -> str:
    # TODO: Implement actual Ollama API call
    return f"[Ollama-{lang}] {prompt}"

def call_gemini(prompt: str, lang: str) -> str:
    # TODO: Implement actual Gemini API call
    return f"[Gemini-{lang}] {prompt}"

class RAGService:
    def __init__(self):
        self.vector_store = ChromaVectorStore()

    def answer_question(self, query: str, model: str = "ollama", lang: str = "en") -> str:
        # Retrieve relevant docs
        results = self.vector_store.query(query)
        context = "\n".join(results.get("documents", [[]])[0]) if results.get("documents") else ""
        # Compose prompt
        prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer in {lang.upper()}:"
        # Call selected LLM
        if model == "ollama":
            return call_ollama(prompt, lang)
        elif model == "gemini":
            return call_gemini(prompt, lang)
        else:
            return "Model not supported."
