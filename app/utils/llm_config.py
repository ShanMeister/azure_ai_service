import os
from pathlib import Path
import yaml
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    """
    LLMConfig handles loading and validation of LLM-related configuration settings.

    This class supports reading from:
    - A YAML configuration file.
    - Environment variables with the prefix `LLM_`.
    - A `.env` file (if present).

    Attributes:
        model_provider (str): The provider of the LLM model (e.g., "azure_openai").
        model (str): The model name (e.g., "gpt-4o").
        azure_deployment (str): The Azure deployment name (if using Azure).
        azure_endpoint (str): The endpoint URL for Azure LLM API.
        api_key (str): The API key for authentication.
        api_version (str): The API version.

    Usage:
        1. Load configuration from a YAML file:

        ```python
        config = LLMConfig.from_file(Path("config.yaml"))
        print(config.model_provider)
        ```

        2. Load configuration from environment variables:

        ```python
        config = LLMConfig()
        print(config.api_key)  # Reads from LLM_API_KEY if set
        ```

    """

    model_provider: str
    model: str
    azure_deployment: str
    azure_endpoint: str
    api_key: str
    api_version: str

    @classmethod
    def from_file(cls, config_path: Path) -> "LLMConfig":
        """Loads configuration from a YAML file."""
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
        return cls(**config["llm"])

    class Config:
        env_prefix = (
            "LLM_"  # Allows loading from environment variables (e.g., LLM_API_KEY)
        )
        env_file = ".env"  # Reads from a .env file if available
        env_file_encoding = "utf-8"

class AnswerSimilarityConfig(BaseSettings):
    """
    AnswerSimilarityConfig handles loading and validation of answer similarity evaluation settings.

    This class supports reading from:
    - A YAML configuration file.
    - Environment variables with the prefix `ANSWER_SIMILARITY_`.

    Attributes:
        tracking_uri (str): The MLflow tracking URI.
        experiment_name (str): The MLflow experiment name.
        model_path (str): The path to the LLM model, i.e., a python file contains LangChain chain
        csv_path (str): The path to the CSV file containing evaluation data.

    Usage:
        1. Load configuration from a YAML file:

        ```python
        config = AnswerSimilarityConfig.from_file(Path("config.yaml"))
        print(config.tracking_uri)
        ```

        2. Load configuration from environment variables:

        ```python
        config = AnswerSimilarityConfig()
        print(config.model_path)  # Reads from ANSWER_SIMILARITY_MODEL_PATH if set
        ```
    """
    tracking_uri: str
    experiment_name: str
    model_path: str
    csv_path: str

    @classmethod
    def from_file(cls, config_path: Path) -> "AnswerSimilarityConfig":
        """Loads configuration from a YAML file."""
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
        return cls(**config["answer_similarity"])

    class Config:
        env_prefix = (
            "ANSWER_SIMILARITY_"  # Allows loading from environment variables (e.g., ANSWER_SIMILARITY_API_KEY)
        )


def configure_azure_openai_env(endpoint: str, api_key: str) -> None:
    """
    Configures environment variables for Azure OpenAI integration.

    This function sets the necessary environment variables required
    to authenticate with Azure OpenAI services.

    :param endpoint: The base URL of the Azure OpenAI API.
    :param api_key: The API key for Azure OpenAI authentication.
    :raises ValueError: If either argument is empty or None.
    """
    if not endpoint or not api_key:
        raise ValueError("Both 'endpoint' and 'api_key' must be non-empty strings.")

    os.environ["AZURE_OPENAI_ENDPOINT"] = endpoint
    os.environ["AZURE_OPENAI_API_KEY"] = api_key
