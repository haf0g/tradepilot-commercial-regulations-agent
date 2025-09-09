# test_app.py
import pytest
import os
import shutil # Pour.rmtree
import config
from data.loader import load_and_split_pdfs, clean_documents # Importer clean_documents
from retrieval.vector_store import VectorStoreManager
from core.analyzer import LegalDocumentAnalyzer
from models.llm_client import get_llm_client # Test the client too
# from langchain_core.documents import Document # Si tu veux créer un Document mocké pour tester clean_documents

# Use a small test PDF if available, or mock
# For this example, we'll assume a test PDF exists or skip data tests if not.
TEST_PDF_NAME = "test_document.pdf" # Place a small test PDF in data/pdfs/
TEST_PDF_PATH = config.DATA_DIR / TEST_PDF_NAME

# --- Nouveau test pour la fonction de nettoyage ---
def test_clean_documents():
    """Test the clean_documents function."""
    # Créer un document mocké pour le test
    # from langchain_core.documents import Document # Décommente si nécessaire
    # mock_doc = Document(page_content="Line 1\nLine 2\n  Multiple   Spaces  \n\tTab", metadata={})
    
    # Pour éviter une dépendance directe sur la classe Document dans le test,
    # on peut utiliser un objet simple qui a un attribut page_content.
    class MockDocument:
        def __init__(self, page_content, metadata=None):
            self.page_content = page_content
            self.metadata = metadata or {}

    original_content = "Line 1\nLine 2\n  Multiple   Spaces  \n\tTab"
    mock_doc = MockDocument(page_content=original_content)

    cleaned_docs = clean_documents([mock_doc])
    
    assert len(cleaned_docs) == 1
    cleaned_content = cleaned_docs[0].page_content
    # Vérifier que les newlines sont supprimés (selon l'implémentation actuelle de clean_documents)
    # Et que les espaces multiples sont réduits (si c'est le comportement souhaité)
    # L'implémentation actuelle dans loader.py fait seulement doc.page_content.replace('\n', ' ')
    # Donc, vérifions cela :
    expected_content_after_clean = original_content.replace('\n', ' ')
    assert cleaned_content == expected_content_after_clean
    # Note : L'implémentation actuelle ne gère pas les espaces multiples/tabs.
    # Si tu veux cela, il faut modifier clean_documents.

# --- Fin du test ---

def test_config_loaded():
    assert config.GROQ_API_KEY is not None # Assumes it's set for tests
    assert config.DATA_DIR.exists()
    # Correction : Vérifier si les dossiers des index existent (ils sont créés par config.py)
    # Ou vérifier les fichiers index directement après création.
    assert config.FAISS_INDEX_PATH.parent.exists() # C'est le dossier de l'index FAISS
    assert config.BM25_MODEL_PATH.parent.exists() # C'est le dossier du modèle BM25 (si pertinent)

def test_data_loading():
    # This test requires a test PDF file
    if not TEST_PDF_PATH.exists():
        pytest.skip(f"Test PDF {TEST_PDF_NAME} not found in {config.DATA_DIR}")

    docs = load_and_split_pdfs(config.DATA_DIR, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    assert len(docs) > 0
    
    # --- Vérification optionnelle du nettoyage ---
    # Charger et nettoyer un petit échantillon
    # (Cela suppose que clean_documents est appelé ailleurs, comme dans app.py)
    # Pour tester ici le processus complet de nettoyage après chargement/fragmentation :
    # 1. Charger et fragmenter
    # 2. Nettoyer
    # 3. Vérifier
    # Cela dupliquerait un peu la logique de app.py, mais peut être utile.
    # Une alternative est de tester clean_documents séparément (comme ci-dessus).
    #
    # Exemple : Vérifier qu'au moins un document a du contenu (ce qui implique qu'il a été traité)
    # Et que le contenu est une chaîne (implicite avec l'utilisation de hasattr(doc, 'page_content'))
    sample_doc = docs[0]
    assert hasattr(sample_doc, 'page_content')
    assert isinstance(sample_doc.page_content, str)
    # Vérifier si le nettoyage (remplacement des \n) a été appliqué indirectement
    # Cela dépend de si clean_documents est appelé ici ou dans app.py.
    # Ce test ne l'appelle pas directement, donc cette vérification est peut-être prématurée ici.
    # Le test dédié à clean_documents ci-dessus est plus direct.
    # --- Fin de la vérification optionnelle ---

def test_vector_store_build():
    if not TEST_PDF_PATH.exists():
        pytest.skip(f"Test PDF {TEST_PDF_NAME} not found for vector store test.")

    # Ensure clean state for test
    # Correction : Supprimer les dossiers complets ou les fichiers d'index
    if config.FAISS_INDEX_PATH.exists(): # FAISS crée un dossier
        shutil.rmtree(config.FAISS_INDEX_PATH)
    if config.BM25_MODEL_PATH.exists(): # BM25 est sauvegardé comme un fichier
        os.remove(config.BM25_MODEL_PATH)

    docs = load_and_split_pdfs(config.DATA_DIR, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    # Appliquer le nettoyage comme dans app.py si c'est une partie critique du processus de test
    docs = clean_documents(docs) # Ajout du nettoyage
    vsm = VectorStoreManager(config)
    vsm.build_or_load_store(docs) # Should build

    # Vérifier si les fichiers/dossiers d'index ont été créés
    # FAISS sauvegarde dans un dossier, BM25 dans un fichier.
    assert config.FAISS_INDEX_PATH.exists() # Vérifie que le dossier de l'index FAISS existe
    assert config.BM25_MODEL_PATH.exists() # Vérifie que le fichier du modèle BM25 existe

    # Test loading
    vsm2 = VectorStoreManager(config)
    vsm2.build_or_load_store([]) # Should load existing
    assert vsm2.ensemble_retriever is not None

def test_llm_client_initialization():
    # Test Groq client initialization
    try:
        client = get_llm_client(config)
        assert client is not None
        # Cannot easily test generation without mocking API or using a tiny model
    except ValueError as e:
        # If Groq key is not set, this is expected in some test environments
        if "GROQ_API_KEY not found" in str(e):
             pytest.skip("Groq API Key not set for testing client initialization.")
        else:
             raise e
    except Exception as e: # Attraper d'autres erreurs potentielles d'initialisation (comme celle de httpx)
        # Si l'erreur est liée à httpx/proxies, cela pourrait être une erreur d'environnement.
        # On peut la laisser échouer ou la gérer spécifiquement si nécessaire.
        # Pour l'instant, on la relance pour voir l'erreur exacte dans les logs de test.
        raise e

# Note: Testing the full analyzer.ask flow would require mocking the LLM API call
# or using a very small/specific test case with a local/tiny model, which is complex.
# This test suite focuses on the main components.

if __name__ == "__main__":
    pytest.main([__file__])