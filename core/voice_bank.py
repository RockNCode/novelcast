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
        for ext in [".wav", ".mp3", ".flac", ".m4a"]:
            path = os.path.join(self.voice_bank_dir, f"{clean}{ext}")
            if os.path.exists(path):
                return path
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
        if name in self.config.characters:
            char = self.config.characters[name]
            if not char.reference_audio:
                char.reference_audio = self._find_ref_audio(name)
            return char
        
        # Return fallback with auto-detected reference audio if it exists
        ref = self._find_ref_audio(name)
        return CharacterVoice(
            description=f"Auto-cast character: {name}",
            instruct="male, middle-aged, moderate pitch" if "male" in name.lower() else "female, young adult, moderate pitch",
            reference_audio=ref
        )

    def auto_discover_voices(self):
        """Scans voice_bank_dir and registers any discovered audio files."""
        if os.path.exists(self.voice_bank_dir):
            for fname in os.listdir(self.voice_bank_dir):
                name, ext = os.path.splitext(fname)
                if ext.lower() in [".wav", ".mp3", ".flac", ".m4a"]:
                    char_name = name.capitalize().replace("_", " ")
                    if char_name not in self.config.characters:
                        self.config.characters[char_name] = CharacterVoice(
                            description=f"Discovered voice: {char_name}",
                            reference_audio=os.path.join(self.voice_bank_dir, fname)
                        )

    def add_character(self, name: str, voice: CharacterVoice):
        if not voice.reference_audio:
            voice.reference_audio = self._find_ref_audio(name)
        self.config.characters[name] = voice
        self.save()

    def list_characters(self) -> Dict[str, CharacterVoice]:
        # Also auto-populate any characters present in voice_bank directory
        result = dict(self.config.characters)
        if os.path.exists(self.voice_bank_dir):
            for f in os.listdir(self.voice_bank_dir):
                if f.endswith((".wav", ".mp3")):
                    base = os.path.splitext(f)[0]
                    cap_name = base.replace("_", " ").title()
                    if cap_name not in result and base not in result:
                        result[cap_name] = CharacterVoice(
                            description=f"Discovered from {f}",
                            reference_audio=os.path.join(self.voice_bank_dir, f)
                        )
        return result
