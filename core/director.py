import re
from typing import Tuple, Optional, Dict, Any

VALID_INSTRUCT_TAGS = {
    "american accent", "australian accent", "british accent", "canadian accent",
    "child", "chinese accent", "elderly", "female", "high pitch", "indian accent",
    "japanese accent", "korean accent", "low pitch", "male", "middle-aged",
    "moderate pitch", "portuguese accent", "russian accent", "teenager",
    "very high pitch", "very low pitch", "whisper", "young adult"
}

def sanitize_instruct(instruct_str: Optional[str]) -> Optional[str]:
    """Filters instruct string to ensure only valid model tokens are passed."""
    if not instruct_str:
        return None
    tokens = [t.strip() for t in instruct_str.split(",") if t.strip()]
    valid = [t for t in tokens if t in VALID_INSTRUCT_TAGS]
    return ", ".join(valid) if valid else None

class Director:
    """
    Analyzes narrative context to detect speaker attributions,
    emotional tags ([gasp], [laughter], etc.), and vocal parameters.
    """

    def __init__(self, custom_rules: Optional[Dict[str, Any]] = None):
        self.custom_rules = custom_rules or {}

    def identify_speaker(self, dialogue_text: str, prev_text: str, next_text: str, last_speaker: str = "Narrador") -> str:
        dial = dialogue_text.lower()
        surrounding = f"{next_text} {prev_text}".lower()

        # 1. Check custom user rules if provided
        for keyword, speaker in self.custom_rules.get("keywords", {}).items():
            if keyword.lower() in dial:
                return speaker

        # 2. General character speech patterns
        if "barusu" in dial:
            return "Ram"
        if "subaru-kun" in dial or "subaru kun" in dial:
            return "Rem"
        if "emilia-tan" in dial or "beako" in dial or "rem-rin" in dial or "ram-chi" in dial:
            return "Subaru"
        if "de hecho" in dial or "supongo" in dial or "kashira" in dial:
            if "loli" in dial or "taladro" in dial:
                return "Subaru"
            return "Beatrice"
        if "lia" in dial:
            return "Puck"

        # 3. Explicit attribution in surrounding narration
        patterns = [
            (r'\b(dijo|preguntó|exclamó|murmuró|pensó|gritó|llamó|contestó|respondió|añadió|bromeó|declaró|suspiró)\s+(beatrice|betty|la chica de cabello rizado|la niña)\b', "Beatrice"),
            (r'\b(beatrice|betty|la chica de cabello rizado)\s+(dijo|preguntó|exclamó|murmuró|respondió|suspiró|hizo una mueca)\b', "Beatrice"),
            (r'\b(dijo|preguntó|exclamó|murmuró|pensó|gritó|contestó|respondió|añadió|bromeó|declaró|continuó)\s+(subaru|el chico)\b', "Subaru"),
            (r'\b(subaru|el chico)\s+(dijo|preguntó|exclamó|murmuró|respondió|sonrió|gritó|replicó|añadió)\b', "Subaru"),
            (r'\b(dijo|preguntó|exclamó|murmuró|pensó|gritó|contestó|respondió|añadió|sonrió)\s+(emilia|la chica de cabello plateado|la semielfa)\b', "Emilia"),
            (r'\b(emilia|la chica de cabello plateado)\s+(dijo|preguntó|exclamó|murmuró|respondió|sonrió|inclinó la cabeza)\b', "Emilia"),
            (r'\b(dijo|preguntó|exclamó|murmuró|respondió)\s+(rem|la sirvienta de cabello azul)\b', "Rem"),
            (r'\b(rem|la sirvienta de cabello azul)\s+(dijo|preguntó|respondió|hizo una reverencia)\b', "Rem"),
            (r'\b(dijo|preguntó|exclamó|murmuró|respondió)\s+(ram|la sirvienta de cabello rosa)\b', "Ram"),
            (r'\b(ram|la sirvienta de cabello rosa)\s+(dijo|preguntó|respondió|resopló)\b', "Ram"),
            (r'\b(dijo|preguntó|exclamó|comentó|rió|declaró)\s+(roswaal|el señor de la mansión|el marqués)\b', "Roswaal"),
            (r'\b(roswaal|el marqués)\s+(dijo|preguntó|exclamó|comentó|rió|aplaudió)\b', "Roswaal"),
            (r'\b(dijo|preguntó|exclamó|bromeó)\s+(puck|el espíritu gato|el gato)\b', "Puck"),
            (r'\b(puck|el espíritu)\s+(dijo|preguntó|bromeó|flotó)\b', "Puck"),
            (r'\b(reinhard)\b', "Reinhard"),
            (r'\b(felt)\b', "Felt"),
            (r'\b(petra)\b', "Petra")
        ]

        for pattern, spk in patterns:
            if re.search(pattern, surrounding):
                return spk

        # 4. Turn alternation fallback
        if last_speaker == "Subaru":
            if "beatrice" in surrounding: return "Beatrice"
            if "emilia" in surrounding: return "Emilia"
            if "rem" in surrounding: return "Rem"
            if "ram" in surrounding: return "Ram"
            if "roswaal" in surrounding: return "Roswaal"
            return "Emilia"
        return "Subaru"

    def analyze_emotion_and_delivery(self, dialogue_text: str, prev_text: str, next_text: str, speaker: str) -> Tuple[str, Optional[str], float, float]:
        surrounding = f"{prev_text} {next_text}".lower()
        dial_lower = dialogue_text.lower()

        token = ""
        speed = 1.0
        guidance_scale = 2.8

        if speaker == "Beatrice":
            if any(k in dial_lower for k in ["supongo", "de hecho", "molestia", "humano"]) or any(k in surrounding for k in ["suspiró", "hastiada"]):
                token = "[sigh] "
            elif "¡" in dialogue_text or "insolente" in dial_lower or "gritó" in surrounding:
                token = "[gasp] "
                speed = 1.04
                guidance_scale = 3.2
            instruct = "female, child, very high pitch" if (token == "[gasp] " or "¡" in dialogue_text) else "female, child, high pitch"

        elif speaker == "Rem":
            if any(w in dial_lower for w in ["subaru", "amor", "perdón", "tranquilo", "descanse"]) or "susurró" in surrounding:
                instruct = "female, whisper, young adult"
                guidance_scale = 2.6
            else:
                instruct = "female, young adult, moderate pitch"

        elif speaker == "Ram":
            if any(k in surrounding for k in ["burló", "resopló", "barusu"]):
                token = "[sigh] "
            instruct = "female, young adult, moderate pitch"

        elif speaker == "Subaru":
            if any(k in surrounding for k in ["gritó", "aterrado", "desesperación", "pánico", "horror", "jadeó"]) or ("¡" in dialogue_text and len(dialogue_text) < 60):
                token = "[gasp] "
                speed = 1.05
                guidance_scale = 3.2
                instruct = "male, teenager, high pitch"
            elif any(k in surrounding for k in ["gimió", "dolor", "herido", "agonía"]) or "argh" in dial_lower or "guh" in dial_lower:
                token = "[groan] "
                speed = 0.92
                instruct = "male, teenager, low pitch"
            elif any(k in surrounding for k in ["rió", "carcajada", "jajaja"]) or "jaja" in dial_lower:
                token = "[laughter] "
                instruct = "male, teenager, moderate pitch"
            elif "susurró" in surrounding or "en voz baja" in surrounding:
                instruct = "male, whisper, teenager"
            else:
                instruct = "male, teenager, moderate pitch"

        elif speaker == "Roswaal":
            if any(k in surrounding for k in ["rió", "carcajada", "jajaja"]) or "jaja" in dial_lower:
                token = "[laughter] "
            instruct = "male, middle-aged, low pitch"
            speed = 0.95

        elif speaker == "Emilia":
            if any(k in surrounding for k in ["gritó", "alarmada", "preocupada"]) or "¡" in dialogue_text:
                token = "[gasp] "
                speed = 1.02
            instruct = "female, young adult, high pitch"

        elif speaker == "Puck":
            if any(k in surrounding for k in ["rió", "sonrió", "juguetón"]) or "jaja" in dial_lower:
                token = "[laughter] "
            instruct = "female, child, high pitch"

        elif speaker == "Narrador":
            instruct = None
            guidance_scale = 2.8

        else:
            instruct = "male, middle-aged, moderate pitch"

        clean_inst = sanitize_instruct(instruct)
        formatted_text = token + dialogue_text if token and not dialogue_text.startswith("[") else dialogue_text
        return formatted_text, clean_inst, speed, guidance_scale
