import logging
import os
import re
import sys
from typing import Optional, Tuple

import chardet
import tiktoken


class TokenCounter:
    def __init__(self, token_encoding_name: str = "cl100k_base"):
        """Initialize the TokenCounter with a specified token encoding."""
        self.encoding = tiktoken.get_encoding(token_encoding_name)

    def count_tokens(self, string: str) -> int:
        """Returns the number of tokens in a text string."""
        return len(self.encoding.encode(string))


def setup_logger(name, level=logging.INFO):
    """Function to setup a logger that outputs to stdout"""
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)
    return logger


def list_files_recursively(input_dir: str) -> list[str]:
    """
    Recursively list all files in the specified directory.

    Args:
        input_dir (str): The directory to search for files.

    Returns:
        list[str]: A list of file paths.
    """
    all_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.isfile(file_path):
                all_files.append(file_path)
    return all_files


def get_file_content(input_file_path: str, encoding: Optional[str] = None) -> Tuple[str, str]:
    """
    Returns the content of a specified file as a string along with its encoding.

    Args:
        input_file_path (str): The path of the file to read.
        encoding (Optional[str]): The encoding to use for reading the file. If not specified, chardet.detect is used.

    Returns:
        Tuple[str, str]: A tuple containing the file content and its encoding.
    """
    with open(input_file_path, 'rb') as file:
        raw_data = file.read()
        if encoding is None:
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'  # Use 'utf-8' if encoding detection fails
        content = raw_data.decode(encoding, errors='replace')
    return content, encoding


def remove_sql_comments(sql_text: str) -> str:
    """
    Removes both line and block comments from SQL text.

    Args:
        sql_text (str): The SQL text to clean.

    Returns:
        str: The SQL text without comments.
    """
    no_line_comments = re.sub(r'--.*', '', sql_text)
    no_comments = re.sub(r'/\*.*?\*/', '', no_line_comments, flags=re.DOTALL)
    no_comments = re.sub(r'\n\s*\n', '\n\n', no_comments)  # Remove multiple empty lines
    return no_comments


def parse_number_ranges(input_string: str) -> list[int]:
    """Parses a comma-separated string into a list of integers.
    The string can contain single integers or hyphen-separated ranges (e.g., "5-8").

    Args:
        input_string: The string containing comma-separated integers or ranges.

    Returns:
        A list containing all integers found in input_string.
    """
    result_numbers = []
    if input_string:  # Process only if input is not empty
        for part in input_string.split(','):
            part = part.strip()  # Remove extra whitespace
            if '-' in part:  # Range detected
                start_str, end_str = part.split('-')
                start, end = int(start_str), int(end_str)
                result_numbers.extend(range(start, end + 1))  # Add range of numbers
            else:
                result_numbers.append(int(part))  # Add single number
    return result_numbers
