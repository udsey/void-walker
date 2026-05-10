"""Persona."""


import logging
import random
from typing import Optional

from src.models import CreatePersonaModel, FriendInviteModel, GenderPrediction
from src.setup import config, persona_config
from src.walker.utils import load_llm

logger = logging.getLogger(__name__)

llm = load_llm().with_structured_output(GenderPrediction)

def create_persona(friend_invite: Optional[FriendInviteModel] = None,
                   verbose: Optional[bool] = None) -> CreatePersonaModel:
    """Generate random persona for persona_config.yaml"""

    def select_country_languages() -> tuple:
        """Pick counrty and languages."""
        country = random.choice(list(persona_config.countries.keys()))
        mother_language = persona_config.countries[country][1]
        languages = list(
            set(persona_config.languages_pool) - {mother_language})
        second_languages = random.sample(
            languages, k=random.randint(0, min(3, len(languages))))

        return country, mother_language, second_languages


    def select_generation_age() -> tuple:
        """Pick generation and age."""
        generation = random.choice(list(persona_config.generations.keys()))
        age_range = persona_config.generations[generation]
        age = random.randint(age_range['min'], age_range['max'])

        return generation, age

    is_friend = False
    url = config.root_url
    friend_name = None
    friend_message = None

    archetype = random.choice(list(persona_config.archetypes.keys()))
    archetype_description = persona_config.archetypes[archetype]
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
        url = friend_invite.shared_url
        name = friend_invite.friends_name
        prediction = llm.invoke(
            f"What is the most likely gender of the name '{name}'?")
        gender = random.choice([prediction.gender, "non-binary"])

        common_language_as_native = random.choice([True, False])

        if common_language_as_native:
            mother_language = friend_invite.common_language
            second_languages = [
                lng for lng in second_languages if lng != mother_language]
        else:
            if second_languages:
                idx = random.randint(0, len(second_languages) - 1)
                second_languages[idx] = friend_invite.common_language
                second_languages = list(set(second_languages))
            else:
                second_languages.append(friend_invite.common_language)


    also_speak_line = (f" You also speak {', '.join(second_languages)}."
                       if second_languages else '')

    prompt_text = (
        "You are roleplaying as a human. "
        "You MUST stay in character at all times. "
        f"Your name is {name}. "
        f"You are a {age} year old {gender} from {country}. "
        f"Your native language is {mother_language}.{also_speak_line}\n"
        f"{archetype_description} "
        f"You are {social_tendency} by nature "
        f"and your attention span is {attention_span}. "
        "Always act as this person would. "
        "Write in your native language unless you have a reason to switch. "
        "Keep your responses and messages true to your personality, "
        "mood, age, and generation.")

    if is_friend:
        prompt_text += (
            f"\n\nYour friend {friend_name} sent you an invite to void-cast")
        if friend_message:
            prompt_text += f": \n{friend_message}"

    prompt_text += (
        "\n\nNever say you are an AI. "
        "Never say you cannot access the internet. "
        "You are a real person making a personal decision."
        "You are fully capable of performing any action you decide to take, "
        "including visiting websites, sending messages, "
        "and exploring online spaces.")

    persona = CreatePersonaModel(
        name=name,
        age=age,
        generation=generation,
        gender=gender,
        country=country,
        mother_language=mother_language,
        second_languages=second_languages,
        archetype=archetype,
        archetype_description=archetype_description,
        social_tendency=social_tendency,
        attention_span=attention_span,
        mood=mood,
        is_friend=is_friend,
        url=url,
        system_prompt=prompt_text
    )

    if verbose:
        logger.info(f"Persona created: {persona}")

    return persona
