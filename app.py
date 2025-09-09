# app.py
import os
import logging
# Importer config pour vérifier la clé API
import config 
# Importer uniquement ce qui est nécessaire pour l'interface
from ui.interface import create_interface

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting the Agentic TradePilot Application...")

    # 1. Vérifier la clé API (toujours important)
    if not config.GROQ_API_KEY:
        logger.error("GROQ_API_KEY environment variable is not set.")
        print("ERROR: GROQ_API_KEY environment variable is not set.")
        exit(1)
    else:
        logger.info("GROQ API key found.")

    # 2. Informer que l'agent gérera le scraping/RAG dynamiquement
    logger.info("The Agentic AI will handle document fetching and RAG updates dynamically.")
    print("The Agentic AI will handle document fetching and RAG updates dynamically.")

    # 3. Lancer l'interface
    # create_interface va obtenir l'agent via get_agent()
    logger.info("Step: Launching Gradio interface...")
    iface = create_interface()
    iface.launch(share=True) # Set share=False for local only

if __name__ == "__main__":
    main()