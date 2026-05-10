"""Utils."""

import logging
from typing import Callable, Literal

from dotenv import load_dotenv
from langchain.chat_models import BaseChatModel
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from src.setup import config

logger = logging.getLogger(__name__)

load_dotenv()

def load_llm() -> BaseChatModel:
    """Load llm with params."""
    model_type = config.llm_config.model_type

    logger.info(f"Loading {model_type} LLM: {config.llm_config.model_name}")

    if model_type == "groq":
        return ChatGroq(
        model=config.llm_config.model_name,
        temperature=config.llm_config.temperature
        )
    elif model_type == "local":
        return ChatOllama(
            model=config.llm_config.model_name,
            temperature=config.llm_config.temperature
        )
    elif model_type == "gemini":
        return ChatGoogleGenerativeAI(
            model=config.llm_config.model_name,
            temperature=config.llm_config.temperature
        )
    elif model_type == "deepseek":
        return ChatDeepSeek(
            model=config.llm_config.model_name,
            temperature=config.llm_config.temperature,
            extra_body={"thinking": {"type": "disabled"}}
        )
    else:
        logger.error(f"Unknown model type: '{model_type}")
        raise ValueError


def register(_name: str, _type: Literal["node", "router", "tool"]):
        """Wrapper to add attributes to graph tools, routers and nodes."""
        def decorator(func: Callable):
            func._name = _name
            func._type = _type
            return func
        return decorator


def create_map(target, _type: str) -> dict:
    """Create map {func_name: func}"""
    func_map = {}
    for name in dir(target):
        try:
            method = getattr(target, name)
            if (callable(method)
                and hasattr(method, '_type')
                and getattr(method, '_type') == _type):
                func_map[getattr(method, '_name')] = method
        except Exception:
            continue
    return func_map
