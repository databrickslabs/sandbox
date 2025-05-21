import re
from dataclasses import dataclass
from typing import List, Optional

from . import token_utils, utils


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
    tokenizer_type: str
    tokenizer_model: str


class FileTokenCountHelper:
    def __init__(self, endpoint_name: str = None, tokenizer_type: str = None, tokenizer_model: str = None):
        """
        Initialize the FileTokenCounter with endpoint name or explicit tokenizer settings.

        Args:
            endpoint_name (str, optional): The name of the endpoint to determine the tokenizer type.
                                         Used to infer tokenizer type and model if not explicitly provided.
            tokenizer_type (str, optional): The type of tokenizer to use ('openai' or 'claude').
                                          If not provided, will be inferred from endpoint_name.
            tokenizer_model (str, optional): The specific model to use for tokenization.
                                           If not provided, will be inferred from tokenizer_type or endpoint_name.
        """
        self.endpoint_name = endpoint_name

        # Use explicit tokenizer settings if provided
        if tokenizer_type:
            self.tokenizer_type = tokenizer_type
            self.tokenizer_model = tokenizer_model or ('claude' if tokenizer_type == 'claude' else 'o200k_base')
        # Otherwise infer from endpoint_name
        elif endpoint_name:
            self.tokenizer_type, self.tokenizer_model = token_utils.determine_tokenizer_from_endpoint(endpoint_name)
        # Default to Claude if neither is provided
        else:
            self.tokenizer_type = 'claude'
            self.tokenizer_model = 'claude'

        # Create the token counter
        self.token_counter = token_utils.get_token_counter(self.tokenizer_type, self.tokenizer_model)

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
            tokenizer_type=self.tokenizer_type,
            tokenizer_model=self.tokenizer_model,
            input_file_token_count=token_count,
            input_file_token_count_without_sql_comments=token_count_without_sql_comments,
            input_file_content=content,
            input_file_content_without_sql_comments=content_without_sql_comments
        )
