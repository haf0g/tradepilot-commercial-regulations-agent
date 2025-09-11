# orchestrator/workflow.py
import logging
from typing import Annotated, Dict, Any, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from orchestrator.tools import (
    extract_trade_info,
    run_scraper_tool,
    update_rag_knowledge_base,
    generate_final_response 
)

logger = logging.getLogger(__name__)

# --- Définition de l'État ---
class GraphState(TypedDict):
    user_query: str
    extracted_info: dict
    scraping_status: str
    scraping_success: bool 
    mfn_data_available: bool # indicateur pour MFN
    rag_documents_count: int # nombre de documents chargés
    final_answer: str

# --- Fonctions des Nœuds $ ---
def node_extract_info(state: GraphState) -> dict:
    logger.info("Executing: Extract Info Node")
    result = extract_trade_info(state)
    return result

def node_scrape_pdfs(state: GraphState) -> dict:
    logger.info("Executing: Scrape PDFs Node")
    result = run_scraper_tool(state)
    # On détermine si le scraping est un "succès" (même s'il n'y a pas de PDFs)
    # en vérifiant le message de statut ou en vérifiant l'existence de mfn_data.json
    import os
    scraping_status = result.get("scraping_status", "")
    scraping_success = "Successfully scraped" in scraping_status or "No documents were found" in scraping_status
    mfn_available = os.path.exists("data/mfn_data.json") # Vérification simple
    return {**result, "scraping_success": scraping_success, "mfn_data_available": mfn_available}

def node_update_rag(state: GraphState) -> dict:
    logger.info("Executing: Update RAG Node")
    result = update_rag_knowledge_base(state)
    # On peut compter les documents ou vérifier le statut
    # Pour cet exemple, on met un indicateur simple.
    rag_status = result.get("rag_update_status", "")
    docs_count = 0 
    if "updated" in rag_status.lower():
        docs_count = 1 
    return {**result, "rag_documents_count": docs_count}

# --- Fonctions de Routage ---
def route_after_extraction(state: GraphState) -> Literal["scrape_pdfs", "__end__"]:
    # Vérifie si l'extraction était suffisante
    if state.get("extracted_info") and not state.get("error"):
        return "scrape_pdfs"
    return "__end__" # Ou un nœud d'erreur

def route_after_scraping(state: GraphState) -> Literal["update_rag", "generate_final_response"]:
    # Si le scraping (incluant MFN) a été tenté, on passe à la suite
    # La décision finale se fera dans generate_final_response
    if state.get("scraping_success"):
        return "update_rag"
    # Si échec critique du scraping, on pourrait aller à une erreur
    # Pour cet exemple, on considère qu'on continue pour vérifier RAG/MFN
    return "update_rag" 

# --- Construction du Graphe ---
def create_workflow():
    logger.info("Creating LangGraph workflow (Agentic style)...")
    workflow = StateGraph(GraphState)

    workflow.add_node("extract_info", node_extract_info)
    workflow.add_node("scrape_pdfs", node_scrape_pdfs)
    workflow.add_node("update_rag", node_update_rag)
    workflow.add_node("generate_final_response", generate_final_response)

    workflow.add_edge(START, "extract_info")
    workflow.add_conditional_edges("extract_info", route_after_extraction)
    workflow.add_edge("scrape_pdfs", "update_rag")
    # Tous les chemins après update_rag vont vers la réponse finale
    workflow.add_edge("update_rag", "generate_final_response")
    workflow.add_edge("generate_final_response", END)

    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    logger.info("LangGraph workflow (Agentic) created and compiled.")
    return app

_workflow_app = None
def get_workflow_app():
    global _workflow_app
    if _workflow_app is None:
        _workflow_app = create_workflow()
    return _workflow_app
