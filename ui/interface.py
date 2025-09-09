# ui/interface.py
import gradio as gr
# from core.analyzer import LegalDocumentAnalyzer # Plus nécessaire ici
from orchestrator.agent import get_agent # Importer l'agent
import logging

logger = logging.getLogger(__name__)

def create_interface():
    """Creates and returns the Gradio interface."""
    
    # Obtenir l'instance de l'agent (cela initialise l'agent LangGraph)
    agent = get_agent()

    # --- Nouvelle fonction de traitement utilisant l'agent ---
    def process_question(question):
        if not question or not question.strip():
            return "Please enter a question about trade regulations."
        logger.info(f"Processing question with Agentic AI: {question}")
        # Appeler la méthode run de l'agent (TradePilotAgent.run)
        # qui exécute le workflow LangGraph
        return agent.run(question)
    # --- Fin de la nouvelle fonction ---

    # --- Configuration de l'interface Gradio ---
    iface = gr.Interface(
        fn=process_question, # Utilise la nouvelle fonction
        inputs=gr.Textbox(
            label="Ask a Trade Regulation Question",
            placeholder="E.g., Explain the rules of origin for exporting olives from Morocco to the USA.",
            lines=3
        ),
        outputs=gr.Textbox(label="Answer", lines=10), # Un peu plus de lignes pour des réponses détaillées
        title="TradePilot Agentic AI Assistant",
        description="An AI assistant that can dynamically fetch and analyze trade documents based on your query.",
        examples=[
            "What are the rules of origin for exporting olive oil from Morocco to the USA?",
            "How can I certify the origin of textiles exported from Morocco to the EU?",
            "What documents are needed for a Certificate of Origin for USA-Morocco trade?",
            "Explain the tariff shifts for agricultural products under the USMCA."
        ],
        theme="soft"
    )
    return iface