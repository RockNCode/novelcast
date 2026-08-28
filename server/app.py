import os
import re
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
from novelcast.core.llm_manager import LLMConfigManager, LLMProviderConfig
from novelcast.core.ai_director import AIDirector
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

class VoiceProfileRequest(BaseModel):
    name: str
    reference_audio: str
    gender: Optional[str] = "unspecified"
    instruct: Optional[str] = None
    description: Optional[str] = None
    speed: float = 1.0
    guidance_scale: float = 2.8
    pause_after_ms: int = 400

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

class LLMUpdateConfigRequest(BaseModel):
    active_provider: Optional[str] = None
    active_model: Optional[str] = None
    provider_id: Optional[str] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    models: Optional[List[str]] = None
    temperature: Optional[float] = None

class LLMTestRequest(BaseModel):
    provider_id: str
    model: Optional[str] = None

class AIDirectRequest(BaseModel):
    provider_id: Optional[str] = None
    model: Optional[str] = None
    batch_size: int = 25
    refine_speakers: bool = True
    refine_instructs: bool = True
    insert_audio_tokens: bool = True

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
    """Deletes a project from the workspace registry."""
    custom = {}
    if os.path.exists(PROJECTS_REGISTRY_FILE):
        try:
            with open(PROJECTS_REGISTRY_FILE, "r", encoding="utf-8") as f:
                custom = json.load(f)
        except Exception:
            custom = {}

    deleted = False
    if project_id in custom:
        del custom[project_id]
        with open(PROJECTS_REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(custom, f, ensure_ascii=False, indent=2)
        deleted = True

    if project_id in PROJECT_DIRS:
        del PROJECT_DIRS[project_id]
        deleted = True

    if deleted:
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
# 4. Voice Bank Endpoints & Management
# ─────────────────────────────────────────────────────────────
@app.get("/api/voice-bank/library")
def get_voice_bank_library():
    """Returns the full catalog of audio samples and character voice profiles in the Voice Bank."""
    vb = VoiceBank(voice_bank_dir="voice_bank")
    vb.auto_discover_voices()
    
    chars = vb.list_characters()
    samples = []
    
    if os.path.exists("voice_bank"):
        for root, _, files in os.walk("voice_bank"):
            for f in sorted(files):
                if f.endswith((".wav", ".mp3", ".flac", ".m4a")):
                    rel_path = os.path.relpath(os.path.join(root, f), "voice_bank")
                    full_path = os.path.join(root, f)
                    
                    # Category tag from directory
                    rel_dir = os.path.dirname(rel_path)
                    if not rel_dir or rel_dir == ".":
                        category = "Default / Root"
                    elif "elevenlabs" in rel_dir:
                        category = "ElevenLabs Archive"
                    elif "all_voices" in rel_dir:
                        category = "Master Bank"
                    else:
                        category = rel_dir.replace("_", " ").title()

                    # Find characters using this reference audio
                    assigned_chars = []
                    for c_name, c_prof in chars.items():
                        if c_prof.reference_audio:
                            c_ref = c_prof.reference_audio
                            if c_ref == rel_path or c_ref.endswith(rel_path) or os.path.basename(c_ref) == f:
                                assigned_chars.append(c_name)

                    samples.append({
                        "name": rel_path,
                        "filename": f,
                        "label": os.path.splitext(f)[0].replace("_", " ").title(),
                        "category": category,
                        "audio_url": f"/api/audio/sample?name={rel_path}",
                        "size_kb": int(os.path.getsize(full_path) / 1024),
                        "assigned_characters": assigned_chars
                    })

    return {
        "characters": {k: v.model_dump() for k, v in chars.items()},
        "samples": samples,
        "total_samples": len(samples),
        "default_narrator": vb.config.default_narrator or "Narrador"
    }

@app.post("/api/voice-bank/upload")
async def upload_voice_sample(
    file: UploadFile = File(...),
    voice_name: str = Form(""),
    category: str = Form("custom"),
    gender: str = Form("unspecified"),
    instruct: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    speed: float = Form(1.0),
    guidance_scale: float = Form(2.8)
):
    """Uploads a new audio voice sample and registers it in the Voice Bank and voice_config.json."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".wav", ".mp3", ".flac", ".m4a"]:
        raise HTTPException(status_code=400, detail="Invalid audio file extension. Must be .wav, .mp3, .flac, or .m4a")

    # Determine target directory
    safe_cat = re.sub(r'[^a-zA-Z0-9_\-]', '', category.strip()) if category != "root" else ""
    target_dir = os.path.join("voice_bank", safe_cat) if safe_cat else "voice_bank"
    os.makedirs(target_dir, exist_ok=True)

    # Clean filename
    clean_base = re.sub(r'[^a-zA-Z0-9_\-]', '_', os.path.splitext(file.filename)[0]).strip('_').lower()
    clean_filename = f"{clean_base}{ext}"
    target_path = os.path.join(target_dir, clean_filename)

    # Write file
    content = await file.read()
    with open(target_path, "wb") as f:
        f.write(content)

    rel_path = os.path.relpath(target_path, "voice_bank")

    # Register in VoiceBank config
    vb = VoiceBank(voice_bank_dir="voice_bank")
    char_key = voice_name.strip() if voice_name.strip() else clean_base.replace("_", " ").title()
    
    vb.config.characters[char_key] = CharacterVoice(
        gender=gender,
        instruct=instruct,
        description=description or f"Custom uploaded voice sample: {clean_filename}",
        speed=speed,
        guidance_scale=guidance_scale,
        reference_audio=f"voice_bank/{rel_path}"
    )
    vb.save()

    return {
        "success": True,
        "character": char_key,
        "sample_path": rel_path,
        "audio_url": f"/api/audio/sample?name={rel_path}"
    }

@app.post("/api/voice-bank/profile")
def save_voice_profile(req: VoiceProfileRequest):
    """Creates or updates a character voice profile in voice_config.json."""
    vb = VoiceBank(voice_bank_dir="voice_bank")
    char_key = req.name.strip()
    
    ref_path = req.reference_audio
    if not ref_path.startswith("voice_bank/") and os.path.exists(os.path.join("voice_bank", ref_path)):
        ref_path = f"voice_bank/{ref_path}"

    vb.config.characters[char_key] = CharacterVoice(
        gender=req.gender or "unspecified",
        instruct=req.instruct,
        description=req.description or f"Voice profile for {char_key}",
        speed=req.speed,
        guidance_scale=req.guidance_scale,
        pause_after_ms=req.pause_after_ms,
        reference_audio=ref_path
    )
    vb.save()
    return {"success": True, "character": char_key, "profile": vb.config.characters[char_key].model_dump()}

@app.delete("/api/voice-bank/samples")
def delete_voice_sample(name: str = Query(...)):
    """Deletes an audio sample file from voice_bank and unbinds matching character profiles."""
    safe_rel = os.path.normpath(name).lstrip("/\\")
    if ".." in safe_rel:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    full_path = os.path.join("voice_bank", safe_rel)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"Voice sample '{safe_rel}' not found")
    
    try:
        os.remove(full_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

    # Update VoiceBank config
    vb = VoiceBank(voice_bank_dir="voice_bank")
    unbound_chars = []
    for c_name, c_prof in list(vb.config.characters.items()):
        if c_prof.reference_audio:
            if c_prof.reference_audio.endswith(safe_rel) or os.path.basename(c_prof.reference_audio) == os.path.basename(safe_rel):
                c_prof.reference_audio = None
                unbound_chars.append(c_name)
    vb.save()

    return {"success": True, "deleted_sample": safe_rel, "unbound_characters": unbound_chars}

@app.delete("/api/voice-bank/profiles/{character_name}")
def delete_voice_profile(character_name: str):
    """Deletes a character voice profile from voice_config.json."""
    vb = VoiceBank(voice_bank_dir="voice_bank")
    if character_name not in vb.config.characters:
        # Check case-insensitive
        match = None
        for k in vb.config.characters:
            if k.lower() == character_name.lower():
                match = k
                break
        if match:
            character_name = match
        else:
            raise HTTPException(status_code=404, detail=f"Character profile '{character_name}' not found")

    del vb.config.characters[character_name]
    vb.save()
    return {"success": True, "deleted_character": character_name}

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

class BatchCastRequest(BaseModel):
    assignments: Dict[str, str]

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

@app.get("/api/projects/{project_id}/characters")
def detect_project_characters(project_id: str):
    """
    Auto-detects all characters, speaker dialogue counts, and sample quotes
    from the project's scripts, matching them against VoiceBank reference files.
    """
    from novelcast.core.character_detector import CharacterDetector
    pinfo = resolve_project_dir(project_id)
    scripts_dir = pinfo["path"]
    
    vb = VoiceBank(voice_bank_dir="voice_bank")
    vb.auto_discover_voices()
    detector = CharacterDetector(voice_bank=vb)

    scripts = []
    if os.path.exists(scripts_dir):
        for f in sorted(os.listdir(scripts_dir)):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(scripts_dir, f), "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if isinstance(data, dict):
                            if "chapter_id" not in data:
                                data["chapter_id"] = os.path.splitext(f)[0]
                            if "title" not in data:
                                data["title"] = os.path.splitext(f)[0]
                            scripts.append(ChapterScript(**data))
                except Exception:
                    continue

    detected = detector.detect_from_scripts(scripts)
    
    samples = []
    if os.path.exists("voice_bank"):
        for root, _, files in os.walk("voice_bank"):
            for f in sorted(files):
                if f.endswith((".wav", ".mp3", ".flac", ".m4a")):
                    rel_path = os.path.relpath(os.path.join(root, f), "voice_bank")
                    samples.append({
                        "name": rel_path,
                        "label": os.path.splitext(os.path.basename(f))[0].replace("_", " ").title(),
                        "audio_url": f"/api/audio/sample?name={rel_path}"
                    })

    return {
        "project_id": project_id,
        "characters": detected,
        "available_samples": samples
    }

@app.post("/api/projects/{project_id}/cast_all")
def batch_cast_characters(project_id: str, req: BatchCastRequest):
    """Batch updates voice assignments for multiple characters in one shot."""
    vb = VoiceBank(voice_bank_dir="voice_bank")
    
    updated_count = 0
    for char_name, voice_file in req.assignments.items():
        if not voice_file:
            continue
        char_key = char_name.strip()
        ref_path = os.path.join("voice_bank", voice_file)
        
        existing = vb.get_character(char_key)
        gender = existing.gender if existing else ("male" if char_name.lower() in ["narrador", "subaru", "roswaal", "reinhard"] else "female")
        instruct = existing.instruct if existing else None
        
        vb.config.characters[char_key] = CharacterVoice(
            gender=gender,
            instruct=instruct,
            description=f"Cast voice: {voice_file}",
            reference_audio=ref_path if os.path.exists(ref_path) else voice_file
        )
        updated_count += 1
        
    vb.save()
    return {"success": True, "updated_characters": updated_count}

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

class RunPipelineRequest(BaseModel):
    project_id: str
    title: Optional[str] = None
    author: Optional[str] = None
    engine: str = "omnivoice"
    mode: str = "remote"
    remote_url: Optional[str] = "http://192.168.0.180:9880/synthesize"
    workers: int = 4
    speaker_change_ms: int = 600
    same_speaker_ms: int = 400
    bitrate: str = "128k"

# In-memory jobs tracking
jobs_db: Dict[str, Dict[str, Any]] = {}

def _run_pipeline_worker(job_id: str, req: RunPipelineRequest):
    try:
        pinfo = resolve_project_dir(req.project_id)
        scripts_dir = pinfo["path"]
        cache_dir = pinfo["cache"]
        output_dir = pinfo["output"]
        chapters_dir = os.path.join(output_dir, "chapters")
        os.makedirs(chapters_dir, exist_ok=True)

        job = jobs_db[job_id]
        job["status"] = "running"
        job["step"] = 1
        job["step_name"] = "Inspecting Project Scripts"
        job["progress_pct"] = 5.0
        job["logs"].append(f"Starting End-to-End Pipeline for project: {req.project_id}")

        script_files = sorted([f for f in os.listdir(scripts_dir) if f.endswith(".json")])
        if not script_files:
            raise ValueError(f"No chapter scripts found in {scripts_dir}")

        job["logs"].append(f"Found {len(script_files)} chapter script(s) to process.")

        # Step 2: Batch TTS Synthesis
        job["step"] = 2
        job["step_name"] = "Synthesizing Speech Audio Chunks"
        job["logs"].append("Step 2/4: Batch synthesizing speech audio with OmniVoice...")

        vb = VoiceBank(voice_bank_dir="voice_bank")
        vb.auto_discover_voices()
        remote_url = req.remote_url if req.mode == "remote" else None
        engine = get_engine(req.engine, remote_url=remote_url, cache_dir=cache_dir, workers=req.workers)

        # Count total segments across all scripts
        all_scripts = []
        total_segments_count = 0
        for sf in script_files:
            with open(os.path.join(scripts_dir, sf), "r", encoding="utf-8") as fp:
                data = json.load(fp)
                cs = ChapterScript(**data)
                all_scripts.append(cs)
                total_segments_count += len(cs.segments)

        job["total_items"] = total_segments_count
        job["current_item"] = 0

        processed_so_far = 0
        def check_cancelled() -> bool:
            return bool(job.get("cancel_requested", False))

        def check_paused() -> bool:
            return bool(job.get("pause_requested", False))

        for cs in all_scripts:
            if check_cancelled():
                job["status"] = "stopped"
                job["logs"].append("🛑 Pipeline stopped by user.")
                return

            def on_progress(cur, tot, seg, is_cached, success):
                nonlocal processed_so_far
                if check_cancelled():
                    job["status"] = "stopped"
                    return

                processed_so_far += 1
                job["current_item"] = processed_so_far
                step_pct = (processed_so_far / max(total_segments_count, 1)) * 65.0
                job["progress_pct"] = round(10.0 + step_pct, 1)
                
                status_str = "cached" if is_cached else "synthesized"
                if processed_so_far % 10 == 0 or processed_so_far == total_segments_count:
                    job["logs"].append(f"[{job['progress_pct']}%] Segment {processed_so_far}/{total_segments_count} ({seg.speaker}: {seg.text[:30]}...) [{status_str}]")

            engine.batch_synthesize(
                cs, vb, language="es",
                progress_callback=on_progress,
                is_cancelled=check_cancelled,
                is_paused=check_paused
            )

            if check_cancelled():
                job["status"] = "stopped"
                job["logs"].append("🛑 Pipeline stopped by user.")
                return

        job["logs"].append(f"✓ All {total_segments_count} speech chunks ready in cache!")

        # Step 3: Stitch Chapters
        if job.get("cancel_requested"):
            job["status"] = "stopped"
            return

        job["step"] = 3
        job["step_name"] = "Stitching Continuous Chapter Tracks"
        job["progress_pct"] = 78.0
        job["logs"].append("Step 3/4: Stitching chapters into audio tracks...")

        from novelcast.core.schema import PauseSettings
        pauses = PauseSettings(speaker_change_ms=req.speaker_change_ms, same_speaker_ms=req.same_speaker_ms)
        stitcher = AudioStitcher(pause_settings=pauses)

        stitched_files = []
        for idx, cs in enumerate(all_scripts):
            if job.get("cancel_requested"):
                job["status"] = "stopped"
                job["logs"].append("🛑 Pipeline stopped during stitching.")
                return

            audio_files = [engine.get_cache_path(s) for s in cs.segments]
            out_mp3 = os.path.join(chapters_dir, f"{cs.chapter_id}.mp3")
            stitcher.stitch_chapter(cs, audio_files, out_mp3)
            stitched_files.append(out_mp3)
            
            stitch_pct = ((idx + 1) / len(all_scripts)) * 12.0
            job["progress_pct"] = round(78.0 + stitch_pct, 1)
            job["logs"].append(f"✓ Stitched Chapter {idx + 1}/{len(all_scripts)}: {cs.title}")

        # Step 4: Package Master M4B
        if job.get("cancel_requested"):
            job["status"] = "stopped"
            return

        job["step"] = 4
        job["step_name"] = "Packaging Master M4B Audiobook"
        job["progress_pct"] = 92.0
        job["logs"].append("Step 4/4: Compiling master M4B with chapters and cover art...")

        book_title = req.title or pinfo.get("name", "NovelCast Audiobook")
        author_name = req.author or "Author"
        
        cover_art = None
        for cname in ["cover.jpg", "cover_vol2.jpg", "cover_vol3.jpg", "cover.png"]:
            cand = os.path.join(output_dir, cname)
            if os.path.exists(cand):
                cover_art = cand
                break

        out_m4b = os.path.join(output_dir, f"{book_title.replace(' ', '_')}.m4b")
        chapter_entries = []
        for sf in stitched_files:
            bname = os.path.splitext(os.path.basename(sf))[0]
            chapter_entries.append({
                "title": bname.replace("_", " ").title(),
                "audio_path": sf
            })

        packager = AudiobookPackager(bitrate=req.bitrate)
        packager.package_m4b(
            chapter_files=chapter_entries,
            output_m4b_path=out_m4b,
            book_title=book_title,
            author=author_name,
            cover_image_path=cover_art
        )

        size_mb = round(os.path.getsize(out_m4b) / (1024 * 1024), 2) if os.path.exists(out_m4b) else 0
        job["status"] = "completed"
        job["progress_pct"] = 100.0
        job["logs"].append(f"🎉 Production Complete! Master M4B: {out_m4b} ({size_mb} MB)")
        job["result"] = {
            "m4b_path": out_m4b,
            "size_mb": size_mb,
            "title": book_title,
            "download_url": f"/api/audio/download?path={out_m4b}"
        }

    except Exception as e:
        jobs_db[job_id]["status"] = "failed"
        jobs_db[job_id]["error"] = str(e)
        jobs_db[job_id]["logs"].append(f"❌ Error: {str(e)}")

@app.post("/api/pipeline/run")
def start_pipeline(req: RunPipelineRequest, background_tasks: BackgroundTasks):
    """Launches the complete 1-Click Audiobook Pipeline in the background with real-time job tracking."""
    job_id = f"job_{int(time.time())}_{req.project_id}"
    jobs_db[job_id] = {
        "job_id": job_id,
        "project_id": req.project_id,
        "status": "pending",
        "step": 1,
        "total_steps": 4,
        "step_name": "Initializing",
        "progress_pct": 0.0,
        "current_item": 0,
        "total_items": 0,
        "pause_requested": False,
        "cancel_requested": False,
        "logs": ["Job queued..."],
        "result": None,
        "error": None
    }
    background_tasks.add_task(_run_pipeline_worker, job_id, req)
    return {"job_id": job_id, "status": "started"}

@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    """Returns real-time progress status, percentages, and logs for a running job."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs_db[job_id]

@app.post("/api/jobs/{job_id}/pause")
def toggle_pause_job(job_id: str):
    """Pauses or resumes an active pipeline job."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs_db[job_id]
    job["pause_requested"] = not job.get("pause_requested", False)
    if job["pause_requested"]:
        job["status"] = "paused"
        job["logs"].append("⏸ Production paused by user.")
    else:
        job["status"] = "running"
        job["logs"].append("▶ Production resumed by user.")
    return {"success": True, "paused": job["pause_requested"], "status": job["status"]}

@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    """Cancels/stops an active pipeline job."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs_db[job_id]
    job["cancel_requested"] = True
    job["status"] = "stopped"
    job["logs"].append("🛑 Stop request received. Terminating job...")
    return {"success": True, "status": "stopped"}

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
            audio_results = engine.batch_synthesize(sub_script, vb)
            generated_chunks += sum(1 for a in audio_results if a and os.path.exists(a))

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
# 6. LLM & AI Script Director Endpoints
# ─────────────────────────────────────────────────────────────
@app.get("/api/llm/config")
def get_llm_config():
    """Returns current LLM global configuration and available providers."""
    mgr = LLMConfigManager()
    return mgr.config.model_dump()

@app.post("/api/llm/config")
def update_llm_config(req: LLMUpdateConfigRequest):
    """Updates active LLM provider or edits a specific provider configuration."""
    mgr = LLMConfigManager()
    if req.active_provider:
        mgr.set_active(req.active_provider, req.active_model)
    if req.provider_id:
        mgr.update_provider(
            provider_id=req.provider_id,
            api_base=req.api_base,
            api_key=req.api_key,
            default_model=req.default_model,
            models=req.models,
            temperature=req.temperature
        )
    return {"success": True, "config": mgr.config.model_dump()}

@app.post("/api/llm/test")
def test_llm_connection(req: LLTestRequest if 'LLTestRequest' in globals() else LLMTestRequest):
    """Tests connectivity to a local or cloud LLM endpoint."""
    mgr = LLMConfigManager()
    result = mgr.test_connection(req.provider_id, model_override=req.model)
    return result

@app.post("/api/scripts/{project_id}/{chapter_file}/ai-fix")
def direct_chapter_script_api(
    project_id: str,
    chapter_file: str,
    req: AIDirectRequest
):
    """
    Executes the AI Script Director on a single chapter script,
    re-attributing speakers, emotion instruct prompts, and audio tokens.
    """
    pinfo = resolve_project_dir(project_id)
    scripts_dir = pinfo["path"]
    fpath = os.path.join(scripts_dir, chapter_file)

    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail=f"Chapter script '{chapter_file}' not found")

    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "chapter_id" not in data:
        data["chapter_id"] = os.path.splitext(chapter_file)[0]
    script = ChapterScript(**data)

    vb = VoiceBank(voice_bank_dir="voice_bank")
    vb.auto_discover_voices()

    mgr = LLMConfigManager()
    prov_id = req.provider_id or mgr.config.active_provider
    model_ovr = req.model or mgr.config.active_model

    director = AIDirector(config_manager=mgr)
    director.set_provider(prov_id, model_override=model_ovr)

    # Collect candidate characters
    from novelcast.core.character_detector import CharacterDetector
    detector = CharacterDetector(voice_bank=vb)
    detected = detector.detect_from_scripts([script])
    candidate_chars = [
        {"name": c["name"], "gender": c["gender"], "description": c.get("sample_quote", "")}
        for c in detected
    ]

    updated_script, diffs = director.direct_chapter_script(
        script=script,
        candidate_characters=candidate_chars,
        vb=vb,
        batch_size=req.batch_size,
        refine_speakers=req.refine_speakers,
        refine_instructs=req.refine_instructs,
        insert_audio_tokens=req.insert_audio_tokens
    )

    # Save to disk
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(updated_script.model_dump(), f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "chapter_id": script.chapter_id,
        "title": script.title,
        "total_segments": len(script.segments),
        "total_fixed": len(diffs),
        "diffs": diffs,
        "segments": [s.model_dump() for s in updated_script.segments]
    }

