"""Schema analysis utility for extracting categorical options from judge instructions."""

import json
import logging
from functools import lru_cache
from typing import List

from databricks.rag_eval import context, env_vars
from server.utils.constants import VERSION

logger = logging.getLogger(__name__)

SCHEMA_ANALYSIS_SYSTEM_PROMPT = """You are an expert at analyzing judge instructions to extract the possible categorical outputs.

Your task is to analyze the given judge instruction and determine what categorical options the judge should return.

Return your analysis as a JSON object:
{
  "options": ["Pass", "Fail"]
}

Examples:
- "Return pass if good, fail if bad" → ["Pass", "Fail"]  
- "Rate as poor, fair, good, or excellent" → ["Poor", "Fair", "Good", "Excellent"]
- "Score from 1 to 5" → ["1", "2", "3", "4", "5"]
- "Answer yes or no" → ["Yes", "No"]

Guidelines:
- Extract the specific output values mentioned in the instruction
- Convert numeric ranges to categorical options (1-5 becomes ["1", "2", "3", "4", "5"])
- Default to ["Pass", "Fail"] if unclear
- Always return at least 2 options

Return only valid JSON."""


@lru_cache(maxsize=128)
@context.eval_context
def _extract_categorical_options_from_instruction(instruction: str) -> List[str]:
    env_vars.RAG_EVAL_EVAL_SESSION_CLIENT_NAME.set(f'judge-builder-v{VERSION}')
    managed_rag_client = context.get_context().build_managed_rag_client()
    
    user_prompt = f"""Analyze this judge instruction and extract the categorical options. Provide your analysis as JSON. Do not use any markdown. 
    <instruction>{instruction}</instruction>"""

    response = managed_rag_client.get_chat_completions_result(
        user_prompt=user_prompt, 
        system_prompt=SCHEMA_ANALYSIS_SYSTEM_PROMPT
    )
    
    if not response.output:
        logger.warning("No output from LLM, falling back to pass/fail")
        return ["Pass", "Fail"]
        
    # Parse LLM response
    try:
        analysis = json.loads(response.output.strip())
        options = analysis.get("options", ["Pass", "Fail"])
        
        # Validate options
        if not isinstance(options, list) or len(options) < 2:
            logger.warning(f"Invalid options: {options}, using pass/fail")
            return ["Pass", "Fail"]
            
        logger.info(f"LLM extracted options: {options}")
        return options
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM JSON response: {e}")
        return ["Pass", "Fail"]


def extract_categorical_options_from_instruction(instruction: str) -> List[str]:
    """Extract categorical options from judge instruction using LLM analysis.
    
    Args:
        instruction: The judge instruction text to analyze
        
    Returns:
        List of categorical options (e.g., ["Pass", "Fail"] or ["Poor", "Fair", "Good", "Excellent"])
        Falls back to ["Pass", "Fail"] if analysis fails.
    """
    try:
        return _extract_categorical_options_from_instruction(instruction)
    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        return ["Pass", "Fail"]


def is_binary_categorical_options(options: List[str]) -> bool:
    """Check if options represent binary categorical output.
    
    Args:
        options: List of categorical options
        
    Returns:
        True if exactly 2 options, False otherwise
    """
    return len(options) == 2
