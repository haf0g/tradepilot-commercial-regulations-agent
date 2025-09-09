# retrieval/vector_store.py
import os
from pathlib import Path
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
import pickle
import logging

logger = logging.getLogger(__name__)

class VectorStoreManager:
    def __init__(self, config):
        self.config = config
        self.embeddings = SentenceTransformerEmbeddings(model_name=config.EMBEDDING_MODEL_NAME)
        self.db = None
        self.bm25_retriever = None
        self.faiss_retriever = None
        self.ensemble_retriever = None

    def build_or_load_store(self, documents):
        """Builds FAISS/BM25 index or loads from disk if available."""
        faiss_exists = os.path.exists(self.config.FAISS_INDEX_PATH)
        bm25_exists = os.path.exists(self.config.BM25_MODEL_PATH)

        if faiss_exists and bm25_exists:
            logger.info("Loading existing FAISS and BM25 indexes...")
            try:
                self.db = FAISS.load_local(self.config.FAISS_INDEX_PATH, self.embeddings, allow_dangerous_deserialization=True)
                with open(self.config.BM25_MODEL_PATH, 'rb') as f:
                    self.bm25_retriever = pickle.load(f)
                logger.info("Indexes loaded successfully.")
            except Exception as e:
                logger.error(f"Error loading indexes: {e}. Rebuilding...")
                self._build_store(documents)
        else:
            logger.info("Building FAISS and BM25 indexes...")
            self._build_store(documents)

        self._setup_retrievers()

    def _build_store(self, documents):
        """Builds the FAISS and BM25 stores from scratch."""
        # --- FAISS ---
        self.db = FAISS.from_documents(documents, self.embeddings)
        self.db.save_local(self.config.FAISS_INDEX_PATH)
        logger.info(f"FAISS index saved to {self.config.FAISS_INDEX_PATH}")

        # --- BM25 ---
        # BM25Retriever works directly on documents, no separate "build" step usually
        # We'll save it for persistence if needed
        self.bm25_retriever = BM25Retriever.from_documents(documents)
        with open(self.config.BM25_MODEL_PATH, 'wb') as f:
            pickle.dump(self.bm25_retriever, f)
        logger.info(f"BM25 model saved to {self.config.BM25_MODEL_PATH}")

    def _setup_retrievers(self):
        """Sets up the FAISS and Ensemble retrievers."""
        if self.db and self.bm25_retriever:
            self.faiss_retriever = self.db.as_retriever(search_kwargs={'k': self.config.RETRIEVER_K})
            self.bm25_retriever.k = self.config.RETRIEVER_K # Set k for BM25
            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[self.faiss_retriever, self.bm25_retriever],
                weights=self.config.ENSEMBLE_WEIGHTS
            )
            logger.info("Ensemble retriever configured.")
        else:
            raise ValueError("FAISS or BM25 retriever not initialized.")

    def get_retriever(self):
        """Returns the configured ensemble retriever."""
        if self.ensemble_retriever:
            return self.ensemble_retriever
        else:
            raise RuntimeError("Retriever not set up. Call build_or_load_store first.")
