 
# models/llm_client.py
from groq import Groq
# import torch # For local model
# from transformers import AutoTokenizer, AutoModelForCausalLM # For local model
import logging

logger = logging.getLogger(__name__)

class GroqModelClient:
    """Client for interacting with Groq API."""
    def __init__(self, api_key, model_name):
        self.client = Groq(api_key=api_key)
        self.model_name = model_name

    def generate(self, messages, max_tokens=1024, temperature=0.7):
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            raise # Re-raise for handling upstream

# Placeholder for local Qwen model (if needed)
# class LocalQwenModelClient:
#     def __init__(self, model_name, ...): # Add necessary config
#         # Load tokenizer and model (similar to notebook)
#         self.tokenizer = AutoTokenizer.from_pretrained(...)
#         self.model = AutoModelForCausalLM.from_pretrained(...)
#         # Handle device placement, quantization etc.
#
#     def generate(self, messages, ...):
#         # Apply chat template, tokenize, generate (similar to notebook)
#         # Return generated text
#         pass

# Factory function to choose client
def get_llm_client(config):
    if config.GROQ_API_KEY:
        logger.info("Initializing Groq API client.")
        return GroqModelClient(config.GROQ_API_KEY, config.GROQ_MODEL_NAME)
    else:
        # Fallback or raise error if local model setup is complex
        raise ValueError("GROQ_API_KEY not found. Local model setup not implemented here.")
