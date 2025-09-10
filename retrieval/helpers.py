# retrieval/helpers.py
"""Utilitaires pour le système RAG."""

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def compute_pdfs_hash(pdfs_directory: Path) -> str:
    """
    Calcule un hash SHA256 unique basé sur les noms et les contenus des fichiers PDF.
    L'ordre des fichiers est trié pour assurer la cohérence.
    """
    hash_sha256 = hashlib.sha256()
    
    if not pdfs_directory.exists():
        logger.warning(f"PDF directory {pdfs_directory} does not exist for hashing.")
        # Hash d'une chaîne vide si le dossier n'existe pas
        hash_sha256.update(b"")
        return hash_sha256.hexdigest()

    # Trier les fichiers pour garantir un ordre cohérent
    try:
        pdf_files = sorted(pdfs_directory.glob("*.pdf"))
    except Exception as e:
        logger.error(f"Error listing PDF files in {pdfs_directory}: {e}")
        hash_sha256.update(b"")
        return hash_sha256.hexdigest()

    if not pdf_files:
        logger.info(f"No PDF files found in {pdfs_directory} for hashing.")
        hash_sha256.update(b"")
        return hash_sha256.hexdigest()

    for pdf_file in pdf_files:
        try:
            # 1. Mettre à jour le hash avec le nom du fichier (chemin relatif)
            # Cela permet de détecter si des fichiers sont ajoutés/supprimés/renommés
            relative_path_str = str(pdf_file.relative_to(pdfs_directory))
            hash_sha256.update(relative_path_str.encode('utf-8'))
            logger.debug(f"Hashing file name: {relative_path_str}")
            
            # 2. Mettre à jour le hash avec le contenu du fichier
            # Cela permet de détecter si le contenu d'un fichier change
            with open(pdf_file, 'rb') as f:
                # Lire par blocs pour les gros fichiers
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            logger.debug(f"Hashed content of: {pdf_file.name}")
        except IOError as e:
            logger.warning(f"Could not read file {pdf_file} for hashing: {e}. Skipping file content in hash.")
            # On inclut le nom mais pas le contenu, le hash sera différent si le fichier devient lisible
        except Exception as e:
            logger.error(f"Unexpected error hashing file {pdf_file}: {e}. Skipping.")
            
    final_hash = hash_sha256.hexdigest()
    logger.debug(f"Computed hash for {len(pdf_files)} files in {pdfs_directory}: {final_hash}")
    return final_hash

def save_signature(signature: str, signature_path: Path):
    """Sauvegarde la signature dans un fichier."""
    try:
        signature_path.parent.mkdir(parents=True, exist_ok=True)
        with open(signature_path, 'w') as f:
            f.write(signature)
        logger.debug(f"Saved PDFs signature to {signature_path}")
    except Exception as e:
        logger.error(f"Could not save signature to {signature_path}: {e}")

def load_signature(signature_path: Path) -> str:
    """Charge la signature depuis un fichier."""
    try:
        with open(signature_path, 'r') as f:
            sig = f.read().strip()
        logger.debug(f"Loaded PDFs signature from {signature_path}: {sig}")
        return sig
    except FileNotFoundError:
        logger.info(f"Signature file {signature_path} not found. This is expected on first run.")
        return ""
    except Exception as e:
        logger.error(f"Could not load signature from {signature_path}: {e}")
        return ""
