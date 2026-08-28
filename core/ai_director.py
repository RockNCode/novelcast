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
Your task is to analyze sequential lines of a novel/audiobook chapter and accurately determine:
1. The TRUE speaker of each line (distinguishing Third-Person Narration vs Character Spoken Dialogue).
2. The emotional tone / delivery instruct for voice synthesis (OmniVoice / Qwen3 / CosyVoice).
3. Any expressive vocal audio tokens (ONLY when explicit laughing, crying, sighing, gasping, or groaning occurs).

CRITICAL DIRECTIVE RULES:
1. NARRATION VS DIALOGUE:
   - Third-person exposition, descriptions of actions, scene setting, and character thoughts MUST have:
     speaker: "Narrador", instruct: null, audio_token: null.
   - Spoken dialogue (dialogue dashes —, quotes «», or direct speech) MUST be attributed to the specific character speaking.
2. REPORTING VERBS & SPEECH CLUES:
   - Check embedded or surrounding reporting verbs ("dijo X", "respondió ella", "preguntó Emilia", "murmuró la pequeña doncella", "añadió el marqués").
   - Check character nicknames and speech patterns:
     * Ram calls Subaru "Barusu" (sharp/sarcastic tone).
     * Rem calls Subaru "Subaru-kun" (gentle/polite tone).
     * Beatrice uses verbal tics ("supongo", "de hecho") and refers to herself as "Betty".
     * Roswaal uses prolonged vowels ("Bueeeno", "¿está bieeen?") and refers to "señorita Emilia".
     * Puck calls Emilia "Lia".
3. CONVERSATIONAL ALTERNATION:
   - In 2-person dialogues, spoken lines alternate between the two active characters unless interrupted by a third speaker.
4. AUDIO TOKENS:
   - audio_token MUST be null by default. Only set "[laughter]" if chuckling/laughing, "[gasp]" if gasping/shock, "[sigh]" if sighing, "[groan]" if in physical pain.
5. STRICT JSON OUTPUT:
   - Output ONLY a valid JSON array of objects with NO Markdown backticks, conversational filler, or commentary outside the JSON array.
"""

class AIDirector:
    """
    Directs audiobook dialogue attribution and emotional synthesis
    using modern LLMs (Gemini, DeepSeek, OpenAI, Groq, Ollama, LM Studio, etc.).
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
                "max_tokens": 4096
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
                    "maxOutputTokens": 4096
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
            "max_tokens": 4096
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
        """
        Robust JSON parser that handles markdown fencing, trailing commas,
        and uses a resilient object-by-object fallback to salvage segments
        if the LLM output is truncated or contains unescaped quotes.
        """
        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
        clean = clean.strip()

        # 1. Try standard JSON array parse
        s_idx = clean.find("[")
        e_idx = clean.rfind("]")
        if s_idx != -1 and e_idx != -1 and e_idx > s_idx:
            candidate = clean[s_idx:e_idx + 1]
            try:
                return json.loads(candidate)
            except Exception:
                # Attempt syntax repair on trailing commas
                candidate_repaired = re.sub(r",\s*\]", "]", candidate)
                candidate_repaired = re.sub(r",\s*\}", "}", candidate_repaired)
                try:
                    return json.loads(candidate_repaired)
                except Exception:
                    pass

        # 2. Resilient Object-by-Object Regex Extractor (salvages every completed segment)
        results = []
        for m in re.finditer(r'\{[^{}]*"id"\s*:\s*(\d+)[^{}]*\}', raw_text):
            chunk = m.group(0)
            try:
                results.append(json.loads(chunk))
            except Exception:
                # Repair trailing comma in single object
                fixed = re.sub(r',\s*\}', '}', chunk)
                try:
                    results.append(json.loads(fixed))
                except Exception:
                    pass

        return results

    def direct_chapter_script(
        self,
        script: ChapterScript,
        candidate_characters: Optional[List[Dict[str, Any]]] = None,
        vb: Optional[VoiceBank] = None,
        batch_size: int = 20,
        refine_speakers: bool = True,
        refine_instructs: bool = True,
        insert_audio_tokens: bool = True,
        progress_callback: Optional[Callable[[int, int, int, str], None]] = None
    ) -> Tuple[ChapterScript, List[Dict[str, Any]]]:
        """
        Runs the AI Director over the chapter segments in context-preserving batches
        with lookbehind dialogue context and resilient JSON recovery.
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
                    f"Directing lines {batch[0].id} to {batch[-1].id} ({b_idx + 1}/{total_batches})..."
                )

            # Preceding lookbehind context (3 lines before this batch)
            start_pos = b_idx * batch_size
            lookbehind_lines = []
            if start_pos > 0:
                prev_segs = segments[max(0, start_pos - 3):start_pos]
                for p_seg in prev_segs:
                    lookbehind_lines.append(f'[{p_seg.id}] {p_seg.speaker}: "{p_seg.text}"')

            context_block = ""
            if lookbehind_lines:
                context_block = "PREVIOUS CONVERSATION CONTEXT (Already directed):\n" + "\n".join(lookbehind_lines) + "\n\n"

            # Target lines to direct (clean text without bias)
            batch_lines = []
            for seg in batch:
                clean_text = re.sub(r'^\[(?:laughter|gasp|sigh|groan|pant)\]\s*', '', seg.text).strip()
                batch_lines.append(f'[{seg.id}] "{clean_text}"')

            prompt = f"""{char_context}

{context_block}LINES TO DIRECT (Lines {batch[0].id} - {batch[-1].id}):
{chr(10).join(batch_lines)}

INSTRUCTIONS:
Return a JSON array of objects for lines {batch[0].id} to {batch[-1].id}.
Example format:
[
  {{"id": {batch[0].id}, "speaker": "Narrador", "instruct": null, "audio_token": null}},
  {{"id": {batch[-1].id}, "speaker": "Subaru", "instruct": "male, teenager, moderate pitch", "audio_token": null}}
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

                        changed = False
                        old_spk = seg.speaker
                        old_inst = seg.instruct
                        old_text = seg.text

                        # Apply Speaker Refinement
                        if refine_speakers and new_speaker and new_speaker != seg.speaker:
                            seg.speaker = new_speaker
                            changed = True

                        # Clean any previous over-eager tokens
                        clean_text = re.sub(r'^\[(?:laughter|gasp|sigh|groan|pant)\]\s*', '', seg.text).strip()

                        # Apply Audio Token (only if valid and explicit)
                        if insert_audio_tokens and audio_tok and audio_tok in AUDIO_TOKENS:
                            seg.text = f"{audio_tok} {clean_text}"
                        else:
                            seg.text = clean_text

                        if seg.text != old_text:
                            changed = True

                        # Apply Instruct / Tone
                        if refine_instructs:
                            if seg.speaker.lower() == "narrador":
                                if seg.instruct is not None:
                                    seg.instruct = None
                                    changed = True
                            elif new_instruct:
                                if seg.instruct != new_instruct:
                                    seg.instruct = new_instruct
                                    changed = True

                        if changed:
                            # Recompute hash for cache invalidation
                            seg.compute_hash()
                            diff_changelog.append({
                                "id": seg.id,
                                "speaker_changed": (old_spk != seg.speaker),
                                "instruct_changed": (old_inst != seg.instruct),
                                "token_changed": (old_text != seg.text),
                                "old_speaker": old_spk,
                                "new_speaker": seg.speaker,
                                "text": seg.text,
                                "old_instruct": old_inst,
                                "new_instruct": seg.instruct
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
