# orchestrator/agent.py
import logging
import uuid
from orchestrator.workflow import get_workflow_app, GraphState

logger = logging.getLogger(__name__)

class TradePilotAgent:
    def __init__(self):
        self.workflow_app = get_workflow_app()
        logger.info("TradePilot Agentic AI - initialized.")

    def run(self, user_input: str) -> str:
        logger.info(f"Agent received input: '{user_input}'")
        try:
            initial_state: GraphState = {
                "user_query": user_input,
                "extracted_info": {},
                "scraping_status": "",
                "scraping_success": False,
                "mfn_data_available": False,
                "rag_documents_count": 0,
                "final_answer": "",
            }
            
            config_for_run = {"configurable": {"thread_id": str(uuid.uuid4())}}
            final_state = self.workflow_app.invoke(initial_state, config=config_for_run)
            
            # La réponse finale est directement dans l'état
            final_answer = final_state.get("final_answer", "Sorry, I couldn't generate a final answer.")
            logger.info("Agent execution completed.")
            return final_answer
            
        except Exception as e:
            logger.error(f"Error during agent execution: {e}")
            return f"Sorry, the agent encountered an error: {e}"

_agent_instance = None
def get_agent():
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = TradePilotAgent()
    return _agent_instance
