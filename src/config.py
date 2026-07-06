"""Configuration loading and management."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class VideoConfig(BaseModel):
    """Video output configuration."""

    width: int = 1920
    height: int = 1080
    fps: int = 30
    format: str = "mp4"
    codec: str = "h264"


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: str = "openai"
    model: str = "gpt-5.4"
    max_tokens: int = 16384
    temperature: float = 0.7


class TTSConfig(BaseModel):
    """Text-to-speech configuration."""

    provider: str = "edge"
    voice_id: str | None = None
    model: str = "edge-tts"
    output_format: str = "mp3_44100_128"


class BudgetConfig(BaseModel):
    """Budget limits in USD."""

    llm_per_video: float = 50.0
    tts_per_video: float = 10.0
    image_gen_per_video: float = 20.0
    total_per_video: float = 100.0


class PathsConfig(BaseModel):
    """Path configuration."""

    output_dir: str = "output"
    templates_dir: str = "templates"
    animations_dir: str = "animations"


class ReviewConfig(BaseModel):
    """Human review configuration."""

    enabled: bool = True
    checkpoints: list[str] = Field(default_factory=lambda: ["script", "storyboard", "final"])


class CharacterConfig(BaseModel):
    """Short-first recurring character configuration."""

    enabled: bool = True
    character_id: str = "character_1"
    asset_source: str = "remotion/public/characters/synctoon"
    aligner_url: str = "http://localhost:49153/transcriptions?async=false"
    aligner_timeout_seconds: float = 5.0
    word_timing_fallback: bool = True


class Config(BaseModel):
    """Main application configuration."""

    video: VideoConfig = Field(default_factory=VideoConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    character: CharacterConfig = Field(default_factory=CharacterConfig)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "Config":
        """Load configuration from a YAML file."""
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f)

        if data is None:
            return cls()

        # Flatten nested resolution config
        if "video" in data and "resolution" in data["video"]:
            res = data["video"].pop("resolution")
            data["video"]["width"] = res.get("width", 1920)
            data["video"]["height"] = res.get("height", 1080)

        return cls(**data)

    def to_yaml(self, path: Path | str) -> None:
        """Save configuration to a YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = self.model_dump()
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)


def load_config(config_path: Path | str | None = None) -> Config:
    """Load configuration from file or use defaults."""
    if config_path is None:
        # Look for config.yaml in current directory or project root
        candidates = [Path("config.yaml"), Path(__file__).parent.parent / "config.yaml"]
        for candidate in candidates:
            if candidate.exists():
                config_path = candidate
                break

    if config_path is not None:
        return Config.from_yaml(config_path)

    return Config()
