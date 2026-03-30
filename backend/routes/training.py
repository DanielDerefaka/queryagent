"""
Training data endpoint — returns stats about accumulated training data.
"""

from fastapi import APIRouter

from queryagent.training import get_training_stats, load_training_dataset

router = APIRouter()


@router.get("/training/stats")
def training_stats():
    """Return statistics about the training data pipeline."""
    stats = get_training_stats()
    return stats


@router.get("/training/examples")
def training_examples(label: str = "positive", limit: int = 20):
    """Return recent training examples, optionally filtered by label."""
    valid_labels = {"positive", "negative"}
    label_filter = label if label in valid_labels else None

    examples = load_training_dataset(label_filter=label_filter)

    # Return most recent first
    examples.reverse()
    return {
        "label_filter": label_filter,
        "total": len(examples),
        "examples": examples[:limit],
    }
