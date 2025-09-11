# ui/interface.py
import gradio as gr
from orchestrator.agent import get_agent
import logging

logger = logging.getLogger(__name__)

def create_interface():
    """Creates and returns the Gradio interface."""
    
    agent = get_agent()

    def process_question(question):
        if not question or not question.strip():
            return "### Error\nPlease enter a question about trade regulations."
        logger.info(f"Processing question with Agentic AI: {question}")
        return agent.run(question)

    iface = gr.Interface(
        fn=process_question,
        inputs=gr.Textbox(
            label="Ask a Trade Regulation Question",
            placeholder="E.g., Explain the rules of origin for exporting olives from Morocco to the USA.",
            lines=3
        ),
    
        outputs=gr.Markdown(
            label="Answer",
            value="### Welcome\nPlease enter your question above and click 'Submit'.",
            visible=True,
            elem_id="answer-markdown"
        ),
        css="""
        #answer-markdown {
            min-height: 300px; /* Ajustez cette valeur si necessaire */
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            overflow-y: auto; /* Ajoute un ascenseur si le contenu est trop long */
        }
        """,
        title="TradePilot Agentic AI Assistant",
        description="An AI assistant that can dynamically fetch and analyze trade documents based on your query.",
        examples=[
            "What are the documents I need to send saffron from Morocco to China",
            "What are the rules of origin for exporting olive oil from Morocco to the USA?",
            "How can I certify the origin of textiles exported from Morocco to the EU?",
            "What documents are needed for a Certificate of Origin for USA-Morocco trade?",
        ],
        theme="soft"
    )
    return iface
