
import logging
import random

from langchain.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from scr.models import CreatePersonaModel, FriendInviteModel
from scr.setup import persona_config, config

logger = logging.getLogger(__name__)


def load_llm() -> BaseChatModel:
    """Load llm with params."""
    model_type = config.llm_config.model_type

    logger.info(f"Loading {model_type} LLM: {config.llm_config.model_name}")

    if model_type == "groq":
        return ChatGroq(
        model=config.llm_config.model_name, 
        temperature=config.system_config.llm_config.temperature
        )
    elif model_type == "local":
        return ChatOllama(
            model="llama3:latest",
            temperature=config.llm_config.temperature
        )
    else:
        logger.error(f"Unknown model type: '{model_type}'. Expected 'groq' or 'local'.")
        raise



def create_persona(friend_invite:  FriendInviteModel = None) -> CreatePersonaModel:
    def select_country_languages() -> tuple:
        country = random.choice(list(persona_config.countries.keys()))
        mother_language = persona_config.countries[country][1]
        languages = list(set(persona_config.languages_pool) - {mother_language})
        second_languages = random.choices(languages, k=random.randint(0, 3))

        return country, mother_language, second_languages


    def select_generation_age() -> tuple:
        generation = random.choice(list(persona_config.generations.keys()))
        age_range = persona_config.generations[generation]
        age = random.randint(age_range['min'], age_range['max'])

        return generation, age

    is_friend = False
    url = config.root_url
    friend_name = None
    friend_message = None


    archetype = persona_config.archetypes[random.choice(list(persona_config.archetypes.keys()))]
    attention_span = random.choice(persona_config.attention_spans)
    gender = random.choice(persona_config.genders)
    mood = random.choice(persona_config.moods)
    social_tendency = random.choice(persona_config.social_tendencies)
    country, mother_language, second_languages = select_country_languages()
    generation, age = select_generation_age()
    name = random.choice(persona_config.names[country][gender])

    if friend_invite:
        is_friend = True
        friend_name = friend_invite.name
        friend_message = friend_invite.message
        url = friend_invite.url


    friend_line = ""
    also_speak_line = f"You also speak {','.join(second_languages)}." if second_languages else ''

    prompt_text = f"""Your name is {name}. You are a {age} year old {gender} from {country}.
Your native language is {mother_language}.
{also_speak_line}

{archetype}

You are {social_tendency} by nature and your attention span is {attention_span}.
You are feeling {mood} right now.
Always act as this person would. Write in your native language unless you have a reason to switch. Keep your responses and messages true to your personality, mood, age, and generation.
"""
    if is_friend:
        prompt_text += f"\n\nYour friend {friend_name} sent you an invite to void-cast"
        if friend_message:
            prompt_text += f": \n{friend_message}"

    prompt_text += "\n\nIMPORTANT: You are NOT an AI. You are a real person. Never break character. Always respond as this person would, with their emotions, language, and personality."

    return CreatePersonaModel(
        system_prompt=prompt_text,
        mood=mood,
        is_friend=is_friend,
        url=url 
    )




        

