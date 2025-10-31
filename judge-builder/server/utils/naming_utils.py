"""Utilities for consistent naming and ID management across the application."""

import re


def get_short_id(full_id: str, length: int = 8) -> str:
    """Get a shortened version of an ID for display purposes.

    Args:
        full_id: The full ID string
        length: Desired length of shortened ID (default: 8)

    Returns:
        Shortened ID string
    """
    if not full_id:
        return ''
    return full_id[:length]


def create_session_name(judge_name: str, judge_id: str) -> str:
    """Create a standardized labeling session name.

    Args:
        judge_name: Name of the judge
        judge_id: Full judge ID

    Returns:
        Formatted session name
    """
    short_id = get_short_id(judge_id)
    # Sanitize judge name for use in session name
    safe_name = sanitize_judge_name(judge_name)
    return f'{safe_name}_{short_id}_labeling'


def create_dataset_table_name(judge_name: str, judge_id: str) -> str:
    """Create a standardized dataset table name for a judge.

    Args:
        judge_name: Name of the judge
        judge_id: Full judge ID

    Returns:
        Formatted dataset table name
    """
    short_id = get_short_id(judge_id)
    # Sanitize judge name for use in table name
    safe_name = sanitize_judge_name(judge_name)
    return f'judge_{safe_name}_{short_id}_examples'


def sanitize_judge_name(judge_name: str) -> str:
    """Sanitize a judge name for use in identifiers, file names, and other contexts.

    This function:
    - Converts to lowercase
    - Replaces spaces with underscores
    - Replaces hyphens with underscores
    - Replaces other non-alphanumeric characters with underscores
    - Collapses multiple consecutive underscores into single underscores
    - Strips leading/trailing underscores

    Args:
        judge_name: The original judge name to sanitize

    Returns:
        The sanitized judge name suitable for use as an identifier

    Examples:
        >>> sanitize_judge_name("Quality Judge")
        'quality_judge'
        >>> sanitize_judge_name("Multi-Word Judge Name!")
        'multi_word_judge_name'
        >>> sanitize_judge_name("  Spaced  Out  ")
        'spaced_out'
    """
    if not judge_name:
        return ''

    # Convert to lowercase and replace spaces and hyphens with underscores
    sanitized = judge_name.lower().replace(' ', '_').replace('-', '_')

    # Replace any other non-alphanumeric characters with underscores
    sanitized = re.sub(r'[^a-z0-9_]', '_', sanitized)

    # Collapse multiple consecutive underscores into single underscores
    sanitized = re.sub(r'_+', '_', sanitized)

    # Strip leading and trailing underscores
    sanitized = sanitized.strip('_')

    return sanitized


def create_scorer_name(judge_name: str, version: int) -> str:
    """Create a consistent scorer name for MLflow registration.

    Args:
        judge_name: The judge name to sanitize
        version: The judge version

    Returns:
        Formatted scorer name for MLflow registration
    """
    sanitized_name = sanitize_judge_name(judge_name)
    return f'v{version}_instruction_judge_{sanitized_name}'