@app.post("/api/scripts/{project_id}/ai-fix-all")
def direct_all_chapters_api(
    project_id: str,
    req: AIDirectRequest,
    background_tasks: BackgroundTasks
):
    """
    Launches a background job to direct all chapters in the project.
    """
    job_id = f"job_aifix_{int(time.time())}"
    tasks_status[job_id] = {
        "id": job_id,
        "type": "ai_fix_all",
        "project_id": project_id,
        "status": "running",
        "progress": 0,
        "step": "Starting AI Director for all chapters...",
        "logs": [f"[{time.strftime('%H:%M:%S')}] Initializing AI Director job for {project_id}..."],
        "total_fixed": 0
    }

    def run_job():
        try:
            pinfo = resolve_project_dir(project_id)
            scripts_dir = pinfo["path"]
            json_files = sorted([f for f in os.listdir(scripts_dir) if f.endswith(".json")])
            total_chaps = len(json_files)

            vb = VoiceBank(voice_bank_dir="voice_bank")
            vb.auto_discover_voices()
            mgr = LLMConfigManager()
            director = AIDirector(config_manager=mgr)
            director.set_provider(req.provider_id or mgr.config.active_provider, req.model or mgr.config.active_model)

            total_fixes = 0
            for idx, jf in enumerate(json_files):
                fpath = os.path.join(scripts_dir, jf)
                with open(fpath, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                if isinstance(data, dict) and "chapter_id" not in data:
                    data["chapter_id"] = os.path.splitext(jf)[0]
                script = ChapterScript(**data)

                tasks_status[job_id]["step"] = f"Directing Chapter {idx + 1}/{total_chaps}: {script.title}"
                tasks_status[job_id]["progress"] = round((idx / total_chaps) * 100, 1)

                updated_script, diffs = director.direct_chapter_script(
                    script=script,
                    vb=vb,
                    batch_size=req.batch_size,
                    refine_speakers=req.refine_speakers,
                    refine_instructs=req.refine_instructs,
                    insert_audio_tokens=req.insert_audio_tokens
                )
                total_fixes += len(diffs)

                with open(fpath, "w", encoding="utf-8") as fp:
                    json.dump(updated_script.model_dump(), fp, indent=2, ensure_ascii=False)

                tasks_status[job_id]["logs"].append(
                    f"[{time.strftime('%H:%M:%S')}] ✓ {jf}: Corrected {len(diffs)} lines"
                )

            tasks_status[job_id]["status"] = "completed"
            tasks_status[job_id]["progress"] = 100.0
            tasks_status[job_id]["step"] = f"Complete! Fixed {total_fixes} lines across {total_chaps} chapters."
            tasks_status[job_id]["total_fixed"] = total_fixes
        except Exception as e:
            tasks_status[job_id]["status"] = "failed"
            tasks_status[job_id]["step"] = f"Failed: {str(e)}"
            tasks_status[job_id]["logs"].append(f"[{time.strftime('%H:%M:%S')}] ✗ Error: {str(e)}")

    background_tasks.add_task(run_job)
    return {"success": True, "job_id": job_id}
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.exists(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "NovelCast Studio API is running. Web UI not found in novelcast/web."}
