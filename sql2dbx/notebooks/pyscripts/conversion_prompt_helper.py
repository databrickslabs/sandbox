from enum import Enum
from pathlib import Path
from typing import Dict, List, TypedDict, Union

import yaml
from omegaconf import OmegaConf


class SupportedSQLDialect(Enum):
    """Enumeration of supported SQL dialects, paired with default YAML filenames."""
    MYSQL = ("mysql", "mysql_to_databricks_notebook.yml")
    NETEZZA = ("netezza", "netezza_to_databricks_notebook.yml")
    ORACLE = ("oracle", "oracle_to_databricks_notebook.yml")
    POSTGRESQL = ("postgresql", "postgresql_to_databricks_notebook.yml")
    REDSHIFT = ("redshift", "redshift_to_databricks_notebook.yml")
    SNOWFLAKE = ("snowflake", "snowflake_to_databricks_notebook.yml")
    TERADATA = ("teradata", "teradata_to_databricks_notebook.yml")
    TSQL = ("tsql", "tsql_to_databricks_notebook.yml")

    @property
    def dialect_name(self):
        return self.value[0]

    @property
    def default_yaml_filename(self):
        return self.value[1]


class FewShot(TypedDict):
    """Type definition for few-shot examples in the conversion process.

    Attributes:
        role: The role of the example (e.g., 'user', 'assistant').
        content: The content of the example.
    """
    role: str
    content: str


class ConversionPromptHelper:
    """Helper class for managing SQL code conversion prompts.

    This class orchestrates the prompt management for SQL code conversion,
    handling system messages and few-shot examples.
    """
    _CONVERSION_PROMPT_YAML_DIR_NAME = "conversion_prompt_yaml"
    _COMMON_INSTRUCTION_YAML_DIR_NAME = "common_instructions"
    _COMMON_INSTRUCTION_YAML_FILE_NAME = "sql_to_databricks_notebook_common_python.yml"

    def __init__(self, conversion_prompt_yaml: str, comment_lang: str = None):
        """Initialize the ConversionPromptHelper.

        Args:
            conversion_prompt_yaml: Path to the YAML file containing prompts.
            comment_lang: Language to be used for comments in the converted code.
        """
        self.prompt_config = PromptConfig(
            conversion_prompt_yaml=conversion_prompt_yaml,
            comment_lang=comment_lang
        )

    def get_system_message(self) -> str:
        """Retrieve the system message for the conversion process.

        Returns:
            The formatted system message with the specified comment language.
        """
        return self.prompt_config.get_system_message()

    def get_few_shots(self) -> List[FewShot]:
        """Retrieve the few-shot examples for the conversion process.

        Returns:
            A list of few-shot examples to be used in the conversion.
        """
        return self.prompt_config.get_few_shots()

    @staticmethod
    def get_supported_sql_dialects() -> List[str]:
        """Return a list of supported SQL dialects."""
        return [dialect.dialect_name for dialect in SupportedSQLDialect]

    @staticmethod
    def get_default_yaml_for_sql_dialect(dialect: str) -> str:
        """Return the full path of the default YAML for the given dialect.

        Args:
            dialect: SQL dialect name (e.g., 'tsql', 'snowflake').

        Returns:
            The resolved file path (absolute) for the default YAML.

        Raises:
            ValueError: If the dialect is not supported.
        """
        # Find the matching enum member
        for item in SupportedSQLDialect:
            if item.dialect_name == dialect:
                yaml_path = ConversionPromptHelper._get_yaml_base_dir() / item.default_yaml_filename
                return str(yaml_path.resolve())
        raise ValueError(f"Unsupported sql dialect: {dialect}")

    @staticmethod
    def _get_common_instruction_yaml() -> str:
        """Return the full path of the common instruction YAML.

        Returns:
            The resolved file path (absolute) for the common instruction YAML.
        """
        yaml_path = ConversionPromptHelper._get_yaml_base_dir() / ConversionPromptHelper._COMMON_INSTRUCTION_YAML_DIR_NAME / \
            ConversionPromptHelper._COMMON_INSTRUCTION_YAML_FILE_NAME
        return str(yaml_path.resolve())

    @staticmethod
    def _get_yaml_base_dir() -> Path:
        """Return the base directory for YAML files.

        Returns:
            The absolute path to the base directory containing YAML files.
        """
        base_dir = Path(__file__).parent
        return base_dir / ConversionPromptHelper._CONVERSION_PROMPT_YAML_DIR_NAME


