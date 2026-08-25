"""Shared text normalization used by training, prediction, and similarity search."""

import html
import re


def preprocess_text(text):
    """Normalize support text without removing domain-specific words."""
    if text is None:
        return ""

    value = html.unescape(str(text)).lower()
    value = re.sub(r"https?://\S+|www\.\S+", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)

    value = re.sub(r"(.)\1{3,}", r"\1\1", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def combine_ticket_text(subject, description):
    """Create the single text representation used throughout the ML system."""
    return preprocess_text(f"{subject or ''} {description or ''}")
