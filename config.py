# config.py
import os
from pathlib import Path

# --- Configuration ---
PROJECT_ROOT = Path(__file__).parent

# Data
DATA_DIR = PROJECT_ROOT / "data" / "pdfs" # Place your PDFs here
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Embeddings
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
# FAISS
FAISS_INDEX_PATH = PROJECT_ROOT / "retrieval" / "faiss_index"
# BM25 (if persisted)
BM25_MODEL_PATH = PROJECT_ROOT / "retrieval" / "bm25_model.pkl"

# File where PDF's SHA Signature is saved
PDFS_SIGNATURE_PATH = PROJECT_ROOT / "retrieval" / "last_pdfs_signature.txt"

# Retriever
ENSEMBLE_WEIGHTS = [0.6, 0.4] # FAISS, BM25
RETRIEVER_K = 6 # Number of documents to retrieve

# LLM - Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # Set via environment variable
GROQ_MODEL_NAME = "llama-3.3-70b-versatile" # Or "Qwen/Qwen2.5-3B-Instruct" for local

# Prompts
SYSTEM_PROMPT = """You are a professional legal document assistant. Provide clear, accurate answers based on the provided legal documents.

Guidelines:
- Give direct, conversational responses that answer the user's question
- Reference specific sections and documents naturally within your answer
- If information isn't available in the documents, say so politely
- Use a helpful, professional but friendly tone
- Keep responses concise but complete
- Don't add unnecessary disclaimers or extra questions at the end
- If asked about the documents you know about, list their titles based on the provided context.
"""

INSTRUCTIONS_PROMPT = """
INSTRUCTIONS:
1. Find the answer to the question within the document.
2. Provide the response ONLY in the exact format below.
3. Extract the literal text for "Answer".
4. Extract only the numbers for 'Section' and 'Point'.
5. Use the filename for 'Document'.
6. If information is missing, write "Information not found" for that field.
7. Do not add any other text, explanations, or markdown.

Format:
Answer: [Exact text from document]
Section: [Section number]
Point: [Point number]
Document: [Filename]
"""

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
BM25_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
PDFS_SIGNATURE_PATH.parent.mkdir(parents=True, exist_ok=True) # <-- Ajout
