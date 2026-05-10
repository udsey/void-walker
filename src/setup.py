"""Setup."""

import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

from src.models import ConfigModel, PersonaConfigModel

load_dotenv()


# ~~~~~~~~~~~~~~~~~~ Logging configurations ~~~~~~~~~~~~~~~~~~

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("WDM").setLevel(logging.WARNING)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("WDM").setLevel(logging.WARNING)


# ~~~~~~~~~~~~~~~~~~ Utils ~~~~~~~~~~~~~~~~~~

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
SQL_DIR = Path(os.path.join(BASE_DIR, "src/db/sql"))
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

os.makedirs(DATA_DIR, exist_ok=True)

path = os.path.join(BASE_DIR, 'configs/persona_config.yaml')
persona_config = load_config_file(path)
persona_config = PersonaConfigModel(**persona_config)
path = os.path.join(BASE_DIR, 'configs/config.yaml')
config = load_config_file(path)
config = ConfigModel(**config)

