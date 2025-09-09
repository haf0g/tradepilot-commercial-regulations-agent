# orchestrator/workflow.py
"""Définition du workflow LangGraph pour l'agent agentic."""

import logging
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver # Pour la persistance de l'état

# Importer les outils
from orchestrator.tools import (
    extract_trade_info,
    run_scraper_tool,
    update_rag_knowledge_base,
    query_rag,
    route_based_on_extraction,
    route_after_scraping,
    route_after_rag_update
)
from models.llm_client import get_llm_client
import config

logger = logging.getLogger(__name__)

# --- Définition de l'État ---
# L'état partagé entre tous les nœuds du graphe
class GraphState(TypedDict):
    # Entrée utilisateur
    user_query: str
    
    # LLM Client (passé pour les outils qui en ont besoin)
    llm_client: object # Instance de GroqModelClient
    
    # Résultats intermédiaires
    extracted_info: dict
    scraping_status: str
    rag_update_status: str
    
    # Sortie finale
    final_answer: str
    
    # Pour gérer les erreurs (optionnel)
    error: str

# --- Fonctions des Nœuds ---
# Chaque nœud est une fonction qui prend l'état et renvoie un dictionnaire
# de mises à jour à appliquer à l'état.

def node_extract_info(state: GraphState) -> dict:
    """Nœud pour extraire les informations."""
    logger.info("Executing: Extract Info Node")
    # L'état est passé à l'outil
    result = extract_trade_info(state)
    # Le résultat de l'outil est un dict qui sera fusionné dans l'état
    return result

def node_scrape_pdfs(state: GraphState) -> dict:
    """Nœud pour scraper les PDFs."""
    logger.info("Executing: Scrape PDFs Node")
    result = run_scraper_tool(state)
    return result

def node_update_rag(state: GraphState) -> dict:
    """Nœud pour mettre à jour le RAG."""
    logger.info("Executing: Update RAG Node")
    result = update_rag_knowledge_base(state)
    return result

def node_query_rag(state: GraphState) -> dict:
    """Nœud pour interroger le RAG."""
    logger.info("Executing: Query RAG Node")
    result = query_rag(state)
    return result

# --- Construction du Graphe ---
def create_workflow():
    """Crée et compile le graphe LangGraph."""
    logger.info("Creating LangGraph workflow...")

    # 1. Créer le graphe avec l'état défini
    workflow = StateGraph(GraphState)

    # 2. Ajouter les nœuds (états/étapes)
    workflow.add_node("extract_info", node_extract_info)
    workflow.add_node("scrape_pdfs", node_scrape_pdfs)
    workflow.add_node("update_rag", node_update_rag)
    workflow.add_node("query_rag", node_query_rag)
    # Vous pouvez ajouter un nœud 'error_handler' si nécessaire

    # 3. Définir les arêtes (transitions)
    
    # Du point de départ à l'extraction
    workflow.add_edge(START, "extract_info")
    
    # De l'extraction au scraping ou à l'erreur
    # Utiliser une fonction de routage
    workflow.add_conditional_edges(
        "extract_info",
        route_based_on_extraction,
        {
            "scrape": "scrape_pdfs",
            "error": END # Ou un nœud d'erreur
        }
    )
    
    # Du scraping à la mise à jour du RAG ou à l'erreur
    workflow.add_conditional_edges(
        "scrape_pdfs",
        route_after_scraping,
        {
            "update_rag": "update_rag",
            "error": END # Ou retour à extract_info
        }
    )
    
    # De la mise à jour du RAG à l'interrogation du RAG ou à l'erreur
    workflow.add_conditional_edges(
        "update_rag",
        route_after_rag_update,
        {
            "query_rag": "query_rag",
            "error": END
        }
    )
    
    # De l'interrogation du RAG à la fin
    workflow.add_edge("query_rag", END)
    
    # 4. Compiler le graphe
    # MemorySaver permet de conserver l'état entre les exécutions (utile pour une session)
    # Pour une exécution unique, cela peut ne pas être nécessaire.
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory) 
    
    logger.info("LangGraph workflow created and compiled.")
    return app

# --- Instance Singleton ---
_workflow_app = None

def get_workflow_app():
    """Fournit une instance singleton du workflow compilé."""
    global _workflow_app
    if _workflow_app is None:
        _workflow_app = create_workflow()
    return _workflow_app
