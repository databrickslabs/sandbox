import ast
import logging
from typing import List, Optional, Tuple, Union

from .utils import setup_logger


class CellSplitHelper:
    """
    A helper class for splitting Python code into Databricks notebook cells.

    This class provides functionality to intelligently split Python code into
    separate cells, considering code structure, comments, and blank lines.

    Attributes:
        COMMAND_MARKER (str): The marker used to denote the start of a new cell in Databricks notebooks.
        logger (logging.Logger): Logger for the class.

    Main methods:
        split_cells: Splits the input code into Databricks notebook cells.
    """
    COMMAND_MARKER = "# COMMAND ----------"

    def __init__(self, log_level: Union[int, str] = logging.INFO):
        self.logger = setup_logger('CellSplitHelper', log_level)

    def split_cells(self, code: Optional[str]) -> Optional[str]:
        """
        Split the input code into Databricks notebook cells.

        This method performs the following operations:
        1. Parse the code into an Abstract Syntax Tree (AST)
        2. Extract top-level nodes from the AST
        3. Merge nearby nodes into blocks
        4. Adjust block start lines to include preceding comments and blank lines
        5. Extend block endings downward to include trailing blank lines
        6. Format the output with `# COMMAND ----------` separators

        If a SyntaxError occurs during parsing, the entire code is returned as a single cell.

        Args:
            code (Optional[str]): The input Python code to be split into cells.

        Returns:
            Optional[str]: The code split into Databricks notebook cells, with `# COMMAND ----------` separating each cell.
                           Returns None if the input is invalid or empty.
                           Returns a single cell containing the entire code if a SyntaxError occurs during parsing.
        """
        self.logger.debug(f"Starting cell splitting process.")

        # If the code is None or not a string, return None
        if code is None or not isinstance(code, str):
            self.logger.warning(f"Invalid input: code is None or not a string.")
            return None

        # If stripping the code results in an empty string, return None
        code_stripped = code.strip()
        if not code_stripped:
            self.logger.warning(f"Invalid input: code is empty after stripping.")
            return None

        # Parse with AST
        # If parsing fails, return the entire code as a single cell
        try:
            tree = ast.parse(code)
            self.logger.debug("AST parsing successful.")
        except Exception as e:
            self.logger.error(f"Error occurred while parsing the code: {type(e).__name__} - {e}")
            return self._create_single_cell(code)

        # Get top-level nodes
        top_level_nodes = self._get_top_level_nodes(tree)
        self.logger.debug(f"Found {len(top_level_nodes)} top-level nodes")
        if not top_level_nodes:
            self.logger.warning("No top-level nodes found, returning single cell")
            return self._create_single_cell(code)

        # Merge nearby nodes into single blocks
        merged_blocks = self._merge_nearby_nodes(top_level_nodes)
        self.logger.debug(f"Merged into {len(merged_blocks)} blocks")

        # Adjust block start lines to include preceding comments and blank lines
        lines = code.split("\n")
        adjusted_blocks = self._adjust_block_start_lines(merged_blocks, lines)
        self.logger.debug(f"Adjusted block start lines, total blocks: {len(adjusted_blocks)}")

        # Extend block endings downward and format the output
        output_lines = self._extend_and_format_blocks(adjusted_blocks, lines)
        self.logger.debug(f"Extended block endings and formatted output, total lines: {len(output_lines)}")

        # Merge consecutive COMMAND_MARKER lines
        final_code = self._clean_command_lines("\n".join(output_lines))
        self.logger.debug("Final code generated.")
        return final_code

    def _extend_and_format_blocks(self, adjusted_blocks: List[Tuple[int, int]], lines: List[str]) -> List[str]:
        """
        Extend block endings downward to include trailing blank lines and format the output.
        This method processes each block, extends it to include trailing blank lines,
        and formats the output with COMMAND_MARKER separators.

        Args:
            adjusted_blocks (List[Tuple[int, int]]): A list of tuples representing adjusted blocks.
            lines (List[str]): The list of code lines.

        Returns:
            List[str]: A list of formatted output lines including COMMAND_MARKER and extended blocks.
        """
        output_lines = []
        last_used_line = 0

        for (block_start, block_end) in adjusted_blocks:
            # Adjust to avoid overlap with the previous block
            if block_start <= last_used_line:
                block_start = last_used_line + 1

            block_start = max(1, block_start)
            block_end = min(block_end, len(lines))

            # Include trailing blank lines
            extended_end = self._extend_block_downward_for_blank_lines(
                block_end, lines
            )

            if extended_end > block_end:
                block_end = extended_end

            if block_start <= block_end:
                output_lines.append(self.COMMAND_MARKER)
                for ln in range(block_start, block_end + 1):
                    output_lines.append(lines[ln - 1])
                last_used_line = max(last_used_line, block_end)

        return output_lines

    def _get_top_level_nodes(self, tree: ast.AST) -> List[Tuple[int, int]]:
        self.logger.debug("Getting top-level nodes from AST")
        """
        Get the top-level nodes from the AST and sort them by line number.

        Args:
            tree (ast.AST): The AST to analyze.

        Returns:
            List[Tuple[int, int]]: A sorted list of tuples containing the start and end line numbers of top-level nodes.
        """
        top_level_nodes = []
        for node in ast.iter_child_nodes(tree):
            start_line = getattr(node, "lineno", None)
            end_line = self._get_node_end_line(node)
            if start_line is not None and end_line is not None:
                top_level_nodes.append((start_line, end_line))
        return sorted(top_level_nodes, key=lambda x: x[0])

    def _merge_nearby_nodes(self, nodes: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        self.logger.debug(f"Merging nearby nodes, initial count: {len(nodes)}")
        """
        Merge nearby nodes into single blocks.
        This method combines nodes that are consecutive or very close (within one line)
        into a single block. This helps to prevent overly fine-grained splitting of the code.

        Args:
            nodes (List[Tuple[int, int]]): A list of tuples containing the start and end line numbers of nodes.

        Returns:
            List[Tuple[int, int]]: A list of tuples representing merged blocks of nearby nodes.
        """
        if not nodes:
            return []

        merged_blocks = []
        cur_start, cur_end = nodes[0]
        for i in range(1, len(nodes)):
            s, e = nodes[i]
            # If the node starts within one line of the previous block's end, include it in the same block
            if s <= cur_end + 1:
                cur_end = max(cur_end, e)
            else:
                merged_blocks.append((cur_start, cur_end))
                cur_start, cur_end = s, e
        merged_blocks.append((cur_start, cur_end))
        return merged_blocks

    def _adjust_block_start_lines(self, merged_blocks: List[Tuple[int, int]], lines: List[str]) -> List[Tuple[int, int]]:
        self.logger.debug(f"Adjusting block start lines, block count: {len(merged_blocks)}")
        """
        Adjust block start lines to include preceding comments and blank lines.
        This method ensures that each block includes any relevant comments or blank lines
        that precede it, helping to maintain context and readability in the split code.

        Args:
            merged_blocks (List[Tuple[int, int]]): A list of tuples representing merged blocks of nearby nodes.
            lines (List[str]): The list of code lines.

        Returns:
            List[Tuple[int, int]]: A list of tuples representing adjusted blocks with updated start lines.
        """
        adjusted_blocks = []
        used_end_line = 0
        for (start, end) in merged_blocks:
            real_start = self._pull_up_leading_comments_and_blank_lines(
                start_line=start,
                lines=lines,
                limit_line=used_end_line + 1  # Don't go above the end of the previous block + 1
            )
            adjusted_blocks.append((real_start, end))
            used_end_line = end
        return adjusted_blocks

    def _create_single_cell(self, code: str) -> str:
        """
        Create a single cell with the given code.

        Args:
            code (str): The code to be included in the cell.

        Returns:
            str: A single cell with COMMAND_MARKER and the given code.
        """
        return self._clean_command_lines(f"{self.COMMAND_MARKER}\n{code}")

    def _get_node_end_line(self, node: ast.AST) -> Optional[int]:
        """
        Recursively get the end line of an AST node.
        This method determines the last line of a given AST node by checking its
        end_lineno attribute if available, or recursively checking its child nodes.

        The algorithm works as follows:
        1. If the node has an end_lineno attribute, return its value.
        2. Otherwise, start with the node's lineno as the maximum line.
        3. Recursively check all child nodes:
           - If a child's end line is greater than the current maximum, update the maximum.
        4. Return the maximum line number found, or None if no valid line number was found.

        Args:
            node (ast.AST): The AST node to analyze.

        Returns:
            Optional[int]: The end line number of the node, or None if not found.
        """
        if hasattr(node, "end_lineno") and node.end_lineno is not None:
            return node.end_lineno
        max_line = getattr(node, "lineno", 0)
        for child in ast.iter_child_nodes(node):
            child_end = self._get_node_end_line(child)
            if child_end and child_end > max_line:
                max_line = child_end
        return max_line if max_line != 0 else None

    def _pull_up_leading_comments_and_blank_lines(
        self, start_line: int, lines: List[str], limit_line: int
    ) -> int:
        """
        Include blank lines or comment lines above the block start line in the same block.

        Args:
            start_line (int): The initial start line of the block.
            lines (List[str]): The list of code lines.
            limit_line (int): The upper limit line number to consider.

        Returns:
            int: The new start line for the block, including leading comments and blank lines.
        """
        idx = start_line - 1
        while idx - 1 >= limit_line - 1:
            content = lines[idx - 1].strip()
            if content == "" or content.startswith("#"):
                idx -= 1
            else:
                break
        if idx < limit_line - 1:
            idx = limit_line - 1
        return idx + 1

    def _extend_block_downward_for_blank_lines(
        self, block_end: int, lines: List[str]
    ) -> int:
        """
        Extend the block end to include trailing blank lines.

        Args:
            block_end (int): The initial end line of the block.
            lines (List[str]): The list of code lines.

        Returns:
            int: The new end line for the block, including trailing blank lines.
        """
        idx = block_end
        while idx < len(lines):
            content = lines[idx].strip()
            if content == "":
                idx += 1
            else:
                break
        return idx

    def _clean_command_lines(self, code: str) -> str:
        """
        Merge consecutive COMMAND_MARKER lines into a single line.

        Args:
            code (str): The code with potentially consecutive COMMAND_MARKER lines.

        Returns:
            str: The code with merged COMMAND_MARKER lines.
        """
        marker = self.COMMAND_MARKER
        double_marker = f"{marker}\n{marker}"
        while double_marker in code:
            code = code.replace(double_marker, marker)
        return code
