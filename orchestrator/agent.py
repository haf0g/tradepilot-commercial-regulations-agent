# orchestrator/agent.py (mise à jour pour LangGraph)
"""Agent principal qui orchestre les outils via LangGraph."""

import logging
import uuid # Pour générer un thread_id si nécessaire
from orchestrator.workflow import get_workflow_app, GraphState
from models.llm_client import get_llm_client
import config

logger = logging.getLogger(__name__)

class TradePilotAgent:
    def __init__(self):
        self.workflow_app = get_workflow_app() # Obtenir le workflow compilé
        self.llm_client = get_llm_client(config) # Obtenir le client LLM
        logger.info("TradePilot Agentic AI (LangGraph) initialized.")

    def run(self, user_input: str) -> str:
        """
        Exécute le workflow LangGraph avec l'entrée de l'utilisateur.
        """
        logger.info(f"Agent received input: '{user_input}'")
        try:
            # 1. Préparer l'état initial
            initial_state: GraphState = {
                "user_query": user_input,
                "extracted_info": {},
                "scraping_status": "",
                "rag_update_status": "",
                "final_answer": "",
                "error": ""
            }
            
            # 2. Exécuter le workflow
            # Un thread_id est nécessaire si un checkpointer (MemorySaver) est utilisé
            # pour suivre l'état d'une session spécifique.
            config_for_run = {"configurable": {"thread_id": str(uuid.uuid4())}}
            
            final_state = self.workflow_app.invoke(initial_state, config=config_for_run)
            
            # 3. Récupérer la réponse finale
            final_answer = final_state.get("final_answer", "Sorry, I couldn't generate a final answer.")
            logger.info("Agent execution (LangGraph) completed.")
            return final_answer
            
        except Exception as e:
            logger.error(f"Error during agent execution: {e}")
            return f"Sorry, the agent encountered an error: {e}"

# Instance singleton
_agent_instance = None

def get_agent():
    """Fournit une instance singleton de l'agent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = TradePilotAgent()
    return _agent_instance
