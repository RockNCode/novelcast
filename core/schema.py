from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import hashlib

class Segment(BaseModel):
    id: int
    speaker: str = "Narrador"
    text: str
    instruct: Optional[str] = None
    speed: float = 1.0
    guidance_scale: float = 2.8
    pause_after_ms: int = 450
    audio_hash: Optional[str] = None

    def compute_hash(self, language: str = "es") -> str:
        """Computes deterministic 12-char SHA256 hash for caching."""
        inst = self.instruct or ""
        text_clean = self.text.strip()
        hash_input = f"omni_{language}_{self.speaker}_{inst}_{self.speed}_{self.guidance_scale}_{text_clean}".encode("utf-8")
        self.audio_hash = hashlib.sha256(hash_input).hexdigest()[:12]
        return self.audio_hash

class ChapterScript(BaseModel):
    title: str
    book: str = "NovelCast Audiobook"
    chapter_id: str = "chapter"
    segments: List[Segment] = Field(default_factory=list)

    @property
    def total_characters(self) -> int:
        return sum(len(s.text) for s in self.segments)

    @property
    def dialogue_count(self) -> int:
        return sum(1 for s in self.segments if s.speaker.lower() not in ["narrador", "narrator"])

class CharacterVoice(BaseModel):
    gender: Optional[str] = "unspecified"
    description: Optional[str] = ""
    instruct: Optional[str] = None
    speed: float = 1.0
    guidance_scale: float = 2.8
    pause_after_ms: int = 400
    reference_audio: Optional[str] = None

class VoiceConfig(BaseModel):
    default_narrator: str = "Narrador"
    characters: Dict[str, CharacterVoice] = Field(default_factory=dict)

class EngineSettings(BaseModel):
    name: str = "omnivoice"  # omnivoice, cosyvoice, kokoro, elevenlabs
    remote_url: Optional[str] = None
    workers: int = 4
    guidance_scale: float = 2.8
    default_speed: float = 1.0

class PauseSettings(BaseModel):
    same_speaker_ms: int = 300
    speaker_change_ms: int = 450
    scene_break_ms: int = 1000
    chapter_title_ms: int = 1200

class AudioSettings(BaseModel):
    bitrate: str = "128k"
    sample_rate: int = 44100
    channels: int = 1
    normalize_lufs: float = -16.0
    format: str = "m4b"

class PathSettings(BaseModel):
    scripts_dir: str = "data/scripts"
    cache_dir: str = "cache_omnivoice"
    output_dir: str = "output"
    voice_bank_dir: str = "voice_bank"
    cover_image: Optional[str] = "cover.jpg"

class ProjectConfig(BaseModel):
    project_name: str = "NovelCast Audiobook"
    language: str = "es"
    engine: EngineSettings = Field(default_factory=EngineSettings)
    pauses: PauseSettings = Field(default_factory=PauseSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
