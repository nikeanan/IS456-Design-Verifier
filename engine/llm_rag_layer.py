# engine/llm_rag_layer.py
import json
import os
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class LLMRagLayer:
    """
    Evaluates ambiguous IS code clauses using an LLM (Large Language Model) 
    and RAG (Retrieval-Augmented Generation).
    """
    def __init__(self, provider="openai"):
        self.provider = provider
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if OpenAI and self.api_key else None
        
    def query_clause(self, element_context: dict, clause: str) -> dict:
        """
        Query the LLM for a specific clause given the element context.
        Returns a dictionary with 'status' (PASS/FAIL/ACTION), 'reasoning', and 'suggestions'.
        """
        if not self.client:
            return {
                "status": "ACTION REQUIRED",
                "reasoning": f"LLM client not configured. Missing API key for clause: {clause}",
                "suggestions": ["Manually verify clause requirements."]
            }
            
        prompt = (
            f"You are a structural engineering assistant. Evaluate the following clause:\n"
            f"Clause: {clause}\n"
            f"Context: {json.dumps(element_context, indent=2)}\n"
            "Return a JSON with 'status' (PASS/FAIL/ACTION), 'reasoning', and a list of 'suggestions'."
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "status": "ACTION REQUIRED",
                "reasoning": f"LLM evaluation failed: {e}",
                "suggestions": ["Manually verify clause requirements."]
            }
