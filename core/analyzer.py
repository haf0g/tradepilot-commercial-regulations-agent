# core/analyzer.py
from models.llm_client import get_llm_client # Import the factory/client
import logging

logger = logging.getLogger(__name__)

class LegalDocumentAnalyzer:
    def __init__(self, retriever, config):
        self.retriever = retriever
        self.config = config
        self.model = get_llm_client(config) # Use factory function
        self.system_prompt = config.SYSTEM_PROMPT
        logger.info("LegalDocumentAnalyzer initialized!")

    def ask(self, question: str) -> str:
        """Simple method to ask a question and get an answer."""
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
        """Get and format context from retriever."""
        try:
            # Assuming retriever has get_relevant_documents or similar
            docs = self.retriever.get_relevant_documents(question)

            if not docs:
                return "No relevant documents found."

            context_parts = []
            for doc in docs:
                if hasattr(doc, 'page_content'):
                    # Extract metadata for better context
                    title = doc.metadata.get('title', 'Unknown Title')
                    source = doc.metadata.get('source', 'Unknown Source')
                    page = doc.metadata.get('page', 'N/A')
                    # You can format this as needed, e.g., include snippets
                    context_parts.append(f"Document: {title} (Source: {source}, Page: {page})\nContent: {doc.page_content[:500]}...") # Limit content length
                # Handle other doc types if necessary
                else:
                    context_parts.append(str(doc))

            return "\n---\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return f"Error retrieving context: {str(e)}"

