import os
import json
import time
import requests
import subprocess
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from novelcast.core.schema import Segment, ChapterScript, CharacterVoice
from novelcast.core.voice_bank import VoiceBank
from novelcast.engines import get_engine
from novelcast.core.stitcher import AudioStitcher
from novelcast.core.packager import AudiobookPackager

app = FastAPI(title="NovelCast Studio API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background task state tracker
tasks_status: Dict[str, Dict[str, Any]] = {}

# ─────────────────────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────────────────────
class EngineConfigRequest(BaseModel):
    engine: str = "omnivoice"
    mode: str = "remote"  # "remote" or "local"
    remote_url: Optional[str] = "http://192.168.0.180:9880/synthesize"
    workers: int = 4
    guidance_scale: float = 2.8

class RegenerateSegmentRequest(BaseModel):
    project_id: str
    chapter_id: str
    segment: Segment
    engine: str = "omnivoice"
    mode: str = "remote"
    remote_url: Optional[str] = "http://192.168.0.180:9880/synthesize"

class UpdateScriptRequest(BaseModel):
    title: Optional[str] = None
    segments: List[Segment]

class AssignVoiceRequest(BaseModel):
    character: str
    voice_file: str
    gender: Optional[str] = "unspecified"
    instruct: Optional[str] = None

class StitchRequest(BaseModel):
    project_id: str
    chapter_id: Optional[str] = None  # None for all chapters
    speaker_change_ms: int = 600
    same_speaker_ms: int = 400

class PackageM4BRequest(BaseModel):
    project_id: str
    title: str = "NovelCast Audiobook"
    author: str = "Tappei Nagatsuki"
    cover_image: Optional[str] = None
    bitrate: str = "128k"

# ─────────────────────────────────────────────────────────────
# Helper Utilities & Project Registry
# ─────────────────────────────────────────────────────────────
PROJECT_DIRS = {
    "vol2": {"name": "Re:Zero Vol 2", "path": "data/scripts", "cache": "cache_omnivoice", "output": "output/volume_2"},
    "vol3": {"name": "Re:Zero Vol 3", "path": "data/scripts_vol3", "cache": "cache_omnivoice", "output": "output/volume_3"},
    "dub": {"name": "Mushoku Tensei Dub", "path": "workspace_dub/scripts", "cache": "workspace_dub/cache_omnivoice", "output": "workspace_dub/chapters_audio"}
}
PROJECTS_REGISTRY_FILE = "projects.json"

def get_all_projects_registry() -> Dict[str, Dict[str, str]]:
    projects = dict(PROJECT_DIRS)
    if os.path.exists(PROJECTS_REGISTRY_FILE):
        try:
            with open(PROJECTS_REGISTRY_FILE, "r", encoding="utf-8") as f:
                custom = json.load(f)
                projects.update(custom)
        except Exception:
            pass
    return projects

def save_custom_project(project_id: str, project_info: Dict[str, str]):
    custom = {}
    if os.path.exists(PROJECTS_REGISTRY_FILE):
        try:
            with open(PROJECTS_REGISTRY_FILE, "r", encoding="utf-8") as f:
                custom = json.load(f)
        except Exception:
            custom = {}
    custom[project_id] = project_info
    with open(PROJECTS_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(custom, f, ensure_ascii=False, indent=2)

def resolve_project_dir(project_id: str) -> Dict[str, str]:
    all_p = get_all_projects_registry()
    if project_id in all_p:
        return all_p[project_id]
    if os.path.exists(project_id):
        return {"name": os.path.basename(project_id), "path": project_id, "cache": "cache_omnivoice", "output": "output"}
    raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

# ─────────────────────────────────────────────────────────────
# 1. Engine & Health Endpoints
# ─────────────────────────────────────────────────────────────
@app.get("/api/engine/status")
def get_engine_status(remote_url: str = "http://192.168.0.180:9880/synthesize"):
    """Checks remote GPU server status and local hardware capabilities."""
    local_info = {"device": "cpu", "available": True}
    try:
        import torch
        if torch.cuda.is_available():
            local_info = {"device": "cuda", "name": torch.cuda.get_device_name(0), "available": True}
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            local_info = {"device": "mps (Apple Silicon)", "available": True}
    except Exception:
        pass

    remote_info = {"online": False, "latency_ms": 0, "error": None}
    if remote_url:
        start_t = time.time()
        try:
            health_url = remote_url.replace("/synthesize", "/health")
            resp = requests.get(health_url, timeout=2.0)
            latency = int((time.time() - start_t) * 1000)
            remote_info = {
                "online": resp.status_code in [200, 404, 405],
                "latency_ms": latency,
                "status_code": resp.status_code
            }
        except Exception as e:
            remote_info = {"online": False, "latency_ms": 0, "error": str(e)}

    return {
        "local": local_info,
        "remote": remote_info,
        "default_remote_url": remote_url
    }

# ─────────────────────────────────────────────────────────────
# 2. Project & Script Endpoints
# ─────────────────────────────────────────────────────────────
@app.get("/api/projects")
def list_projects():
    """Lists all available audiobook projects in workspace."""
    results = []
    all_p = get_all_projects_registry()
    for pid, pinfo in all_p.items():
        exists = os.path.exists(pinfo["path"])
        ch_count = len([f for f in os.listdir(pinfo["path"]) if f.endswith(".json")]) if exists else 0
        results.append({
            "id": pid,
            "name": pinfo["name"],
            "path": pinfo["path"],
            "cache_dir": pinfo["cache"],
            "output_dir": pinfo["output"],
            "chapters_count": ch_count,
            "exists": exists,
            "is_custom": pid not in PROJECT_DIRS
        })
    return results

@app.post("/api/projects/create")
async def create_project(
    name: str = Form(...),
    project_type: str = Form("epub"),
    author: Optional[str] = Form("Author"),
    file: Optional[UploadFile] = File(None),
    local_path: Optional[str] = Form(None)
):
    """
    Creates a new project, parses uploaded or local EPUB files into chapter scripts,
    extracts cover art, and registers it in the studio project list.
    """
    import zipfile
    import shutil
    import re
    from novelcast.core.parser import BookParser

    # Generate slug ID
    slug = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower()).strip('_')
    if not slug:
        slug = f"project_{int(time.time())}"

    proj_dir = os.path.join("projects", slug)
    scripts_dir = os.path.join(proj_dir, "data", "scripts")
    output_dir = os.path.join(proj_dir, "output")
    cache_dir = os.path.join(proj_dir, "cache_omnivoice")
    
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    target_book_path = None

    # 1. Handle file upload or local path
    if file and file.filename:
        upload_path = os.path.join(proj_dir, file.filename)
        with open(upload_path, "wb") as f_out:
            shutil.copyfileobj(file.file, f_out)
        target_book_path = upload_path
    elif local_path and os.path.exists(local_path):
        target_book_path = local_path

    chapters_parsed = 0
    total_segments = 0

    # 2. Parse EPUB if provided
    if target_book_path and target_book_path.lower().endswith(".epub"):
        parser = BookParser()
        chapters_meta = parser.parse_epub_chapters(target_book_path)
        
        with zipfile.ZipFile(target_book_path, 'r') as z:
            # Extract cover art if present
            for zname in z.namelist():
                if any(k in zname.lower() for k in ['cover', 'portada', '000', '01.jpg', '001']) and zname.lower().endswith(('.jpg', '.jpeg', '.png')):
                    cover_dest = os.path.join(output_dir, "cover.jpg")
                    with open(cover_dest, "wb") as cf:
                        cf.write(z.read(zname))
                    break

            for cinfo in chapters_meta:
                chap_id = cinfo["id"]
                chap_title = cinfo["title"]
                files = cinfo["files"]

                html_contents = []
                for fpath in files:
                    if fpath in z.namelist():
                        html_contents.append(z.read(fpath).decode('utf-8', errors='ignore'))

                script = parser.parse_html_to_script(html_contents, chapter_id=chap_id, title=chap_title, book_name=name)
                
                out_path = os.path.join(scripts_dir, f"{chap_id}.json")
                with open(out_path, "w", encoding="utf-8") as f_out:
                    json.dump(script.model_dump(), f_out, ensure_ascii=False, indent=2)

                chapters_parsed += 1
                total_segments += len(script.segments)

    # 3. Register in project registry
    pinfo = {
        "name": name,
        "author": author or "Author",
        "path": scripts_dir,
        "cache": cache_dir,
        "output": output_dir,
        "type": project_type
    }
    save_custom_project(slug, pinfo)

    return {
        "success": True,
        "project_id": slug,
        "name": name,
        "chapters_count": chapters_parsed,
        "total_segments": total_segments,
        "scripts_dir": scripts_dir
    }

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    """Deletes a custom project from the registry."""
    if not os.path.exists(PROJECTS_REGISTRY_FILE):
        raise HTTPException(status_code=404, detail="No custom projects found")

    with open(PROJECTS_REGISTRY_FILE, "r", encoding="utf-8") as f:
        custom = json.load(f)

    if project_id in custom:
        del custom[project_id]
        with open(PROJECTS_REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(custom, f, ensure_ascii=False, indent=2)
        return {"success": True, "deleted": project_id}

    raise HTTPException(status_code=404, detail="Project not found in registry")

@app.get("/api/scripts/{project_id}")
def list_chapters(project_id: str):
    """Lists all chapter scripts within a project."""
    pinfo = resolve_project_dir(project_id)
    scripts_dir = pinfo["path"]
    if not os.path.exists(scripts_dir):
        return []

    chapters = []
    engine = get_engine("omnivoice", cache_dir=pinfo["cache"])

    for f in sorted(os.listdir(scripts_dir)):
        if f.endswith(".json"):
            fpath = os.path.join(scripts_dir, f)
            try:
                with open(fpath, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                segs = data.get("segments", [])
                
                # Count cached chunks
                cached_count = 0
                for s in segs:
                    dseg = Segment(**s)
                    cpath = engine.get_cache_path(dseg)
                    if os.path.exists(cpath) and os.path.getsize(cpath) > 100:
                        cached_count += 1

                chapters.append({
                    "file": f,
                    "chapter_id": data.get("chapter_id", os.path.splitext(f)[0]),
                    "title": data.get("title", f),
                    "book": data.get("book", pinfo["name"]),
                    "total_segments": len(segs),
                    "cached_segments": cached_count,
                    "is_ready": cached_count == len(segs) and len(segs) > 0
                })
            except Exception:
                continue

    return chapters

@app.get("/api/scripts/{project_id}/{chapter_id}")
def get_chapter_script(project_id: str, chapter_id: str):
    """Gets full script data for a chapter with cache state per line."""
    pinfo = resolve_project_dir(project_id)
    scripts_dir = pinfo["path"]
    
    target_path = None
    for f in os.listdir(scripts_dir):
        if f.endswith(".json") and (f == chapter_id or f == f"{chapter_id}.json" or chapter_id in f):
            target_path = os.path.join(scripts_dir, f)
            break

    if not target_path or not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Chapter script not found")

    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    engine = get_engine("omnivoice", cache_dir=pinfo["cache"])
    
    # Enrich segments with cache state & audio stream url
    enriched_segments = []
    for s in data.get("segments", []):
        dseg = Segment(**s)
        cpath = engine.get_cache_path(dseg)
        has_cache = os.path.exists(cpath) and os.path.getsize(cpath) > 100
        
        s_dict = dseg.model_dump()
        s_dict["is_cached"] = has_cache
        s_dict["audio_url"] = f"/api/audio/chunk?path={cpath}" if has_cache else None
        enriched_segments.append(s_dict)

    data["segments"] = enriched_segments
    return data

@app.put("/api/scripts/{project_id}/{chapter_id}")
def update_chapter_script(project_id: str, chapter_id: str, req: UpdateScriptRequest):
    """Saves edits to a chapter script."""
    pinfo = resolve_project_dir(project_id)
    scripts_dir = pinfo["path"]
    
    target_path = None
    for f in os.listdir(scripts_dir):
        if f.endswith(".json") and (f == chapter_id or f == f"{chapter_id}.json" or chapter_id in f):
            target_path = os.path.join(scripts_dir, f)
            break

    if not target_path:
        target_path = os.path.join(scripts_dir, f"{chapter_id}.json")

    # Read existing script if present
    existing_data = {}
    if os.path.exists(target_path):
        with open(target_path, "r", encoding="utf-8") as f:
            existing_data = json.load(f)

    existing_data["segments"] = [s.model_dump() for s in req.segments]
    if req.title:
        existing_data["title"] = req.title

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)

    return {"success": True, "saved_segments": len(req.segments)}

# ─────────────────────────────────────────────────────────────
# 3. Live Single-Line Audition & Re-roll
# ─────────────────────────────────────────────────────────────
@app.post("/api/segments/regenerate")
def regenerate_single_segment(req: RegenerateSegmentRequest):
    """
    Synthesizes a single segment on the fly for live audio auditioning.
    Supports both local and remote OmniVoice.
    """
    pinfo = resolve_project_dir(req.project_id)
    vb = VoiceBank(voice_bank_dir="voice_bank")
    vb.auto_discover_voices()

    remote_url = req.remote_url if req.mode == "remote" else None
    engine = get_engine(req.engine, remote_url=remote_url, cache_dir=pinfo["cache"])

    cache_path = engine.get_cache_path(req.segment)
    
    # Remove existing cache if forcing re-roll
    if os.path.exists(cache_path):
        try: os.remove(cache_path)
        except Exception: pass

    success = engine.synthesize_chunk(req.segment, vb, cache_path)
    if success and os.path.exists(cache_path):
        return {
            "success": True,
            "hash": req.segment.audio_hash,
            "audio_url": f"/api/audio/chunk?path={cache_path}&t={int(time.time())}"
        }
    
    raise HTTPException(status_code=500, detail="Failed to synthesize segment audio")

# ─────────────────────────────────────────────────────────────
# 4. Voice Bank Endpoints
# ─────────────────────────────────────────────────────────────
@app.get("/api/voices")
def get_voices():
    """Lists registered character voices and audio samples."""
    vb = VoiceBank(voice_bank_dir="voice_bank")
    vb.auto_discover_voices()
    
    chars = vb.list_characters()
    
    # Collect all available sample files
    samples = []
    if os.path.exists("voice_bank"):
        for root, _, files in os.walk("voice_bank"):
            for f in sorted(files):
                if f.endswith((".wav", ".mp3", ".flac", ".m4a")):
                    rel_path = os.path.relpath(os.path.join(root, f), "voice_bank")
                    full_path = os.path.join(root, f)
                    samples.append({
                        "name": rel_path,
                        "audio_url": f"/api/audio/sample?name={rel_path}",
                        "size_kb": int(os.path.getsize(full_path) / 1024)
                    })

    return {
        "voices": {k: v.model_dump() for k, v in chars.items()},
        "available_samples": samples,
        "default_voice": vb.config.default_narrator or "narrador.wav"
    }

@app.post("/api/voices/assign")
def assign_character_voice(req: AssignVoiceRequest):
    """Assigns a reference audio sample to a character."""
    vb = VoiceBank(voice_bank_dir="voice_bank")
    char_key = req.character.title()
    ref_path = os.path.join("voice_bank", req.voice_file)
    
    vb.config.characters[char_key] = CharacterVoice(
        gender=req.gender or "unspecified",
        instruct=req.instruct,
        description=f"Assigned voice: {req.voice_file}",
        reference_audio=ref_path if os.path.exists(ref_path) else req.voice_file
    )
    vb.save()
    return {"success": True, "character": req.character, "voice_file": req.voice_file}

# ─────────────────────────────────────────────────────────────
# 5. Audio Streaming
# ─────────────────────────────────────────────────────────────
@app.get("/api/audio/chunk")
def stream_audio_chunk(path: str = Query(...)):
    """Streams a cached MP3/WAV segment chunk directly to the browser."""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audio chunk not found")
    return FileResponse(path, media_type="audio/mpeg")

@app.get("/api/audio/sample")
def stream_voice_sample(name: str = Query(...)):
    """Streams a reference voice audio sample."""
    sample_path = os.path.join("voice_bank", name)
    if not os.path.exists(sample_path):
        # Check all_voices
        sample_path = os.path.join("voice_bank", "all_voices", name)
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Voice sample not found")
    
    ext = os.path.splitext(name)[1].lower()
    media_type = "audio/wav" if ext == ".wav" else "audio/mpeg"
    return FileResponse(sample_path, media_type=media_type)

@app.get("/api/audio/chapter")
def stream_chapter_audio(project_id: str, chapter_id: str):
    """Streams the full stitched chapter MP3."""
    pinfo = resolve_project_dir(project_id)
    ch_file = os.path.join(pinfo["output"], "chapters", f"{chapter_id}.mp3")
    if not os.path.exists(ch_file):
        # check direct output
        ch_file = os.path.join(pinfo["output"], f"{chapter_id}.mp3")
    if not os.path.exists(ch_file):
        raise HTTPException(status_code=404, detail="Stitched chapter audio not found")
    return FileResponse(ch_file, media_type="audio/mpeg")

# ─────────────────────────────────────────────────────────────
# 6. Batch Generation, Stitching & M4B Packaging Actions
# ─────────────────────────────────────────────────────────────
class GenerateTaskRequest(BaseModel):
    project_id: str
    chapter_id: Optional[str] = None
    engine: str = "omnivoice"
    mode: str = "remote"
    remote_url: Optional[str] = "http://192.168.0.180:9880/synthesize"
    workers: int = 4

@app.post("/api/tasks/generate")
def batch_generate_audio(req: GenerateTaskRequest):
    """Batch synthesizes speech audio chunks for a chapter or entire project with multi-worker acceleration."""
    pinfo = resolve_project_dir(req.project_id)
    scripts_dir = pinfo["path"]
    cache_dir = pinfo["cache"]

    vb = VoiceBank(voice_bank_dir="voice_bank")
    vb.auto_discover_voices()
    
    remote_url = req.remote_url if req.mode == "remote" else None
    engine = get_engine(req.engine, remote_url=remote_url, cache_dir=cache_dir, workers=req.workers)

    target_files = []
    if req.chapter_id:
        target_files = [f"{req.chapter_id}.json" if not req.chapter_id.endswith(".json") else req.chapter_id]
    else:
        target_files = sorted([f for f in os.listdir(scripts_dir) if f.endswith(".json")])

    total_chunks = 0
    generated_chunks = 0
    cached_chunks = 0

    for tf in target_files:
        s_path = os.path.join(scripts_dir, tf)
        if not os.path.exists(s_path):
            continue
        with open(s_path, "r", encoding="utf-8") as fp:
            s_data = json.load(fp)
            cscript = ChapterScript(**s_data)

        missing_segs = []
        for s in cscript.segments:
            cpath = engine.get_cache_path(s)
            total_chunks += 1
            if os.path.exists(cpath) and os.path.getsize(cpath) > 100:
                cached_chunks += 1
            else:
                missing_segs.append(s)

        if missing_segs:
            sub_script = ChapterScript(
                title=cscript.title,
                book=cscript.book,
                chapter_id=cscript.chapter_id,
                segments=missing_segs
            )
            success = engine.synthesize_chapter(sub_script, vb)
            if success:
                generated_chunks += len(missing_segs)

    return {
        "success": True,
        "total_chunks": total_chunks,
        "newly_generated": generated_chunks,
        "already_cached": cached_chunks
    }
@app.post("/api/tasks/stitch")
def stitch_project_chapter(req: StitchRequest):
    """Stitches chapter scripts into MP3 tracks."""
    pinfo = resolve_project_dir(req.project_id)
    scripts_dir = pinfo["path"]
    cache_dir = pinfo["cache"]
    out_dir = os.path.join(pinfo["output"], "chapters")
    os.makedirs(out_dir, exist_ok=True)

    from novelcast.core.schema import PauseSettings
    pauses = PauseSettings(speaker_change_ms=req.speaker_change_ms, same_speaker_ms=req.same_speaker_ms)
    stitcher = AudioStitcher(pause_settings=pauses)
    engine = get_engine("omnivoice", cache_dir=cache_dir)

    target_files = []
    if req.chapter_id:
        target_files = [f"{req.chapter_id}.json" if not req.chapter_id.endswith(".json") else req.chapter_id]
    else:
        target_files = sorted([f for f in os.listdir(scripts_dir) if f.endswith(".json")])

    results = []
    for tf in target_files:
        s_path = os.path.join(scripts_dir, tf)
        if not os.path.exists(s_path):
            continue
        with open(s_path, "r", encoding="utf-8") as fp:
            s_data = json.load(fp)
            cscript = ChapterScript(**s_data)

        audio_files = [engine.get_cache_path(s) for s in cscript.segments]
        out_mp3 = os.path.join(out_dir, f"{cscript.chapter_id}.mp3")
        
        success = stitcher.stitch_chapter(cscript, audio_files, out_mp3)
        results.append({
            "chapter_id": cscript.chapter_id,
            "success": success,
            "file": out_mp3,
            "size_mb": round(os.path.getsize(out_mp3) / (1024*1024), 2) if os.path.exists(out_mp3) else 0
        })

    return {"success": True, "stitched_chapters": results}

@app.post("/api/tasks/package")
def package_master_m4b(req: PackageM4BRequest):
    """Packages all stitched chapters into a master M4B."""
    pinfo = resolve_project_dir(req.project_id)
    chapters_dir = os.path.join(pinfo["output"], "chapters")
    if not os.path.exists(chapters_dir):
        chapters_dir = pinfo["output"]

    mp3_files = sorted([f for f in os.listdir(chapters_dir) if f.endswith((".mp3", ".m4a"))])
    if not mp3_files:
        raise HTTPException(status_code=400, detail="No chapter MP3 files found to package")

    cover_art = req.cover_image
    if not cover_art or not os.path.exists(cover_art):
        # Try finding standard cover in output dir
        for cname in ["cover.jpg", "cover_vol2.jpg", "cover_vol3.jpg", "cover.png"]:
            cand = os.path.join(pinfo["output"], cname)
            if os.path.exists(cand):
                cover_art = cand
                break

    out_m4b = os.path.join(pinfo["output"], f"{req.title.replace(' ', '_')}.m4b")
    
    chapter_entries = []
    for f in mp3_files:
        base_name = os.path.splitext(f)[0]
        chapter_entries.append({
            "title": base_name.replace("_", " ").title(),
            "audio_path": os.path.join(chapters_dir, f)
        })

    packager = AudiobookPackager(bitrate=req.bitrate)
    success = packager.package_m4b(
        chapter_files=chapter_entries,
        output_m4b_path=out_m4b,
        book_title=req.title,
        author=req.author,
        cover_image_path=cover_art
    )

    if success and os.path.exists(out_m4b):
        return {
            "success": True,
            "m4b_path": out_m4b,
            "size_mb": round(os.path.getsize(out_m4b) / (1024*1024), 2),
            "download_url": f"/api/audio/download?path={out_m4b}"
        }

    raise HTTPException(status_code=500, detail="Failed to package master M4B")

@app.get("/api/audio/download")
def download_file(path: str = Query(...)):
    """Downloads a finished master M4B or MP3."""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    filename = os.path.basename(path)
    return FileResponse(path, filename=filename, media_type="application/octet-stream")

# ─────────────────────────────────────────────────────────────
# 7. Static Web Frontend Mount
# ─────────────────────────────────────────────────────────────
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.exists(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "NovelCast Studio API is running. Web UI not found in novelcast/web."}
