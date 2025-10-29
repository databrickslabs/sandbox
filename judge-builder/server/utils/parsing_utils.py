"""Parsing utilities for extracting data from various formats."""

import json
from typing import Any, Optional

from mlflow.entities import Feedback, Trace

from server.utils.naming_utils import create_scorer_name, sanitize_judge_name


def extract_text_from_data(data: Any, field_type: str) -> str:
    """Extract text from trace data, handling various formats.

    Args:
        data: The data to extract from (can be dict, string, or other)
        field_type: Either 'request' or 'response' to determine which keys to try

    Returns:
        Extracted text as string
    """
    if data is None:
        return ''

    # If it's already a string, try to parse as JSON first
    if isinstance(data, str):
        try:
            parsed_data = json.loads(data)
            # If successful, continue with dict logic
            data = parsed_data
        except (json.JSONDecodeError, ValueError):
            # If JSON parsing fails, return the string as-is
            return data

    # Now handle dict case
    if isinstance(data, dict):
        # Define the keys to try based on field type
        if field_type == 'request':
            keys_to_try = ['request', 'inputs', 'input', 'prompt']
        else:  # response
            keys_to_try = ['response', 'outputs', 'output', 'content', 'text']

        # Try each key in order
        for key in keys_to_try:
            if key in data:
                value = data[key]
                # If the value is a dict or list, convert to string
                if isinstance(value, (dict, list)):
                    return json.dumps(value)
                else:
                    return str(value)

        # If no specific keys found, return the full dict as string
        return json.dumps(data)

    # For any other type, convert to string
    return str(data)


def extract_request_from_trace(trace) -> str:
    """Extract request text from an MLflow trace object.

    Args:
        trace: MLflow trace object with data and info attributes

    Returns:
        Extracted request text as string
    """
    # Try to get request data from trace.data.request first, fall back to trace.info.request_preview
    request_data = (
        trace.data.request if hasattr(trace.data, 'request') else trace.info.request_preview
    )
    return extract_text_from_data(request_data, 'request')


def extract_response_from_trace(trace) -> str:
    """Extract response text from an MLflow trace object.

    Args:
        trace: MLflow trace object with data and info attributes

    Returns:
        Extracted response text as string
    """
    # Try to get response data from trace.data.response first, fall back to trace.info.response_preview
    response_data = (
        trace.data.response if hasattr(trace.data, 'response') else trace.info.response_preview
    )
    return extract_text_from_data(response_data, 'response')


def get_human_feedback_from_trace(judge_name: str, trace: Trace) -> Optional[Feedback]:
    """Extract human feedback from a trace's assessments.

    Args:
        judge_name: Name of the judge
        trace: Trace object with assessments

    Returns:
        Feedback object if human feedback found, None otherwise
    """
    if not trace.info.assessments:
        return None

    # Normalize judge name for comparison
    normalized_judge_name = sanitize_judge_name(judge_name)

    for assessment in trace.info.assessments:
        if assessment.name == normalized_judge_name and assessment.source.source_type == 'HUMAN':
            return assessment

    return None


def get_scorer_feedback_from_trace(judge_name: str, judge_version: int, trace: Trace) -> Optional[Feedback]:
    """Extract scorer/LLM judge feedback from a trace's assessments.

    Args:
        judge_name: Name of the judge
        judge_version: Version of the judge
        trace: Trace object with assessments

    Returns:
        Feedback object if scorer feedback found, None otherwise
    """
    if not trace.info.assessments:
        return None

    # Create the expected scorer name
    scorer_name = create_scorer_name(judge_name, judge_version)

    for assessment in trace.info.assessments:
        if (assessment.name == scorer_name and
            assessment.source.source_type == 'LLM_JUDGE'):
            return assessment

    return None


def assessment_has_error(assessment) -> bool:
    """Check if an assessment has an error.

    Args:
        assessment: Assessment object to check

    Returns:
        True if assessment has an error, False otherwise
    """
    return assessment.error is not None
