# tests/test_app.py
"""Unit and integration tests for core application components."""
import sys
import os

# --- Configuration du chemin pour les imports ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ---
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY

# --- Imports de l'application ---
import config
from data.loader import load_and_split_pdfs, clean_documents
from retrieval.vector_store import VectorStoreManager
from retrieval.helpers import compute_pdfs_hash, save_signature, load_signature
from models.llm_client import get_llm_client
from scraper.web_scraper import clean_filename, clean_pdfs_folder
# ---

# --- Configuration des tests ---
TEST_PDF_NAME = "document_test.pdf"
TEST_PDF_PATH_SOURCE = Path(__file__) # Emplacement de ce fichier test
TEST_DATA_DIR_NAME = "temp_test_pdfs"

@pytest.fixture(scope="function")
def isolated_test_dir():
    """Crée un dossier temporaire isolé avec le document de test pour chaque test."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        test_dir = Path(tmpdirname) / TEST_DATA_DIR_NAME
        test_dir.mkdir()
        
        # Copier le PDF de test s'il existe
        source_pdf = TEST_PDF_PATH_SOURCE.parent / TEST_PDF_NAME
        if source_pdf.exists():
            shutil.copy(source_pdf, test_dir / TEST_PDF_NAME)
        
        yield test_dir.absolute()
        
# --- Tests ---
def test_clean_filename():
    result = clean_filename("A/File:Name?.txt")
    assert result == "A_File_Name_.txt"

def test_compute_pdfs_hash(isolated_test_dir):
    hash_val = compute_pdfs_hash(isolated_test_dir)
    assert isinstance(hash_val, str)

def test_signature_persistence(isolated_test_dir):
    sig_file = isolated_test_dir / "test.sig"
    original_hash = "test_hash_123"
    save_signature(original_hash, sig_file)
    assert sig_file.exists()
    loaded_hash = load_signature(sig_file)
    assert loaded_hash == original_hash

def test_data_loader_processes_pdfs(isolated_test_dir):
    pdf_files = list(isolated_test_dir.glob("*.pdf"))
    if not pdf_files:
        pytest.skip("No test PDF found, skipping loader test.")

    docs = load_and_split_pdfs(isolated_test_dir, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    # Vérifie que des documents ont été chargés
    assert len(docs) > 0
    # Vérifie la structure d'un document
    assert hasattr(docs[0], 'page_content')
    # Vérifie que le nettoyage fonctionne
    cleaned_docs = clean_documents([docs[0]])
    assert '\n' not in cleaned_docs[0].page_content

def test_vector_store_lifecycle(isolated_test_dir):
    # Test unitaire du cycle de vie du VectorStoreManager
    with patch.object(VectorStoreManager, '_build_and_save_store') as mock_build, \
         patch.object(VectorStoreManager, 'get_retriever') as mock_get_retriever:

        mock_retriever = MagicMock()
        mock_get_retriever.return_value = mock_retriever

        docs = [MagicMock()]
        vsm = VectorStoreManager(config)
        # Appeler build_or_load_store avec des documents pour déclencher _build_and_save_store
        vsm.build_or_load_store(docs)
        
        # Vérifier que la méthode interne a été appelée avec les bons arguments
        # Le deuxième argument est le hash, mocké par ANY
        mock_build.assert_called_once_with(docs, ANY)

def test_llm_client_initialization():
    # Test unitaire de l'initialisation du client LLM
    with patch('models.llm_client.Groq') as mock_groq:
        mock_client_instance = MagicMock()
        mock_groq.return_value = mock_client_instance
        
        client = get_llm_client(config)
        
        mock_groq.assert_called_with(api_key=config.GROQ_API_KEY)
        # Vérifier que l'objet retourné est une instance de GroqModelClient
        from models.llm_client import GroqModelClient 
        assert isinstance(client, GroqModelClient)
        assert client.client == mock_client_instance
