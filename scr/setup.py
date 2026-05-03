import os
from pydantic import BaseModel
import yaml
from dotenv import load_dotenv
import logging


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


