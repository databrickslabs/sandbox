import re
from dataclasses import dataclass
from typing import List, Optional

from . import utils


@dataclass
class FileTokenMetadata:
    """Data class for storing metadata of a file with token counts."""
    input_file_number: Optional[int]
    input_file_path: str
    input_file_encoding: str
    input_file_content: str
    input_file_content_without_sql_comments: Optional[str]
    input_file_token_count: int
    input_file_token_count_without_sql_comments: Optional[int]
    tiktoken_encoding: str


class FileTokenCountHelper:
    def __init__(self, token_encoding: str = "o200k_base"):
        """Initialize the FileTokenCounter with a specified token encoding."""
        self.token_encoding = token_encoding
        self.token_counter = utils.TokenCounter(token_encoding)

    def process_directory(self, input_dir: str, file_encoding: Optional[str] = None,
                          is_sql: bool = True) -> List[FileTokenMetadata]:
        """
        Process all files in a directory and return a list of FileTokenMetadata objects with file details.

        Args:
            input_dir (str): The directory containing the files to be processed.
            file_encoding (Optional[str]): The encoding to use for reading the files. If not specified, the encoding is automatically detected using chardet.detect.
            is_sql (bool): Flag indicating whether the files are SQL files. If True, SQL comments will be removed for token counting.

        Returns:
            List[FileTokenMetadata]: A list of metadata objects for each processed file.
        """
        results = []
        for i, file_path in enumerate(utils.list_files_recursively(input_dir), start=1):
            sql_file_token_metadata = self.process_file(
                input_file_path=file_path, input_file_number=i, file_encoding=file_encoding, is_sql=is_sql)
            results.append(sql_file_token_metadata)
        return results

    def process_file(self, input_file_path: str, input_file_number: Optional[int] = None,
                     file_encoding: Optional[str] = None, is_sql: bool = True) -> FileTokenMetadata:
        """
        Process a file and return its details including token counts.

        Args:
            input_file_path (str): The path of the file to be processed.
            input_file_number (Optional[int]): The number of the input file. If not provided, it will be generated automatically.
            file_encoding (Optional[str]): The encoding to use for reading the file. If not specified, the encoding is automatically detected using chardet.detect.
            is_sql (bool): Flag indicating whether the file is a SQL file. If True, SQL comments will be removed for token counting.

        Returns:
            FileTokenMetadata: Metadata object containing file details and token counts.
        """
        content, input_file_encoding = utils.get_file_content(input_file_path, encoding=file_encoding)
        token_count = self.token_counter.count_tokens(content)

        content_without_sql_comments = None
        token_count_without_sql_comments = None

        if is_sql:
            content_without_sql_comments = utils.remove_sql_comments(content)
            content_without_sql_comments = re.sub(r'\s+', ' ', content_without_sql_comments)
            token_count_without_sql_comments = self.token_counter.count_tokens(content_without_sql_comments)

        return FileTokenMetadata(
            input_file_number=input_file_number,
            input_file_path=input_file_path,
            input_file_encoding=input_file_encoding,
            input_file_content=content,
            input_file_content_without_sql_comments=content_without_sql_comments,
            input_file_token_count=token_count,
            input_file_token_count_without_sql_comments=token_count_without_sql_comments,
            tiktoken_encoding=self.token_encoding
        )
