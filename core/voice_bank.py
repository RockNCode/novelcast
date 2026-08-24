import os
import json
from typing import Dict, Optional
from novelcast.core.schema import VoiceConfig, CharacterVoice

class VoiceBank:
    def __init__(self, config_path: str = "voice_config.json", voice_bank_dir: str = "voice_bank"):
        self.config_path = config_path
        self.voice_bank_dir = voice_bank_dir
        self.config = VoiceConfig()
        self.load()

    def _find_ref_audio(self, name: str) -> Optional[str]:
        clean = name.lower().replace(" ", "_")
        if not os.path.exists(self.voice_bank_dir):
            return None

        # Check top-level first
        for ext in [".wav", ".mp3", ".flac", ".m4a"]:
            path = os.path.join(self.voice_bank_dir, f"{clean}{ext}")
            if os.path.exists(path):
                return path

        # Check recursively in subdirectories (all_voices, elevenlabs, etc.)
        for root, _, files in os.walk(self.voice_bank_dir):
            for f in files:
                if f.lower().startswith(clean) and f.endswith((".wav", ".mp3", ".flac", ".m4a")):
                    return os.path.join(root, f)
        return None

    def load(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                chars_data = data.get("characters", {})
                converted = {}
                for name, item in chars_data.items():
                    if isinstance(item, dict):
                        char = CharacterVoice(**item)
                        if not char.reference_audio:
                            char.reference_audio = self._find_ref_audio(name)
                        converted[name] = char
                self.config = VoiceConfig(
                    default_narrator=data.get("default_narrator", "Narrador"),
                    characters=converted
                )

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config.model_dump(), f, ensure_ascii=False, indent=2)

    def get_character(self, name: str) -> CharacterVoice:
        # 1. Exact match
        if name in self.config.characters:
            char = self.config.characters[name]
            if not char.reference_audio:
                char.reference_audio = self._find_ref_audio(name)
            return char
        
        # 2. Case-insensitive / normalized match
        n_clean = name.strip().lower().replace("_", " ")
        for k, v in self.config.characters.items():
            if k.strip().lower().replace("_", " ") == n_clean:
                if not v.reference_audio:
                    v.reference_audio = self._find_ref_audio(name)
                return v

        # 3. Fallback auto-discovery
        ref = self._find_ref_audio(name)
        return CharacterVoice(
            description=f"Auto-cast character: {name}",
            instruct="male, middle-aged, moderate pitch" if "male" in name.lower() else "female, young adult, moderate pitch",
            reference_audio=ref
        )

    def auto_discover_voices(self):
        """Scans voice_bank_dir and registers any discovered audio files."""
        if os.path.exists(self.voice_bank_dir):
            for root, _, files in os.walk(self.voice_bank_dir):
                for fname in sorted(files):
                    name, ext = os.path.splitext(fname)
                    if ext.lower() in [".wav", ".mp3", ".flac", ".m4a"]:
                        char_name = name.replace("_", " ").title()
                        if char_name not in self.config.characters and not any(k.lower() == char_name.lower() for k in self.config.characters):
                            self.config.characters[char_name] = CharacterVoice(
                                description=f"Discovered voice: {char_name}",
                                reference_audio=os.path.join(root, fname)
                            )

    def add_character(self, name: str, voice: CharacterVoice):
        if not voice.reference_audio:
            voice.reference_audio = self._find_ref_audio(name)
        self.config.characters[name] = voice
        self.save()

    def list_characters(self) -> Dict[str, CharacterVoice]:
        return dict(self.config.characters)
