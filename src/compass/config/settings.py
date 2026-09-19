"""Configuration models and loaders for Code Compass."""

from pathlib import Path
from typing import List, Literal, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProjectConfig(BaseModel):
    """Project metadata settings."""
    name: str = Field(default="my-project", description="Name of the software project")
    description: Optional[str] = Field(default=None, description="Optional brief description")
    version: Optional[str] = Field(default="0.1.0", description="Project version")


class SourceConfig(BaseModel):
    """Source code repository configuration."""
    path: str = Field(default=".", description="Path to local source repository")
    ignore_patterns: List[str] = Field(
        default_factory=lambda: [
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            "dist",
            "build",
            "coverage",
            ".env",
            ".pytest_cache",
            "*.egg-info",
        ],
        description="Glob patterns or folder names to ignore during scanning"
    )


class KnowledgeConfig(BaseModel):
    """Knowledge repository output configuration."""
    path: str = Field(default="./knowledge", description="Destination directory for generated knowledge repository")


class AnalysisConfig(BaseModel):
    """Analysis engine feature flags."""
    languages: List[str] = Field(default_factory=lambda: ["python"], description="Languages to analyze")
    files: bool = Field(default=True, description="Enable file structure analysis")
    imports: bool = Field(default=True, description="Enable import and dependency analysis")
    symbols: bool = Field(default=True, description="Enable class, function, and symbol analysis")
    git_history: bool = Field(default=True, description="Enable git commit history extraction if available")
    max_git_commits: int = Field(default=100, description="Max git commits to analyze")


class LLMConfig(BaseModel):
    """LLM provider configuration. Defaults to completely offline/none."""
    provider: Literal["none", "ollama", "openai", "anthropic", "gemini"] = Field(
        default="none",
        description="LLM Provider. Default 'none' requires zero network access."
    )
    model: Optional[str] = Field(default=None, description="Model name if provider is enabled")
    api_base: Optional[str] = Field(default="http://localhost:11434", description="Base URL for local/remote LLM")
    temperature: float = Field(default=0.0, description="Generation temperature")


class CompassConfig(BaseSettings):
    """Top-level Code Compass configuration schema."""
    model_config = SettingsConfigDict(
        env_prefix="COMPASS_",
        env_nested_delimiter="__",
        extra="ignore"
    )

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    source: SourceConfig = Field(default_factory=SourceConfig)
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "CompassConfig":
        """Load configuration from a YAML file."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}
            
        return cls.model_validate(raw_data)

    def to_yaml(self, path: Path | str) -> None:
        """Write configuration to a YAML file."""
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = self.model_dump(exclude_none=True)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, default_flow_style=False)


def load_config(config_path: Optional[str | Path] = None) -> CompassConfig:
    """Convenience function to locate and load compass configuration."""
    candidates = [
        Path(config_path) if config_path else None,
        Path("compass.yaml"),
        Path("compass.yml"),
        Path(".compass.yaml"),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return CompassConfig.from_yaml(candidate)
    
    # Return default configuration if no file found
    return CompassConfig()
