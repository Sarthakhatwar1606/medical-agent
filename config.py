import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Azure AI Foundry (Claude endpoint)
    AZURE_AI_ENDPOINT: str = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT", "")
    AZURE_AI_KEY: str = os.getenv("AZURE_AI_FOUNDRY_API_KEY", "")
    MODEL: str = os.getenv("CLAUDE_MODEL", "claude-opus-4-8")

    # Azure AI Search
    SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    SEARCH_KEY: str = os.getenv("AZURE_SEARCH_KEY", "")
    SEARCH_INDEX: str = os.getenv("AZURE_SEARCH_INDEX", "medical-knowledge")

    # Azure Blob Storage
    STORAGE_CONN_STR: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    STORAGE_CONTAINER: str = os.getenv("AZURE_STORAGE_CONTAINER", "medical-documents")

    def validate(self) -> None:
        missing = [
            name for name, val in {
                "AZURE_AI_FOUNDRY_ENDPOINT": self.AZURE_AI_ENDPOINT,
                "AZURE_AI_FOUNDRY_API_KEY": self.AZURE_AI_KEY,
                "AZURE_SEARCH_ENDPOINT": self.SEARCH_ENDPOINT,
                "AZURE_SEARCH_KEY": self.SEARCH_KEY,
                "AZURE_STORAGE_CONNECTION_STRING": self.STORAGE_CONN_STR,
            }.items() if not val
        ]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Copy .env.example to .env and fill in your Azure credentials."
            )


config = Config()
