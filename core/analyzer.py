# core/analyzer.py
from models.llm_client import get_llm_client # Import the factory/client
import logging

logger = logging.getLogger(__name__)

class LegalDocumentAnalyzer:
    def __init__(self, retriever, config):
        self.retriever = retriever
        self.config = config
        self.model = get_llm_client(config)
        self.system_prompt = config.SYSTEM_PROMPT
        logger.info("LegalDocumentAnalyzer initialized!")

    def ask(self, question: str) -> str:
        """Simple method to ask a question and get an answer."""
        # --- Ajout: Vérification du retriever ---
        if self.retriever is None:
            error_msg = "The RAG system is not ready (retriever is None). Indexes might be missing or failed to load."
            logger.error(error_msg)
            return error_msg
        # --- Fin de l'ajout ---
        
        try:
            # Get context from retriever
            context = self._get_context(question)

            # Create messages for the model
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"""Based on the following context from legal documents, please answer my question:

Question: {question}

Context: {context}

Please provide a clear, helpful answer based on this information."""}
            ]

            # Get response from model
            answer = self.model.generate(messages)
            return answer

        except Exception as e:
            logger.error(f"Error in ask: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    def _get_context(self, question: str) -> str:
        """Get and format context from retriever, including original URLs if available."""
        try:
            docs = self.retriever.get_relevant_documents(question)

            if not docs:
                return "No relevant documents found."

            context_parts = []
            for doc in docs:
                if hasattr(doc, 'page_content'):
                    # Extraire les métadonnées
                    title = doc.metadata.get('title', 'Unknown Title')
                    source = doc.metadata.get('source', 'Unknown Source')
                    page = doc.metadata.get('page', 'N/A')
                    # --- Nouveau : Récupérer l'URL originale ---
                    original_url = doc.metadata.get('original_url', None)
                    # --- Fin du nouveau ---
                    
                    # Construire la partie du contexte
                    # --- Modification : Inclure le lien dans le texte du contexte ---
                    source_info = f"Document: {title} (Source: {source}, Page: {page})"
                    if original_url:
                         # Vous pouvez formater le lien comme vous voulez.
                         # Option 1 : Texte brut
                         # source_info += f" (Original URL: {original_url})"
                         # Option 2 : Format Markdown (si le LLM le comprend ou si l'interface le gère)
                         # source_info += f" (Original URL: [{os.path.basename(original_url)}]({original_url}))"
                         # Option 3 : Format simple pour le LLM
                         source_info += f" (URL: {original_url})"
                         
                    context_part = f"{source_info}\nContent: {doc.page_content[:500]}..." # Limiter la longueur du contenu
                    context_parts.append(context_part)
                    # --- Fin de la modification ---
                else:
                    context_parts.append(str(doc))

            return "\n---\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return f"Error retrieving context: {str(e)}"

