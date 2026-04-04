from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="core/.env",
        env_file_encoding="utf-8",
    )

    # Application configuration
    app_name: str = "Multi Agent Orchestration" 
    port: int = 80

    # OpenAI API configuration
    azure_openai_api_key: SecretStr
    azure_openai_endpoint: str
    azure_deployment: str
    api_version: str

    tavily_api_key: SecretStr

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        if not self.azure_openai_api_key.get_secret_value() or not self.azure_openai_endpoint or \
            not self.azure_deployment or not self.api_version:
            raise ValueError("Azure OpenAI API configuration is incomplete.")
        
        if not self.tavily_api_key.get_secret_value():
            raise ValueError("Tavily API key is missing.")
        
        return self
    

settings = Settings()

__all__ = ["settings"]


