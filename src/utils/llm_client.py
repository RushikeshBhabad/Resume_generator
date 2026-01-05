"""
LLM client configuration using Groq (free tier).
"""
import os
from typing import Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()


def get_llm(
    model: str = "openai/gpt-oss-120b",
    temperature: float = 0,
    max_tokens: int = 4096
) -> ChatGroq:
    """
    Get configured LLM instance.
    
    Args:
        model: Model name to use
        temperature: Sampling temperature (0 for deterministic)
        max_tokens: Maximum tokens to generate
        
    Returns:
        Configured ChatGroq instance
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found. Please set it in your .env file.\n"
            "Get a free API key from: https://console.groq.com/keys"
        )
    
    return ChatGroq(
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = "openai/gpt-oss-120b",
    temperature: float = 0
) -> str:
    """
    Make a simple LLM call.
    
    Args:
        system_prompt: System message
        user_prompt: User message
        model: Model to use
        temperature: Sampling temperature
        
    Returns:
        LLM response text
    """
    llm = get_llm(model=model, temperature=temperature)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    response = llm.invoke(messages)
    return response.content


# Available Groq models (free tier)
AVAILABLE_MODELS = [
    "llama-3.3-70b-versatile",  # Best quality
    "llama-3.1-8b-instant",     # Faster
    "mixtral-8x7b-32768",       # Good balance
    "gemma2-9b-it",             # Google's model
]
