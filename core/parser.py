import os
import re
import zipfile
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from novelcast.core.schema import ChapterScript, Segment
from novelcast.core.director import Director

def clean_paragraph_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'")
    return text

class BookParser:
    def __init__(self, director: Optional[Director] = None):
        self.director = director or Director()

    def parse_epub_chapters(self, epub_path: str) -> List[Dict[str, Any]]:
        """Discovers and orders chapter documents from an EPUB."""
        chapters = []
        with zipfile.ZipFile(epub_path, 'r') as z:
            namelist = z.namelist()
            # Prioritize XHTML text documents
            text_files = [f for f in namelist if f.endswith(('.xhtml', '.html', '.htm')) and not any(k in f.lower() for k in ['nav', 'toc', 'cover', 'titlepage', 'style', 'page_'])]
            text_files.sort()
            
            # Simple automatic chapter grouping
            for i, fpath in enumerate(text_files):
                fname = os.path.basename(fpath)
                chap_id = f"{i:02d}_{os.path.splitext(fname)[0]}"
                chapters.append({
                    "id": chap_id,
                    "title": f"Chapter {i+1}: {os.path.splitext(fname)[0]}",
                    "files": [fpath]
                })
        return chapters

    def parse_html_to_script(self, html_content: str, chapter_id: str, title: str, book_name: str = "Audiobook") -> ChapterScript:
        soup = BeautifulSoup(html_content, 'html.parser')
        raw_paragraphs = [p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5'])]
        
        segments = []
        seg_id = 1
        last_speaker = "Narrador"

        # Chapter announcement intro
        segments.append(Segment(
            id=seg_id,
            speaker="Narrador",
            text=f"{title}.",
            pause_after_ms=1000
        ))
        seg_id += 1

        for i, p_raw in enumerate(raw_paragraphs):
            p = clean_paragraph_text(p_raw)
            if not p or len(p) < 2:
                continue

            dash_match = re.match(r'^[―—–\-]\s*(.*)$', p)
            quote_match = re.match(r'^["«“]\s*(.*?)["»”]?$', p)

            is_dialogue = False
            dialogue_text = ""

            if dash_match:
                is_dialogue = True
                dialogue_text = dash_match.group(1).strip()
                dialogue_text = re.sub(r'\s*[―—–\-]$', '', dialogue_text).strip()
            elif quote_match:
                is_dialogue = True
                dialogue_text = quote_match.group(1).strip()

            if is_dialogue and len(dialogue_text) > 1:
                prev_p = raw_paragraphs[i-1] if i > 0 else ""
                next_p = raw_paragraphs[i+1] if i + 1 < len(raw_paragraphs) else ""
                speaker = self.director.identify_speaker(dialogue_text, prev_p, next_p, last_speaker=last_speaker)
                last_speaker = speaker

                final_text, instruct, speed, guidance = self.director.analyze_emotion_and_delivery(dialogue_text, prev_p, next_p, speaker)

                seg = Segment(
                    id=seg_id,
                    speaker=speaker,
                    text=final_text,
                    instruct=instruct,
                    speed=speed,
                    guidance_scale=guidance,
                    pause_after_ms=400
                )
                seg.compute_hash()
                segments.append(seg)
                seg_id += 1
            else:
                last_speaker = "Narrador"
                # Chunk longer narration paragraphs into natural speech segments
                if len(p) > 380:
                    sentences = re.split(r'(?<=[.?!])\s+', p)
                    chunk = ""
                    for s in sentences:
                        if len(chunk) + len(s) < 320:
                            chunk += (" " if chunk else "") + s
                        else:
                            if chunk:
                                seg = Segment(
                                    id=seg_id,
                                    speaker="Narrador",
                                    text=chunk.strip(),
                                    pause_after_ms=450
                                )
                                seg.compute_hash()
                                segments.append(seg)
                                seg_id += 1
                            chunk = s
                    if chunk:
                        seg = Segment(
                            id=seg_id,
                            speaker="Narrador",
                            text=chunk.strip(),
                            pause_after_ms=500
                        )
                        seg.compute_hash()
                        segments.append(seg)
                        seg_id += 1
                else:
                    seg = Segment(
                        id=seg_id,
                        speaker="Narrador",
                        text=p,
                        pause_after_ms=500
                    )
                    seg.compute_hash()
                    segments.append(seg)
                    seg_id += 1

        return ChapterScript(
            title=title,
            book=book_name,
            chapter_id=chapter_id,
            segments=segments
        )
