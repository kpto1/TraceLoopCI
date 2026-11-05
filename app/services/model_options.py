"""Bound evaluation output without sending vendor options to other providers."""

from urllib.parse import urlparse


def evaluation_options(url: str, max_tokens: int) -> dict:
    if not 1 <= max_tokens <= 8192:
        raise ValueError("Evaluation max_tokens must be between 1 and 8192")
    options = {"max_tokens": max_tokens}
    if urlparse(url).hostname == "api.deepseek.com":
        options["thinking"] = {"type": "disabled"}
    return options
