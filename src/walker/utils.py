"""Utils."""

import logging
from typing import Callable, Literal

import redis
from dotenv import load_dotenv
from langchain.chat_models import BaseChatModel
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from src.models import AgentState
from src.setup import ENV, config

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

host = 'localhost' if ENV == 'local' else 'redis'
redis_sync = redis.Redis(host=host, port=6379, decode_responses=True)


def publish_session(session_id: str) -> None:
    """Publish session."""
    redis_sync.sadd("observer:sessions", session_id)
    redis_sync.expire("observer:sessions", 3600)
    redis_sync.publish("observer:sessions", session_id)


def remove_session(session_id: str) -> None:
    """Remove session from Redis."""
    redis_sync.srem("observer:sessions", session_id)



def publish_current_url(session_id: str, current_url: str) -> None:
    """Publish current url."""
    redis_sync.setex(f"observer:session:{session_id}:url", 360, current_url)
    redis_sync.publish(f"observer:session:{session_id}", current_url)


def publish_state(session_id: str, state: AgentState) -> None:
    """Publish graph state."""
    state = state.model_dump_json()
    redis_sync.setex(f"observer:session:{session_id}:graph",
                     360, state)
    redis_sync.publish(f"observer:session:{session_id}", state)

