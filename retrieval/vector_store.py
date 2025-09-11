# retrieval/vector_store.py
import os
from pathlib import Path
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
import pickle
import logging
from .helpers import compute_pdfs_hash, load_signature, save_signature
import config

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
        """
        Construit ou charge les index FAISS/BM25 de manière intelligente.
        """
        logger.info("Checking for intelligent persistence of indexes...")
        
        # 1. Calculer la signature actuelle des PDFs
        logger.info("Computing hash for current PDFs...")
        current_signature = compute_pdfs_hash(self.config.DATA_DIR)
        logger.info(f"Current PDFs hash: {current_signature[:16]}...") # Log partiel pour concision

        # 2. Charger la signature sauvegardée
        logger.info("Loading last saved PDFs hash...")
        last_signature = load_signature(self.config.PDFS_SIGNATURE_PATH)
        logger.info(f"Last saved PDFs hash: {last_signature[:16] if last_signature else 'None'}...")

        # 3. Vérifier si les index existent ET si la signature correspond
        faiss_exists = self.config.FAISS_INDEX_PATH.exists()
        bm25_exists = self.config.BM25_MODEL_PATH.exists()
        signatures_match = (current_signature == last_signature)
        has_previous_signature = bool(last_signature)

        if faiss_exists and bm25_exists and signatures_match and has_previous_signature:
            logger.info("PDFs unchanged and indexes exist. Loading existing FAISS and BM25 indexes from disk...")
            try:
                self.db = FAISS.load_local(self.config.FAISS_INDEX_PATH, self.embeddings, allow_dangerous_deserialization=True)
                with open(self.config.BM25_MODEL_PATH, 'rb') as f:
                    self.bm25_retriever = pickle.load(f)
                logger.info("Indexes loaded successfully from disk.")
            except Exception as e:
                logger.error(f"Error loading indexes from disk: {e}. Rebuilding them...")
                self._build_and_save_store(documents, current_signature)
        else:
            if not has_previous_signature:
                logger.info("No previous signature found. Building indexes for the first time.")
            elif not (faiss_exists and bm25_exists):
                logger.info("FAISS or BM25 index files are missing. Rebuilding indexes.")
            elif not signatures_match:
                logger.info("PDFs have changed since last index build. Rebuilding indexes.")
            else:
                logger.info("Unclear condition, rebuilding indexes to be safe.")
                
            self._build_and_save_store(documents, current_signature)

        self._setup_retrievers()

    def _build_and_save_store(self, documents, signature: str):
        """
        Construit les index à partir des documents et sauvegarde la signature.
        """
        if not documents:
            logger.warning("No documents provided to build index. Index will be empty.")
            # On crée un index vide
            self.db = None
            self.bm25_retriever = None
            # Sauvegarder quand même la signature pour le prochain run
            save_signature(signature, self.config.PDFS_SIGNATURE_PATH)
            return
            
        logger.info("Building FAISS and BM25 indexes from documents...")
        # --- FAISS ---
        self.db = FAISS.from_documents(documents, self.embeddings)
        self.db.save_local(self.config.FAISS_INDEX_PATH)
        logger.info(f"FAISS index saved to {self.config.FAISS_INDEX_PATH}")

        # --- BM25 ---
        self.bm25_retriever = BM25Retriever.from_documents(documents)
        with open(self.config.BM25_MODEL_PATH, 'wb') as f:
            pickle.dump(self.bm25_retriever, f)
        logger.info(f"BM25 model saved to {self.config.BM25_MODEL_PATH}")

        # --- Sauvegarder la nouvelle signature ---
        save_signature(signature, self.config.PDFS_SIGNATURE_PATH)
        logger.info(f"New PDFs signature saved.")


    def _setup_retrievers(self):
        """Sets up the FAISS and Ensemble retrievers."""
        # Gérer le cas où les index n'ont pas pu être chargés/construits
        if self.db is None or self.bm25_retriever is None:
             logger.warning("One or both indexes are not available. Retriever will not function.")
             self.ensemble_retriever = None
             return

        self.faiss_retriever = self.db.as_retriever(search_kwargs={'k': self.config.RETRIEVER_K})
        self.bm25_retriever.k = self.config.RETRIEVER_K
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[self.faiss_retriever, self.bm25_retriever],
            weights=self.config.ENSEMBLE_WEIGHTS
        )
        logger.info("Ensemble retriever configured.")

    def get_retriever(self):
        """Returns the configured ensemble retriever."""
        if self.ensemble_retriever:
            return self.ensemble_retriever
        else:
            raise RuntimeError("Retriever is not available (indexes missing or failed to load/build).")