class PromptConfig:
    """Configuration class for managing conversion prompts.

    This class handles loading and managing prompt configurations from YAML files.
    """

    def __init__(self, conversion_prompt_yaml: str, comment_lang: str = None):
        """Initialize the PromptConfig.

        Args:
            conversion_prompt_yaml: Path to the YAML file containing prompts.
            comment_lang: Language to be used for comments.
        """
        self.conversion_prompt_yaml = conversion_prompt_yaml
        self.comment_lang = comment_lang
        self._prompts = self._load_prompts()

    def get_system_message(self) -> str:
        """Get system message with comment language interpolated.

        Returns:
            The system message with the comment language placeholders replaced.
        """
        system_message = self._prompts["system_message"]
        if self.comment_lang:
            system_message = system_message.replace("{comment_lang}", self.comment_lang)
        return system_message

    def get_few_shots(self) -> List[FewShot]:
        """Get few-shot examples from the loaded prompts.

        Returns:
            A list of few-shot examples, or an empty list if none are defined.
        """
        return self._prompts.get("few_shots", [])

    def _load_prompts(self) -> Dict:
        """Load prompts from the YAML file.

        Returns:
            A dictionary containing the loaded prompts.

        Raises:
            FileNotFoundError: If the specified YAML file is not found.
            ValueError: If the YAML content is invalid.
        """
        try:
            common_yaml = self._load_yaml_file(ConversionPromptHelper._get_common_instruction_yaml())
            custom_yaml = self._load_yaml_file(self.conversion_prompt_yaml)
            prompts = self._merge_yaml_files(common_yaml, custom_yaml)
            if "system_message" not in prompts:
                raise ValueError("YAML must contain 'system_message' key")
            return prompts
        except Exception as e:
            raise Exception(f"Failed to load custom prompts: {e}")

    @staticmethod
    def _load_yaml_file(file_path: Union[str, Path]) -> Dict:
        """Common helper method to load a YAML file.

        Args:
            file_path: Path to the YAML file to be loaded (string or Path object).

        Returns:
            The loaded YAML content as a dictionary.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the YAML content is not a dictionary.
        """
        path = Path(file_path) if not isinstance(file_path, Path) else file_path
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            yaml_content = yaml.safe_load(f)
        if not isinstance(yaml_content, dict):
            raise ValueError(f"YAML content must be a dictionary: {path}")
        return yaml_content

    @staticmethod
    def _merge_yaml_files(common_yaml: dict, custom_yaml: dict) -> dict:
        """
        Merges two YAML configuration dictionaries into a single dictionary.

        This method combines the keys and values from `common_yaml` and `custom_yaml`.
        If there are overlapping keys, the values from `custom_yaml` will take precedence.
        The resulting dictionary is resolved using OmegaConf to ensure all references
        and interpolations are processed.

        Args:
            common_yaml (dict): The base YAML configuration dictionary.
            custom_yaml (dict): The custom YAML configuration dictionary that overrides
                                or extends the base configuration.

        Returns:
            dict: A merged and resolved dictionary containing the combined configuration.
        """
        combined_yaml = {**common_yaml, **custom_yaml}
        try:
            conf = OmegaConf.create(combined_yaml)
            return OmegaConf.to_container(conf, resolve=True)
        except Exception:
            # If OmegaConf fails due to unresolved interpolations, return the combined dict as-is
            return combined_yaml
