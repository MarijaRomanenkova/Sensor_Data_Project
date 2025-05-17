import json
import logging
from datetime import datetime
from typing import Any, Dict


def setup_logging(name: str) -> logging.Logger:
    """Set up and return a logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def format_timestamp(timestamp: datetime) -> str:
    """Format datetime object to ISO format string."""
    return timestamp.isoformat()


def create_metadata(batch_id: str) -> Dict[str, Any]:
    """Create metadata dictionary for a batch of records."""
    return {"batch_id": batch_id, "processed_at": format_timestamp(datetime.utcnow())}


def save_processing_stats(stats: Dict[str, int], filename: str):
    """Save processing statistics to a JSON file."""
    try:
        with open(filename, "w") as f:
            json.dump(stats, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save processing stats: {str(e)}")
        raise


def load_processing_stats(filename: str) -> Dict[str, int]:
    """Load processing statistics from a JSON file."""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logging.error(f"Failed to load processing stats: {str(e)}")
        raise
