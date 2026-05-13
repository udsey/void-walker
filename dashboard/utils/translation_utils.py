"""On-demand story translation."""

import copy
import logging
from typing import Any

from deep_translator import LibreTranslator
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def apply_to_dict(obj, func, *args, **kwargs) -> Any:
    if isinstance(obj, dict):
        return {key: apply_to_dict(value, func, *args, **kwargs)
                for key, value in obj.items()}
    elif isinstance(obj, list):
        return [apply_to_dict(item, func, *args, **kwargs) for item in obj]
    elif isinstance(obj, str):
        return func(obj, *args, **kwargs)
    else:
        return obj


class StoryTranslator:
    """Handles on-demand story translation."""

    def __init__(self) -> None:
        self.translator = None
        self._connect()

    def _connect(self) -> None:
        """Connect to LibreTranslate service."""
        try:
            self.translator = LibreTranslator(
                custom_url='http://libretranslate:5000/',
                source='auto',
                target='en'
            )
            self.translator.translate("test text")

            logger.info("Successfully connected to LibreTranslate service")
        except Exception:
            try:
                self.translator = LibreTranslator(
                    custom_url='http://localhost:5000/',
                    source='auto',
                    target='en'
                )
                self.translator.translate("test text")
                logger.info("Successfully connected to LibreTranslate service")
            except Exception as e:
                self.translator = None
                logger.error(f"Failed to connect to LibreTranslate: {e}")

    def _translate_text(self, text: str, target_lang: str = 'en') -> str:
        """Translate a single text string."""
        if not text or not text.strip() or not self.translator:
            return text

        try:
            if len(text) > 5000:
                chunks = self._split_text(text, 5000)
                translated_chunks = [self.translator.translate(chunk)
                                     for chunk in chunks]
                return ' '.join(translated_chunks)
            else:
                return self.translator.translate(text)
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text


    def _split_text(self, text: str, chunk_size: int) -> list:
        """Split long text into chunks without breaking sentences."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 > chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks


    def translate_story(self, story_data: dict,
                        target_lang: str = 'en') -> dict:
        """Translate entire story dictionary on-demand."""
        if not self.translator:
            logger.warning("Translator not available, returning original")
            return story_data

        logger.info(f"Starting translation: {story_data}")
        story = copy.deepcopy(story_data)
        translated = apply_to_dict(story,
                                   self._translate_text,
                                   target_lang=target_lang)


        return translated


translator = StoryTranslator()
