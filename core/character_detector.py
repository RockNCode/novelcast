import os
import re
from typing import List, Dict, Any, Optional
from collections import Counter
from novelcast.core.schema import ChapterScript, Segment
from novelcast.core.voice_bank import VoiceBank

# Common Spanish reporting verbs for speaker attribution
REPORTING_VERBS = [
    r'dijo', r'preguntó', r'exclamó', r'murmuró', r'gritó', r'chilló',
    r'susurró', r'respondió', r'contestó', r'añadió', r'declaró', r'bromeó',
    r'replicó', r'suspiró', r'comentó', r'pensó', r'llamó', r'ordenó'
]

class CharacterDetector:
    """
    Discovers characters, dialogue frequency, and character speech samples
    from EPUBs or parsed chapter scripts, and matches them against VoiceBank reference files.
    """

    def __init__(self, voice_bank: Optional[VoiceBank] = None):
        self.vb = voice_bank or VoiceBank()
        self.vb.auto_discover_voices()

    def detect_from_scripts(self, scripts: List[ChapterScript]) -> List[Dict[str, Any]]:
        """
        Extracts character dialogue statistics and speech samples across all chapter scripts.
        """
        speaker_counts = Counter()
        speaker_samples = {}
        speaker_emotions = Counter()
        total_dialogue_segments = 0

        for cs in scripts:
            for seg in cs.segments:
                spk = seg.speaker.strip() if seg.speaker else "Narrador"
                speaker_counts[spk] += 1
                if spk != "Narrador":
                    total_dialogue_segments += 1

                if spk not in speaker_samples and len(seg.text.strip()) > 10:
                    speaker_samples[spk] = seg.text.strip()
                if seg.instruct:
                    speaker_emotions[f"{spk}::{seg.instruct}"] += 1

        # Build available voices list from voice bank
        available_voices = []
        if os.path.exists(self.vb.voice_bank_dir):
            for f in sorted(os.listdir(self.vb.voice_bank_dir)):
                if f.endswith((".wav", ".mp3", ".flac", ".m4a")):
                    base = os.path.splitext(f)[0]
                    available_voices.append({
                        "filename": f,
                        "name": base.replace("_", " ").title(),
                        "path": os.path.join(self.vb.voice_bank_dir, f),
                        "audio_url": f"/api/audio/sample?name={f}"
                    })

        # Scan all_voices subfolder if present
        all_voices_dir = os.path.join(self.vb.voice_bank_dir, "all_voices")
        if os.path.exists(all_voices_dir):
            for f in sorted(os.listdir(all_voices_dir)):
                if f.endswith((".wav", ".mp3", ".flac", ".m4a")):
                    base = os.path.splitext(f)[0]
                    available_voices.append({
                        "filename": f"all_voices/{f}",
                        "name": base.replace("_", " ").title(),
                        "path": os.path.join(all_voices_dir, f),
                        "audio_url": f"/api/audio/sample?name={f}"
                    })

        detected_list = []
        # Sort characters by frequency (Narrador always first, then by line count)
        sorted_speakers = sorted(
            speaker_counts.keys(),
            key=lambda k: (0 if k == "Narrador" else 1, -speaker_counts[k])
        )

        for spk in sorted_speakers:
            count = speaker_counts[spk]
            char_info = self.vb.get_character(spk)
            assigned_file = None
            if char_info and char_info.reference_audio:
                assigned_file = os.path.basename(char_info.reference_audio)

            # Auto-find best candidate in available voices
            suggested_file = assigned_file
            if not suggested_file:
                clean_spk = spk.lower().replace(" ", "_")
                for v in available_voices:
                    v_base = os.path.splitext(os.path.basename(v["filename"]))[0].lower()
                    if v_base == clean_spk or clean_spk in v_base or v_base in clean_spk:
                        suggested_file = os.path.basename(v["filename"])
                        break

            # If still none and narrator, fallback to narrador.wav
            if not suggested_file and spk == "Narrador":
                for v in available_voices:
                    if "narrador" in v["filename"].lower() or "narrator" in v["filename"].lower():
                        suggested_file = os.path.basename(v["filename"])
                        break

            detected_list.append({
                "name": spk,
                "dialogue_count": count,
                "pct_of_dialogue": round((count / max(total_dialogue_segments, 1)) * 100, 1) if spk != "Narrador" else None,
                "sample_quote": speaker_samples.get(spk, f"Línea de {spk}"),
                "gender": "male" if spk in ["Narrador", "Subaru", "Roswaal", "Reinhard"] else "female" if spk in ["Emilia", "Rem", "Ram", "Beatrice", "Felt", "Petra"] else "unspecified",
                "assigned_voice": assigned_file,
                "suggested_voice": suggested_file,
                "has_reference_audio": bool(assigned_file or suggested_file)
            })

        return detected_list

    def detect_from_raw_text(self, text: str) -> List[Dict[str, Any]]:
        """Extracts potential character names from raw narrative text using NLP patterns."""
        names = Counter()
        pattern = r'\b(' + '|'.join(REPORTING_VERBS) + r')\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b'
        for match in re.finditer(pattern, text, re.IGNORECASE):
            name = match.group(2).capitalize()
            if len(name) > 2 and name not in ["El", "La", "Los", "Las", "Un", "Una", "De", "En", "Por", "Con", "Para"]:
                names[name] += 1

        pattern_reverse = r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+(' + '|'.join(REPORTING_VERBS) + r')\b'
        for match in re.finditer(pattern_reverse, text, re.IGNORECASE):
            name = match.group(1).capitalize()
            if len(name) > 2 and name not in ["El", "La", "Los", "Las", "Un", "Una", "De", "En", "Por", "Con", "Para"]:
                names[name] += 1

        return [{"name": name, "frequency": count} for name, count in names.most_common(20)]
