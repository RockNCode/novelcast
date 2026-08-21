import os
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from novelcast.core.schema import Segment, ChapterScript
from novelcast.core.voice_bank import VoiceBank
from novelcast.engines import get_engine
from novelcast.core.stitcher import AudioStitcher
from novelcast.core.packager import AudiobookPackager

app = FastAPI(title="NovelCast Studio API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RegenerateRequest(BaseModel):
    chapter_id: str
    segment: Segment
    engine: str = "omnivoice"
    remote_url: Optional[str] = "http://192.168.0.180:9880/synthesize"

@app.get("/health")
def health():
    return {"status": "ok", "service": "NovelCast Studio API"}

@app.get("/api/voices")
def get_voices(config_path: str = "voice_config.json"):
    vb = VoiceBank(config_path=config_path)
    return vb.config.model_dump()

@app.get("/api/scripts")
def list_scripts(scripts_dir: str = "data/scripts"):
    if not os.path.exists(scripts_dir):
        return []
    res = []
    for f in sorted(os.listdir(scripts_dir)):
        if f.endswith(".json"):
            with open(os.path.join(scripts_dir, f), "r", encoding="utf-8") as fp:
                data = json.load(fp)
                res.append({
                    "file": f,
                    "chapter_id": data.get("chapter_id", f),
                    "title": data.get("title", f),
                    "segments_count": len(data.get("segments", []))
                })
    return res

@app.get("/api/scripts/{chapter_id}")
def get_script(chapter_id: str, scripts_dir: str = "data/scripts"):
    path = os.path.join(scripts_dir, f"{chapter_id}.json")
    if not os.path.exists(path):
        # Try finding partial match
        for f in os.listdir(scripts_dir):
            if chapter_id in f and f.endswith(".json"):
                path = os.path.join(scripts_dir, f)
                break

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Script not found")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/segments/regenerate")
def regenerate_segment(req: RegenerateRequest, cache_dir: str = "cache_omnivoice"):
    """Regenerates a single segment audio chunk immediately for live GUI auditioning."""
    vb = VoiceBank()
    engine = get_engine(req.engine, remote_url=req.remote_url, cache_dir=cache_dir)
    cache_path = engine.get_cache_path(req.segment)
    
    success = engine.synthesize_chunk(req.segment, vb, cache_path)
    if success and os.path.exists(cache_path):
        return {
            "success": True,
            "audio_path": cache_path,
            "hash": req.segment.audio_hash
        }
    raise HTTPException(status_code=500, detail="Failed to synthesize segment audio")
