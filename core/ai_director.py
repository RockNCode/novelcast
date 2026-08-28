import re
import json
import requests
from typing import List, Dict, Any, Optional, Callable, Tuple
from novelcast.core.schema import Segment, ChapterScript, CharacterVoice
from novelcast.core.llm_manager import LLMProviderConfig, LLMConfigManager
from novelcast.core.voice_bank import VoiceBank

VALID_INSTRUCT_TAGS = [
    "female, child, high pitch",
    "female, child, very high pitch",
    "female, young adult, high pitch",
    "female, young adult, moderate pitch",
    "female, young adult, low pitch",
    "female, whisper, young adult",
    "female, whisper, child",
    "female, elderly, low pitch",
    "male, child, high pitch",
    "male, teenager, high pitch",
    "male, teenager, moderate pitch",
    "male, teenager, low pitch",
    "male, whisper, teenager",
    "male, young adult, moderate pitch",
    "male, middle-aged, low pitch",
    "male, middle-aged, moderate pitch",
    "male, elderly, low pitch",
    "male, whisper, young adult"
]

AUDIO_TOKENS = ["[gasp]", "[laughter]", "[sigh]", "[groan]", "[pant]"]

SYSTEM_PROMPT = """You are an expert Literary Audiobook Director and Dialogue Attribution Specialist.
Your task is to analyze sequential segments of a chapter from a novel/audiobook and determine:
1. Who is the TRUE speaker of each line (distinguishing Narration vs Spoken Dialogue vs Characters).
2. The emotional tone / delivery instruct for speech synthesis.
3. Any expressive vocal audio tokens to insert at the beginning of the line (e.g. [laughter], [gasp], [sigh], [groan], [pant]).

CRITICAL DIRECTIVE RULES:
- Third-person descriptions, exposition, and narrator voice MUST have speaker: "Narrador" and instruct: null.
- Dialogue spoken by characters MUST be attributed to the exact matching Character Name from the Candidate Characters list.
- Pay close attention to reporting verbs ("dijo X", "respondió ella", "preguntó el marqués"), dialogue alternation turns, nicknames, and context.
- If a line contains laughter, crying, shock, sighing, or pain, select the appropriate audio token.
- Output ONLY a valid JSON array of objects with NO conversational filler or markdown formatting outside the JSON.
"""

