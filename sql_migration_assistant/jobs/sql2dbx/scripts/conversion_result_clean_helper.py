from typing import Callable, List


class ConversionResultCleanHelper:
    TRIPLE_BACK_QUOTES_WITH_PYTHON = "```python"
    TRIPLE_BACK_QUOTES = "```"

    def get_udf_functions(self) -> List[Callable[[str], str]]:
        """
        Returns a list of UDF functions for use in PySpark.
        """
        return [self.clean_python_code_blocks]

    def clean_python_code_blocks(self, text: str) -> str:
        """
        Extracts code blocks delimited by `python` and removes any intervening `python` occurrences.
        """
        if text is None:
            return None

        delimiter_count = text.count(self.TRIPLE_BACK_QUOTES_WITH_PYTHON)

        if delimiter_count == 0:
            # No code blocks found, return the original text
            return text
        elif delimiter_count == 1:
            # Only one code block, extract it
            parts = text.split(self.TRIPLE_BACK_QUOTES_WITH_PYTHON)
            result = parts[1].split(self.TRIPLE_BACK_QUOTES)[0]
        else:
            # Multiple code blocks, concatenate them
            parts = text.split(self.TRIPLE_BACK_QUOTES_WITH_PYTHON)
            parts = parts[1:]  # Remove the content before the first ```python

            # If the last element contains triple back quotes, remove everything after the last ```
            if self.TRIPLE_BACK_QUOTES in parts[-1]:
                parts[-1] = parts[-1].split(self.TRIPLE_BACK_QUOTES)[0]

            # Join the parts with newlines
            result = "\n".join(parts)

        # Remove leading newline if it exists
        if result.startswith("\n"):
            result = result[1:]

        return result
