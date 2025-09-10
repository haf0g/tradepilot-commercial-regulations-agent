# orchestrator/tools.py 
"""Définition des outils (fonctions) utilisables par l'agent agentic (LangGraph)"""

import logging
from typing import Dict, Any
# Importations depuis votre application
from scraper.web_scraper import scrape_trade_pdfs, clean_pdfs_folder 

from data.loader import load_and_split_pdfs, clean_documents
from retrieval.vector_store import VectorStoreManager
from core.analyzer import LegalDocumentAnalyzer
from models.llm_client import get_llm_client
import config # Pour accéder aux configurations
import csv
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Charger les données au démarrage du module (une seule fois)
# Assurez-vous que les chemins sont corrects par rapport à la racine du projet
HS_CODES_FILE = Path(__file__).parent.parent / "data" / "json" / "hs_code_descriptions.json"
COUNTRIES_FILE = Path(__file__).parent.parent / "data" / "csv" / "iso_country_codes.csv"

try:
    with open(HS_CODES_FILE, 'r') as f:
        HS_DATA = json.load(f)
    logger.info(f"Loaded {len(HS_DATA)} HS codes.")
except Exception as e:
    logger.error(f"Failed to load HS codes: {e}")
    HS_DATA = []

COUNTRY_MAP = {}
COUNTRY_NAME_TO_CODE = {} # Pour la recherche inverse
try:
    with open(COUNTRIES_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get('Code', '').strip()
            name = row.get('Country Name', '').strip()
            if code and name:
                COUNTRY_MAP[name.lower()] = name
                COUNTRY_NAME_TO_CODE[name.lower()] = code
    logger.info(f"Loaded {len(COUNTRY_MAP)} country mappings.")
except Exception as e:
    logger.error(f"Failed to load country codes: {e}")
    COUNTRY_MAP = {}
    COUNTRY_NAME_TO_CODE = {}

# --- Nouvelle fonction utilitaire ---
def find_hs_code_for_product(product_name: str) -> str:
    """Trouve un code HS basé sur le nom du produit."""
    if not product_name or not HS_DATA:
        return ""
    for item in HS_DATA:
        desc = item.get("description", "")
        if product_name.lower() in desc.lower():
            return item.get("id", "")
    return ""
'''
# --- Outil 1: Extraction d'Informations ---
def extract_trade_info(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait les informations de pays et de produit/HS code de la requête utilisateur.
    Input: {'user_query': str}
    Output: {'extracted_info': Dict}
    """
    user_query = state.get("user_query", "")
    # Obtenir le client LLM localement
    try:
        llm_client = get_llm_client(config)
    except Exception as e:
        logger.error(f"Failed to initialize LLM client inside tool: {e}")
        return {"error": f"LLM Client init failed: {e}", "extracted_info": {}}
    
    if not user_query:
        logger.error("No user query provided for extraction.")
        return {"error": "No user query provided for extraction."}

    logger.info(f"Extracting trade info from query: '{user_query}'")
    # --- Prompt Amélioré ---
    # Plus direct, insiste sur l'ordre Export -> Import -> Produit/HS
    # et sur la vérification de la présence des informations.
    extraction_prompt = f"""
You are an expert in international trade data extraction. Your task is to identify the Exporting Country, Importing Country, and Product/HS Code from the user's query.

Guidelines:
1.  The Exporting Country is the one FROM which goods are sent.
2.  The Importing Country is the one TO which goods are sent.
3.  Identify a Product name or a specific HS Code (e.g., 07099200).
4.  If an HS Code is mentioned, prioritize it over a general product name.
5.  Be concise and extract only the names/codes.
6.  If you cannot confidently identify a piece of information, leave its field as an empty string ("").
7.  Double-check the countries' names for common aliases (e.g., USA/United States, UK/United Kingdom).

Query: {user_query}

Provide the answer in the following strict JSON format:
{{
  "exporter": "Country Name", // E.g., "Morocco"
  "importer": "Country Name", // E.g., "United States Of America"
  "product": "Product Name",  // E.g., "olives"
  "hs_code": "HS Code"        // E.g., "07099200" (can be empty if not found)
}}

Example Output:
{{
  "exporter": "Morocco",
  "importer": "United States Of America",
  "product": "olives",
  "hs_code": "07099200"
}}

Do not include any other text, explanations, or markdown. Only output the JSON.
"""
    messages = [
        {"role": "system", "content": "You are a precise data extraction tool."},
        {"role": "user", "content": extraction_prompt}
    ]
    
    try:
        raw_response = llm_client.generate(messages, max_tokens=300, temperature=0.1) # Un peu plus de tokens
        import json
        try:
            data = json.loads(raw_response)
            logger.info(f"Extracted info: {data}")
            
            # --- Validation basique ---
            # Vérifier si les champs critiques ne sont pas que des espaces
            exporter_raw = data.get("exporter", "").strip()
            importer_raw = data.get("importer", "").strip()

            # Fonction d'aide pour trouver un nom de pays valide
            def find_valid_country_name(raw_name):
                if not raw_name:
                    return ""
                raw_lower = raw_name.lower()
                # Recherche exacte d'abord
                if raw_lower in COUNTRY_MAP:
                    return COUNTRY_MAP[raw_lower]
                # Recherche partielle (plus complexe, exemple simplifié)
                # for key, value in COUNTRY_MAP.items():
                #     if raw_lower in key or raw_lower in value.lower():
                #         return value
                return raw_name # Retourne le nom original si non trouvé
            
            data["exporter"] = find_valid_country_name(exporter_raw)
            data["importer"] = find_valid_country_name(importer_raw)

            product_or_hs = (data.get("hs_code", "") or data.get("product", "")).strip()
            
            product_name = data.get("product", "").strip()
            hs_code = data.get("hs_code", "").strip()
            if not hs_code and product_name and HS_DATA:
                # Recherche simple : trouver le premier code qui contient le nom du produit
                # Une recherche plus sophistiquée (TF-IDF, fuzzy matching) serait meilleure
                for item in HS_DATA:
                    desc = item.get("description", "")
                    if product_name.lower() in desc.lower():
                        data["hs_code"] = item.get("id", "")
                        logger.info(f"Found HS code {data['hs_code']} for product '{product_name}' based on description '{desc}'")
                        # Vous pouvez choisir de breaker ici ou de continuer pour trouver un match plus précis
                        break

                # On peut choisir de renvoyer une erreur ici pour forcer un routage différent
                # ou laisser le routage gérer ça.
                # Pour l'instant, on retourne les données extraites, même incomplètes.
                # Le routage devra être plus intelligent.
            
            return {"extracted_info": data}
        except json.JSONDecodeError:
            logger.error(f"LLM response was not valid JSON: {raw_response}")
            return {"error": "Failed to parse extracted information as JSON.", "extracted_info": {}}
    except Exception as e:
        logger.error(f"Error in extract_trade_info: {e}")
        return {"error": f"Error during extraction: {e}", "extracted_info": {}}
'''

# --- Mise à jour de extract_trade_info ---
def extract_trade_info(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait les informations de pays et de produit/HS code de la requête utilisateur.
    Gère les cas spéciaux comme les accords commerciaux.
    """
    user_query = state.get("user_query", "")
    try:
        llm_client = get_llm_client(config)
    except Exception as e:
        logger.error(f"Failed to initialize LLM client inside tool: {e}")
        return {"error": f"LLM Client init failed: {e}", "extracted_info": {}}
    
    if not user_query:
        logger.error("No user query provided for extraction.")
        return {"error": "No user query provided for extraction."}

    logger.info(f"Extracting trade info from query: '{user_query}'")
    
    # --- Prompt Amélioré avec gestion des accords ---
    extraction_prompt = f"""
You are an expert in international trade data extraction. Your task is to identify the Exporting Country, Importing Country, and Product/HS Code from the user's query.

Guidelines:
1.  The Exporting Country is the one FROM which goods are sent.
2.  The Importing Country is the one TO which goods are sent.
3.  Identify a Product name or a specific HS Code (e.g., 07099200).
4.  If an HS Code is mentioned, prioritize it over a general product name.
5.  Be concise and extract only the names/codes.
6.  Handle Special Cases:
    a. If the query mentions a Trade Agreement (like USMCA, NAFTA, EU, etc.):
        - If it's a two-country agreement (e.g., USA-Morocco FTA), try to infer the two countries.
        - If it's a multi-country agreement (e.g., USMCA, EU):
            - If one country is explicitly mentioned as exporter/importer, use it.
            - Otherwise, you can use placeholder names like "USMCA_Countries" or list specific countries if clear.
7.  Double-check the countries' names for common aliases (e.g., USA/United States, UK/United Kingdom).
8.  If you cannot confidently identify a piece of information, leave its field as an empty string ("").

Query: {user_query}

Provide the answer in the following strict JSON format:
{{
  "exporter": "Country Name or Agreement Placeholder", // E.g., "Morocco" or "USMCA_Countries"
  "importer": "Country Name or Agreement Placeholder", // E.g., "United States Of America" or "USMCA_Countries"
  "product": "Product Name",  // E.g., "olives"
  "hs_code": "HS Code"        // E.g., "07099200" (can be empty if not found)
}}

Example Output for a standard query:
{{
  "exporter": "Morocco",
  "importer": "United States Of America",
  "product": "olives",
  "hs_code": "07099200"
}}

Example Output for an agreement query:
{{
  "exporter": "USMCA_Countries",
  "importer": "USMCA_Countries",
  "product": "agricultural products",
  "hs_code": "841934"
}}

Do not include any other text, explanations, or markdown. Only output the JSON.
"""
    # --- Fin du Prompt Amélioré ---
    
    messages = [
        {"role": "system", "content": "You are a precise data extraction tool."},
        {"role": "user", "content": extraction_prompt}
    ]
    
    try:
        raw_response = llm_client.generate(messages, max_tokens=300, temperature=0.1)
        import json as json_lib
        try:
            data = json_lib.loads(raw_response)
            logger.info(f"Raw extracted info: {data}")
            
            # --- Post-traitement et Validation ---
            exporter_raw = data.get("exporter", "").strip()
            importer_raw = data.get("importer", "").strip()
            product_raw = data.get("product", "").strip()
            hs_code_raw = data.get("hs_code", "").strip()

            # 1. Validation/Correction des Pays
            def find_valid_country_name(raw_name):
                if not raw_name:
                    return ""
                # Gestion des cas spéciaux
                if "usmca" in raw_name.lower():
                    # On peut choisir un pays représentatif ou laisser le placeholder
                    # Pour simplifier, on prend les USA et le Mexique comme exemple
                    # Une logique plus complexe pourrait être implémentée ici
                    return "United States Of America" # Ou "Mexico" ou "Canada"
                if "eu" in raw_name.lower() or "european union" in raw_name.lower():
                    return "Germany" # Ou un autre pays membre
                
                raw_lower = raw_name.lower()
                if raw_lower in COUNTRY_MAP:
                    return COUNTRY_MAP[raw_lower]
                return raw_name

            data["exporter"] = find_valid_country_name(exporter_raw)
            data["importer"] = find_valid_country_name(importer_raw)

            # 2. Validation/Recherche du Code HS
            if not hs_code_raw and product_raw:
                data["hs_code"] = find_hs_code_for_product(product_raw)
                if data["hs_code"]:
                    logger.info(f"Found HS code {data['hs_code']} for product '{product_raw}'")

            # 3. Décider du statut de l'extraction
            # Nouvelle logique : On considère comme "suffisant" si on a au moins un pays ET un produit/HS code
            # Cela permet de continuer même si un pays est manquant (comme dans le cas USMCA)
            exporter = data.get("exporter", "")
            importer = data.get("importer", "")
            product_or_hs = data.get("hs_code", "") or data.get("product", "")

            # Pour les accords, on peut avoir les deux pays identiques ou des placeholders
            # On vérifie simplement qu'on a les infos nécessaires pour le scraping ou le RAG
            if (exporter or importer) and product_or_hs:
                 # On considère que l'extraction est suffisante si on a un pays ET un produit/code
                 # Même si un pays est manquant, le scraper/RAG pourra peut-être gérer
                 # On met un indicateur dans l'état
                 data["extraction_status"] = "partial_but_usable"
                 logger.info(f"Extraction usable (partial): exporter='{exporter}', importer='{importer}', product/hs='{product_or_hs}'")
            elif exporter and importer and product_or_hs:
                data["extraction_status"] = "complete"
                logger.info(f"Extraction complete: exporter='{exporter}', importer='{importer}', product/hs='{product_or_hs}'")
            else:
                data["extraction_status"] = "insufficient"
                logger.warning(f"Insufficient information for full processing: exporter='{exporter}', importer='{importer}', product/hs='{product_or_hs}'")

            return {"extracted_info": data}
        except json_lib.JSONDecodeError:
            logger.error(f"LLM response was not valid JSON: {raw_response}")
            return {"error": "Failed to parse extracted information as JSON.", "extracted_info": {}}
    except Exception as e:
        logger.error(f"Error in extract_trade_info: {e}")
        return {"error": f"Error during extraction: {e}", "extracted_info": {}}
    
# --- Outil 2: Scraping de PDFs ---
def run_scraper_tool(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Exécute le scraper avec les informations extraites.
    Input: {'extracted_info': Dict}
    Output: {'scraping_status': str}
    """

    try:
        clean_pdfs_folder(config.DATA_DIR)
    except Exception as e:
        logger.error(f"Failed to clean PDFs folder before scraping: {e}")

    extracted_info = state.get("extracted_info", {})
    
    # Gérer les placeholders ou valeurs spéciales si nécessaire
    exporter = extracted_info.get("exporter", "")
    importer = extracted_info.get("importer", "")
    # Prioriser le HS code
    product = extracted_info.get("hs_code", "") or extracted_info.get("product", "")
    
    # --- Gestion des placeholders ---
    # Si l'exporter ou l'importer est un placeholder, on peut soit :
    # 1. Tenter le scraping avec une valeur par défaut
    # 2. Arrêter et expliquer
    # Ici, on tente avec une valeur par défaut
    if "usmca" in exporter.lower():
        logger.info("Replacing USMCA exporter placeholder with USA for scraping.")
        exporter = "United States Of America"
    if "usmca" in importer.lower():
        logger.info("Replacing USMCA importer placeholder with Mexico for scraping.")
        importer = "Mexico"
    if "eu" in exporter.lower() or "european union" in exporter.lower():
        logger.info("Replacing EU exporter placeholder with Germany for scraping.")
        exporter = "Germany"
    if "eu" in importer.lower() or "european union" in importer.lower():
        logger.info("Replacing EU importer placeholder with France for scraping.")
        importer = "France"

    if not exporter or not importer or not product:
        error_msg = f"Missing information for scraping: Exporter='{exporter}', Importer='{importer}', Product/HS='{product}'"
        logger.error(error_msg)
        return {"scraping_status": error_msg}

    logger.info(f"Running scraper for {exporter} -> {importer} ({product})")
    try:
        urls_mapping_file_path = scrape_trade_pdfs(exporter, importer, product, output_dir="data")
        success_msg = f"Successfully scraped documents for {exporter} -> {importer} ({product})."
        logger.info(success_msg)
        return {
            "scraping_status": success_msg,
            "urls_mapping_file": urls_mapping_file_path # Nouvelle clé dans le dictionnaire de retour
        }

    except Exception as e:
        error_msg = f"Error during scraping: {e}"
        logger.error(error_msg)
        # --- Modification : Retourner aussi le chemin en cas d'erreur (probablement None ou un chemin invalide) ---
        return {
            "scraping_status": error_msg,
            "urls_mapping_file": None # Ou une valeur par défaut
        }

# --- Outil 3: Mise à Jour du RAG ---
def update_rag_knowledge_base(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Met à jour la base de connaissances du RAG avec les nouveaux PDFs.
    Input: {} (pas d'input spécifique requis)
    Output: {'rag_update_status': str}
    """
    logger.info("Updating RAG knowledge base...")
    try:
        documents = load_and_split_pdfs(config.DATA_DIR, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        if not documents:
            msg = "No documents found in data/pdfs to update RAG."
            logger.warning(msg)
            return {"rag_update_status": msg}
        documents = clean_documents(documents)

        vsm = VectorStoreManager(config)
        vsm.build_or_load_store(documents) # Reconstruire à partir des nouveaux docs
        
        msg = f"RAG knowledge base updated with {len(documents)} document chunks."
        logger.info(msg)
        return {"rag_update_status": msg}
    except Exception as e:
        error_msg = f"Error updating RAG knowledge base: {e}"
        logger.error(error_msg)
        return {"rag_update_status": error_msg}

# --- Outil 4: Interrogation du RAG ---
def query_rag(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interroge le RAG avec la question de l'utilisateur.
    Input: {'user_query': str}
    Output: {'final_answer': str}
    """
    user_question = state.get("user_query", "")
    if not user_question:
         error_msg = "Error: No user question provided to query RAG."
         logger.error(error_msg)
         return {"final_answer": error_msg} # Renvoyer une erreur comme réponse finale

    logger.info(f"Querying RAG with question: '{user_question}'")
    try:
        vsm = VectorStoreManager(config)
        vsm.build_or_load_store([]) # Charger les index existants
        analyzer = LegalDocumentAnalyzer(vsm.get_retriever(), config)
        answer = analyzer.ask(user_question)
        logger.info("RAG query successful.")
        return {"final_answer": answer}
    except Exception as e:
        error_msg = f"Error querying RAG: {e}"
        logger.error(error_msg, exc_info=True) # Log avec traceback
        # Renvoyer l'erreur comme réponse finale pour que l'utilisateur la voie
        return {"final_answer": f"Sorry, I encountered an error while searching the documents: {str(e)}"}

# --- Fonction utilitaire pour décider de la prochaine étape ---
'''
def route_based_on_extraction(state: Dict[str, Any]) -> str:
    #Décide de la prochaine étape après l'extraction.
    # 1. Vérifier les erreurs explicites
    if state.get("error"):
        logger.warning(f"Routing to END due to error in state: {state['error']}")
        return "error" # Cela suppose un nœud 'error' ou un END défini dans le workflow

    # 2. Obtenir les infos extraites
    extracted_info = state.get("extracted_info", {})
    
    # 3. Validation stricte des informations critiques
    exporter = extracted_info.get("exporter", "").strip()
    importer = extracted_info.get("importer", "").strip()
    # Prioriser le HS code, sinon le produit
    product_or_hs = (extracted_info.get("hs_code", "") or extracted_info.get("product", "")).strip()

    if exporter and importer and product_or_hs:
        logger.info(f"Routing to 'scrape': exporter={exporter}, importer={importer}, product/hs={product_or_hs}")
        return "scrape"
    else:
        # Information insuffisante extraite
        logger.info(f"Routing to END: Insufficient information extracted. Exporter='{exporter}', Importer='{importer}', Product/HS='{product_or_hs}'")
        # Option 1: Arrêter et demander plus d'info (moins idéal sans boucle de clarification)
        # Option 2: Retenter l'extraction ? (compliqué sans logique complexe)
        # Pour l'instant, on arrête et on informe l'utilisateur via la réponse finale.
        # Vous pouvez créer un nœud 'ask_for_clarification' ici si vous implémentez cette logique.
        return "error" # Ou END si vous mappez "error" -> END dans le workflow
'''

# --- Fonction de routage mise à jour ---
def route_based_on_extraction(state: Dict[str, Any]) -> str:
    """
    Décide de la prochaine étape après l'extraction.
    """
    # 1. Vérifier les erreurs explicites
    if state.get("error"):
        logger.warning(f"Routing to END due to error in state: {state['error']}")
        return "error"

    # 2. Obtenir les infos extraites
    extracted_info = state.get("extracted_info", {})
    status = extracted_info.get("extraction_status", "")
    
    exporter = extracted_info.get("exporter", "").strip()
    importer = extracted_info.get("importer", "").strip()
    product_or_hs = (extracted_info.get("hs_code", "") or extracted_info.get("product", "")).strip()

    # 3. Nouvelle logique de routage basée sur le statut
    if status in ["complete", "partial_but_usable"]:
        # Même si partiel, on tente de continuer
        logger.info(f"Routing to 'scrape': exporter={exporter}, importer={importer}, product/hs={product_or_hs}")
        return "scrape"
    else: # status == "insufficient" or other
        logger.info(f"Routing to END: Insufficient information extracted. Exporter='{exporter}', Importer='{importer}', Product/HS='{product_or_hs}'")
        return "error" # Ou END

    
def route_after_scraping(state: Dict[str, Any]) -> str:
    """
    Décide de la prochaine étape après le scraping.
    """
    status = state.get("scraping_status", "")
    if "Successfully" in status:
        return "update_rag"
    return "error" # Ou retourner à l'extraction si on veut réessayer?

def route_after_rag_update(state: Dict[str, Any]) -> str:
    """
    Décide de la prochaine étape après la mise à jour du RAG.
    """
    status = state.get("rag_update_status", "")
    if "updated" in status:
        return "query_rag"
    return "error"