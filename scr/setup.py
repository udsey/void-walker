import os
from pydantic import BaseModel
import yaml
from dotenv import load_dotenv
import logging
from scr.models import PersonaConfigModel, ConfigModel

import logging

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),                          # console
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("WDM").setLevel(logging.WARNING)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),                          # console
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("WDM").setLevel(logging.WARNING)


def load_config_file(filename: str) -> dict:
    """Load config fime from name."""
    with open(os.path.join(BASE_DIR, filename), "r") as f:
        config = yaml.safe_load(f)
    return config


def save_config(config: BaseModel, filename: str):
    """Save config file."""
    with open(os.path.join(BASE_DIR, filename), 'w') as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False)


BASE_DIR = os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")


persona_config = load_config_file('persona_config.yaml')
persona_config = PersonaConfigModel(**persona_config)
config = load_config_file('config.yaml')
config = ConfigModel(**config)