class AIDirector:
    """
    Directs audiobook dialogue attribution and emotional synthesis
    using modern LLMs (Ollama, LM Studio, DeepSeek, OpenAI, Groq, etc.).
    """

    def __init__(
        self,
        provider_config: Optional[LLMProviderConfig] = None,
        config_manager: Optional[LLMConfigManager] = None
    ):
        self.config_manager = config_manager or LLMConfigManager()
        self.provider = provider_config or self.config_manager.get_provider()

    def set_provider(self, provider_id: str, model_override: Optional[str] = None):
        prov = self.config_manager.get_provider(provider_id)
        if model_override:
            prov = prov.copy(update={"default_model": model_override})
        self.provider = prov

    def _build_character_context(self, candidate_characters: List[Dict[str, Any]]) -> str:
        lines = ["CANDIDATE CHARACTERS IN THIS NOVEL:"]
        lines.append("- Narrador (Gender: neutral, Role: Third-person narrator / Book exposition)")
        for c in candidate_characters:
            name = c.get("name", "Unknown")
            if name.lower() == "narrador":
                continue
            gender = c.get("gender", "unspecified")
            desc = c.get("description") or c.get("sample_quote") or "Character in novel"
            lines.append(f"- {name} (Gender: {gender}, Notes: {desc})")
        return "\n".join(lines)

    def _call_llm(self, prompt: str, system_override: Optional[str] = None) -> str:
        is_gemini = (self.provider.name.lower().find("gemini") != -1) or ("generativelanguage.googleapis.com" in self.provider.api_base)
        system_content = system_override or SYSTEM_PROMPT

        if is_gemini:
            # Normalize base
            clean_base = self.provider.api_base.rstrip("/")
            if "generativelanguage.googleapis.com" in clean_base and not clean_base.endswith("/openai"):
                clean_base = "https://generativelanguage.googleapis.com/v1beta/openai"

            # 1. Try OpenAI-compatible endpoint
            openai_endpoint = f"{clean_base}/chat/completions"
            headers = {"Content-Type": "application/json"}
            if self.provider.api_key:
                headers["Authorization"] = f"Bearer {self.provider.api_key}"

            payload = {
                "model": self.provider.default_model,
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.provider.temperature or 0.2,
                "max_tokens": 3000
            }

            try:
                resp = requests.post(openai_endpoint, headers=headers, json=payload, timeout=self.provider.timeout_seconds or 60)
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"].strip()
            except Exception:
                pass

            # 2. Fallback to Native Gemini REST endpoint
            native_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.provider.default_model}:generateContent?key={self.provider.api_key}"
            native_payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": system_content}]},
                "generationConfig": {
                    "temperature": self.provider.temperature or 0.2,
                    "maxOutputTokens": 3000
                }
            }
            resp_nat = requests.post(native_endpoint, json=native_payload, timeout=self.provider.timeout_seconds or 60)
            if resp_nat.status_code == 200:
                data = resp_nat.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])
                if parts:
                    return parts[0].get("text", "").strip()
            raise RuntimeError(f"Google Gemini request failed (Status {resp_nat.status_code}): {resp_nat.text[:300]}")

        # Standard OpenAI-Compatible Endpoints
        endpoint = f"{self.provider.api_base.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.provider.api_key:
            headers["Authorization"] = f"Bearer {self.provider.api_key}"

        payload = {
            "model": self.provider.default_model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.provider.temperature or 0.2,
            "max_tokens": 3000
        }

        resp = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=self.provider.timeout_seconds or 60
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM request failed (Status {resp.status_code}): {resp.text[:300]}")

        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    def _parse_llm_json(self, raw_text: str) -> List[Dict[str, Any]]:
        # Strip markdown code fencing if present
        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
        clean = clean.strip()

        # Locate JSON array brackets
        start_idx = clean.find("[")
        end_idx = clean.rfind("]")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            clean = clean[start_idx:end_idx + 1]

        try:
            return json.loads(clean)
        except Exception:
            # Try fixing trailing commas
            clean_fixed = re.sub(r",\s*\]", "]", clean)
            clean_fixed = re.sub(r",\s*\}", "}", clean_fixed)
            return json.loads(clean_fixed)

    def direct_chapter_script(
        self,
        script: ChapterScript,
        candidate_characters: Optional[List[Dict[str, Any]]] = None,
        vb: Optional[VoiceBank] = None,
        batch_size: int = 25,
        refine_speakers: bool = True,
        refine_instructs: bool = True,
        insert_audio_tokens: bool = True,
        progress_callback: Optional[Callable[[int, int, int, str], None]] = None
    ) -> Tuple[ChapterScript, List[Dict[str, Any]]]:
        """
        Runs the AI Director over the chapter segments in context-preserving batches.
        Returns the updated ChapterScript and a changelog diff list.
        """
        # 1. Build candidates list
        if candidate_characters is None:
            if vb is not None:
                candidate_characters = [
                    {"name": k, "gender": v.gender, "description": v.description or v.instruct}
                    for k, v in vb.config.characters.items()
                ]
            else:
                candidate_characters = []

        char_context = self._build_character_context(candidate_characters)
        segments = script.segments
        total_segs = len(segments)
        diff_changelog = []

        batches = []
        for i in range(0, total_segs, batch_size):
            batches.append(segments[i:i + batch_size])

        total_batches = len(batches)

        for b_idx, batch in enumerate(batches):
            if progress_callback:
                progress_callback(
                    b_idx + 1,
                    total_batches,
                    len(diff_changelog),
                    f"Analyzing lines {batch[0].id} to {batch[-1].id} ({b_idx + 1}/{total_batches})..."
                )

            # Build batch prompt
            batch_lines = []
            for seg in batch:
                batch_lines.append(f'[{seg.id}] CurrentSpeaker: "{seg.speaker}" | Text: "{seg.text}"')

            prompt = f"""{char_context}

VALID DELIVERY INSTRUCT EXAMPLES (for OmniVoice / Qwen3 / CosyVoice):
{json.dumps(VALID_INSTRUCT_TAGS, indent=2)}

VALID AUDIO EXPRESSION TOKENS:
[laughter], [gasp], [sigh], [groan], [pant], or null

SEGMENTS TO DIRECT (Lines {batch[0].id} - {batch[-1].id}):
{chr(10).join(batch_lines)}

INSTRUCTIONS:
Return a JSON array containing one object per input segment in this exact structure:
[
  {{
    "id": <int>,
    "speaker": "<Exact Candidate Name or 'Narrador'>",
    "instruct": "<Valid delivery tags or null if Narrador>",
    "audio_token": "<e.g. '[gasp]' or '[laughter]' or null>",
    "speed": <float 0.85 to 1.15, default 1.0>,
    "explanation": "<Brief explanation for this attribution>"
  }}
]
"""
            try:
                raw_response = self._call_llm(prompt)
                results = self._parse_llm_json(raw_response)
                res_by_id = {item.get("id"): item for item in results if isinstance(item, dict) and "id" in item}

                for seg in batch:
                    if seg.id in res_by_id:
                        fix = res_by_id[seg.id]
                        new_speaker = fix.get("speaker") or seg.speaker
                        new_instruct = fix.get("instruct")
                        audio_tok = fix.get("audio_token")
                        speed = fix.get("speed", seg.speed or 1.0)
                        explanation = fix.get("explanation", "")

                        changed = False
                        old_spk = seg.speaker
                        old_inst = seg.instruct
                        old_text = seg.text

                        # Apply Speaker Refinement
                        if refine_speakers and new_speaker and new_speaker != seg.speaker:
                            seg.speaker = new_speaker
                            changed = True

                        # Apply Audio Token (prepend [laughter], [gasp], etc.)
                        if insert_audio_tokens and audio_tok and audio_tok in AUDIO_TOKENS:
                            clean_t = re.sub(r'^\[(?:laughter|gasp|sigh|groan|pant)\]\s*', '', seg.text).strip()
                            seg.text = f"{audio_tok} {clean_t}"
                            if seg.text != old_text:
                                changed = True

                        # Apply Instruct / Tone
                        if refine_instructs:
                            if seg.speaker.lower() == "narrador":
                                seg.instruct = None
                            elif new_instruct:
                                seg.instruct = new_instruct
                                changed = True
                            if speed and speed != seg.speed:
                                seg.speed = speed
                                changed = True

                        if changed:
                            # Recompute hash for cache invalidation
                            seg.compute_hash()
                            diff_changelog.append({
                                "id": seg.id,
                                "old_speaker": old_spk,
                                "new_speaker": seg.speaker,
                                "text": seg.text,
                                "old_instruct": old_inst,
                                "new_instruct": seg.instruct,
                                "explanation": explanation
                            })

            except Exception as e:
                print(f"[AIDirector] Batch {b_idx + 1} processing warning: {e}. Keeping original segment values.")

        if progress_callback:
            progress_callback(
                total_batches,
                total_batches,
                len(diff_changelog),
                f"✓ Finished directing chapter. Corrected {len(diff_changelog)} line(s)."
            )

        return script, diff_changelog
