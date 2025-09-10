# data/loader.py
# --- Updated to use PyMuPDFLoader with DirectoryLoader (as in the notebook) ---
import os
import logging
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain.text_splitter import CharacterTextSplitter # Or RecursiveCharacterTextSplitter
import json

logger = logging.getLogger(__name__)

def load_and_split_pdfs(pdf_directory: Path, chunk_size: int, chunk_overlap: int):
    """
    Loads PDFs from a directory using DirectoryLoader + PyMuPDFLoader and splits them into chunks.
    """
    logger.info(f"Loading PDFs from {pdf_directory}")

    urls_mapping_file = pdf_directory.parent / 'scraped_urls.json'
    url_map = {}
    if urls_mapping_file.exists():
        try:
            with open(urls_mapping_file, 'r') as f:
                scraped_urls_data = json.load(f)
            # Créer un dictionnaire {chemin_local_absolu: url_originale}
            for item in scraped_urls_data:
                local_path = os.path.abspath(item.get("local_path", ""))
                original_url = item.get("original_url", "")
                if local_path and original_url:
                    url_map[local_path] = original_url
            logger.info(f"Loaded URL mapping for {len(url_map)} files.")
        except Exception as e:
            logger.error(f"Failed to load URL mapping from {urls_mapping_file}: {e}")
    else:
        logger.info(f"URL mapping file {urls_mapping_file} not found. Proceeding without URL metadata.")

    # --- Loading using DirectoryLoader + PyMuPDFLoader ---
    try:
        loader = DirectoryLoader(
            str(pdf_directory), # DirectoryLoader usually expects a string path
            glob="*.pdf", # Load only .pdf files directly in the directory
                          # Use "**/*.pdf" if you want recursive loading like in the notebook
            loader_cls=PyMuPDFLoader,
            show_progress=True, # Optional: shows loading progress
            use_multithreading=True # Optional: can speed up loading
        )
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} document objects from PDFs.")
    except Exception as e:
        logger.error(f"Error loading documents from {pdf_directory}: {e}")
        return []

    if not documents:
        logger.warning("No documents were loaded.")
        return []

    # --- Splitting ---
    logger.info("Splitting documents...")
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    # Alternative: RecursiveCharacterTextSplitter
    # text_splitter = RecursiveCharacterTextSplitter(
    #     chunk_size=chunk_size,
    #     chunk_overlap=chunk_overlap,
    #     length_function=len,
    # )
    try:
        splitted_docs = text_splitter.split_documents(documents)
        logger.info(f"Split into {len(splitted_docs)} chunks.")
        
        logger.info("Adding original URLs to document metadata...")
        updated_docs = []
        for doc in splitted_docs:
            # Le PyMuPDFLoader ajoute généralement 'file_path' ou 'source' dans les metadata
            doc_source = doc.metadata.get('file_path') or doc.metadata.get('source')
            if doc_source:
                abs_source_path = os.path.abspath(doc_source)
                original_url = url_map.get(abs_source_path)
                if original_url:
                    # Ajouter l'URL originale aux métadonnées
                    doc.metadata['original_url'] = original_url
                    logger.debug(f"Added URL {original_url[:50]}... to document from {doc_source}")
                else:
                    logger.debug(f"No URL found for document source: {doc_source}")
            else:
                logger.debug("Document has no identifiable source path in metadata.")
            updated_docs.append(doc)
        logger.info("Finished adding original URLs to metadata.")
        return updated_docs
    
    except Exception as e:
        logger.error(f"Error splitting documents: {e}")
        return [] # Return empty list on splitting error


# Optional: Cleaning function if needed (like remove_ws from notebook)
# Note: PyMuPDFLoader might handle some text cleaning differently than PyPDFLoader.
# You might need to adjust this cleaning function or remove it if not needed.
def clean_documents(docs):
    """Simple cleaning function to remove newlines."""
    logger.info("Cleaning document chunks...")
    cleaned_docs = []
    for doc in docs:
        # Assuming page_content is a string
        if hasattr(doc, 'page_content'):
            # Replace newlines with spaces or any other cleaning logic
            cleaned_content = doc.page_content.replace('\n', ' ')
            # Update the page_content of the existing document object
            doc.page_content = cleaned_content
        # Append the (potentially modified) document object
        cleaned_docs.append(doc)
    logger.info("Document chunks cleaned.")
    return cleaned_docs
