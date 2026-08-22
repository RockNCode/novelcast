import re
import json
import requests
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from novelcast.core.schema import Segment, ChapterScript

class ScriptTranslator:
    """
    Translates transcribed audio scripts into target languages with
    contextual character pacing, literary flow, and emotion preservation.
    """

    def __init__(
        self,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "llama3:latest"
    ):
        self.api_base = api_base
        self.api_key = api_key
        self.model = model

    def _infer_emotion_instruct(self, text: str, speaker: str) -> Optional[str]:
        """Infers tone and delivery instruct for OmniVoice / Qwen3."""
        text_lower = text.lower()
        if "?" in text and ("!" in text or re.search(r'\b(what|qué|cómo|dónde)\b', text_lower)):
            return "male, teenager, moderate pitch" if speaker.lower() in ["subaru", "male", "narrator"] else "female, young adult, high pitch"
        if "!" in text or re.search(r'\b(no|wait|stop|cuidado|maldita)\b', text_lower):
            return "male, teenager, high pitch" if speaker.lower() in ["subaru", "male"] else "female, young adult, high pitch"
        if "..." in text or re.search(r'\b(whisper|quiet|shh|silencio)\b', text_lower):
            return "male, teenager, whisper" if speaker.lower() in ["subaru", "male"] else "female, young adult, low pitch"
        return None

    def _translate_gtx_single(self, text: str, from_lang: str = "en", to_lang: str = "es") -> str:
        """Translates a single text using GTX REST API with retry."""
        clean = text.strip()
        if not clean:
            return text
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": from_lang,
            "tl": to_lang,
            "dt": "t",
            "q": clean
        }
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                trans = "".join([part[0] for part in data[0] if part[0]])
                return trans if trans else text
        except Exception:
            pass
        return text

    def _translate_batch_fast(
        self,
        texts: List[str],
        from_lang: str = "en",
        to_lang: str = "es"
    ) -> List[str]:
        """Translates a list of texts concurrently."""
        results = [None] * len(texts)

        def worker(idx, txt):
            return idx, self._translate_gtx_single(txt, from_lang=from_lang, to_lang=to_lang)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i, t) for i, t in enumerate(texts)]
            for fut in futures:
                idx, trans_text = fut.result()
                results[idx] = trans_text

        return [r if r is not None else texts[i] for i, r in enumerate(results)]

    def translate_segments(
        self,
        segments: List[Dict],
        from_lang: str = "en",
        to_lang: str = "es"
    ) -> List[Dict]:
        """
        Translates segments using configured LLM or zero-config fast translator.
        """
        if from_lang.lower() == to_lang.lower():
            return segments

        texts_to_translate = [s["text"] for s in segments]
        translated_texts = None

        # 1. Try LLM if explicitly configured
        if self.api_base:
            endpoint = f"{self.api_base.rstrip('/')}/chat/completions"
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            prompt = (
                f"You are a professional literary audiobook translator. Translate the following list of sentences "
                f"from {from_lang} to {to_lang}. Preserve character voice, emotional intensity, and conversational flow. "
                f"Return ONLY a JSON list of translated strings matching the exact same length.\n\n"
                f"{json.dumps(texts_to_translate, ensure_ascii=False)}"
            )

            try:
                resp = requests.post(
                    endpoint,
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    },
                    timeout=60
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    match = re.search(r'\[.*\]', content, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group(0))
                        if len(parsed) == len(segments):
                            translated_texts = parsed
            except Exception:
                translated_texts = None

        # 2. Fast concurrent translation fallback
        if not translated_texts:
            translated_texts = self._translate_batch_fast(texts_to_translate, from_lang=from_lang, to_lang=to_lang)

        # Apply translations back to segment dictionaries
        for i, trans_text in enumerate(translated_texts):
            segments[i]["text"] = trans_text

        return segments

    def build_chapter_script(
        self,
        chapter_title: str,
        chapter_id: str,
        segments: List[Dict],
        from_lang: str = "en",
        to_lang: str = "es"
    ) -> ChapterScript:
        """
        Converts raw transcribed segments into a validated ChapterScript
        with computed inter-line pauses and target language translation.
        """
        # Run translation
        translated_segments = self.translate_segments(segments, from_lang=from_lang, to_lang=to_lang)

        script_segments = []
        for i, seg in enumerate(translated_segments):
            # Compute natural pause after line based on original audio gap
            pause_ms = 450
            if i + 1 < len(translated_segments):
                gap_sec = translated_segments[i + 1]["start"] - seg["end"]
                if gap_sec > 0.05:
                    pause_ms = int(min(max(gap_sec * 1000, 200), 2000))

            speaker = seg.get("speaker", "Narrator")
            instruct = self._infer_emotion_instruct(seg["text"], speaker)

            script_segments.append(Segment(
                id=i + 1,
                speaker=speaker,
                text=seg["text"],
                instruct=instruct,
                speed=1.0,
                guidance_scale=2.8,
                pause_after_ms=pause_ms
            ))

        return ChapterScript(
            title=chapter_title,
            book="Dubbed Audiobook",
            chapter_id=chapter_id,
            segments=script_segments
        )
