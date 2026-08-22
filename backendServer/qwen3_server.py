import os
import io
import argparse
import tempfile
import asyncio
import torch
import soundfile as sf
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
import uvicorn

# =====================================================================
# Compatibility Patches for transformers & torchaudio on Windows
# =====================================================================
try:
    import transformers
    def _safe_decorator(func=None, *args, **kwargs):
        if func is not None and callable(func):
            return func
        return lambda f: f

    if hasattr(transformers, "modeling_utils"):
        transformers.modeling_utils.check_model_inputs = _safe_decorator
    if hasattr(transformers, "utils") and hasattr(transformers.utils, "generic"):
        transformers.utils.generic.check_model_inputs = _safe_decorator

    try:
        from qwen_tts.core.models.modeling_qwen3_tts import Qwen3TTSTalkerConfig
        if not hasattr(Qwen3TTSTalkerConfig, "pad_token_id"):
            setattr(Qwen3TTSTalkerConfig, "pad_token_id", None)
    except Exception:
        pass
except Exception:
    pass

try:
    import torchaudio
    torchaudio.set_audio_backend("soundfile")
except Exception:
    pass
# =====================================================================

from qwen_tts import Qwen3TTSModel

app = FastAPI(title="Qwen3-TTS Multi-GPU Synthesis Server", version="1.0.0")

class GPUWorker:
    def __init__(self, gpu_id: int, model: Qwen3TTSModel):
        self.gpu_id = gpu_id
        self.model = model
        self.lock = asyncio.Lock()

worker_pool: List[GPUWorker] = []

def load_qwen3_models(model_name: str = "Qwen/Qwen3-TTS-12Hz-1.7B-Base", target_gpus: Optional[List[int]] = None):
    global worker_pool
    num_gpus = torch.cuda.device_count()
    if num_gpus == 0:
        device_ids = [-1]
    elif target_gpus:
        device_ids = target_gpus
    else:
        device_ids = list(range(num_gpus))

    print(f"=======================================================")
    print(f" Initializing Qwen3-TTS on {len(device_ids)} Device(s): {device_ids}")
    print(f"=======================================================")

    for dev_id in device_ids:
        device_str = f"cuda:{dev_id}" if dev_id >= 0 else "cpu"
        dtype = torch.bfloat16 if dev_id >= 0 else torch.float32
        print(f"-> Loading Qwen3TTSModel on '{device_str}' ({dtype})...")

        model = Qwen3TTSModel.from_pretrained(
            model_name,
            device_map=device_str if dev_id >= 0 else None,
            dtype=dtype
        )

        worker = GPUWorker(gpu_id=dev_id, model=model)
        worker_pool.append(worker)
        print(f"   [OK] GPU {dev_id} loaded successfully!")

    print(f"\nAll {len(worker_pool)} GPU worker(s) ready for parallel synthesis!\n")

async def get_available_worker() -> GPUWorker:
    """Find an idle GPU worker or wait for the next available one."""
    while True:
        for worker in worker_pool:
            if not worker.lock.locked():
                return worker
        await asyncio.sleep(0.02)

@app.get("/health")
def health_check():
    gpu_stats = []
    if torch.cuda.is_available():
        for w in worker_pool:
            if w.gpu_id >= 0:
                gpu_stats.append({
                    "gpu_id": w.gpu_id,
                    "name": torch.cuda.get_device_name(w.gpu_id),
                    "vram_allocated_mb": round(torch.cuda.memory_allocated(w.gpu_id) / (1024 * 1024), 2)
                })

    return {
        "status": "online",
        "engine": "Qwen3-TTS Multi-GPU",
        "num_workers": len(worker_pool),
        "gpus": gpu_stats
    }

@app.post("/synthesize")
async def synthesize(
    text: str = Form(...),
    language: str = Form("Spanish"),
    speed: float = Form(1.0),
    speaker: str = Form(""),
    instruct: str = Form(""),
    ref_text: Optional[str] = Form(None),
    x_vector_only_mode: bool = Form(True),
    ref_audio: Optional[UploadFile] = File(None)
):
    """
    Synthesize audio across the GPU pool using Qwen3-TTS with zero-shot voice cloning or custom voice.
    """
    if not worker_pool:
        raise HTTPException(status_code=500, detail="No GPU workers are initialized.")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    ref_wav_path = None
    temp_file = None

    if ref_audio:
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        content = await ref_audio.read()
        temp_file.write(content)
        temp_file.flush()
        temp_file.close()
        ref_wav_path = temp_file.name

    worker = await get_available_worker()

    async with worker.lock:
        try:
            loop = asyncio.get_event_loop()

            def run_inference():
                with torch.no_grad():
                    # If reference audio is provided -> Voice Cloning
                    if ref_wav_path and os.path.exists(ref_wav_path):
                        kwargs = {
                            "text": text.strip(),
                            "language": language,
                            "ref_audio": ref_wav_path,
                            "x_vector_only_mode": True if not ref_text else False
                        }
                        if ref_text and ref_text.strip():
                            kwargs["ref_text"] = ref_text.strip()
                        if instruct and instruct.strip():
                            kwargs["instruct"] = instruct.strip()

                        if hasattr(worker.model, "generate_voice_clone"):
                            wavs, sr = worker.model.generate_voice_clone(**kwargs)
                        else:
                            wavs, sr = worker.model.generate(**kwargs)
                    else:
                        # Otherwise -> Custom Voice
                        kwargs = {
                            "text": text.strip(),
                            "language": language
                        }
                        if speaker:
                            kwargs["speaker"] = speaker
                        if instruct and instruct.strip():
                            kwargs["instruct"] = instruct.strip()

                        if hasattr(worker.model, "generate_custom_voice"):
                            wavs, sr = worker.model.generate_custom_voice(**kwargs)
                        else:
                            wavs, sr = worker.model.generate(**kwargs)

                    audio_arr = wavs[0] if isinstance(wavs, (list, tuple)) else wavs
                    return audio_arr, sr

            wav_data, sr = await loop.run_in_executor(None, run_inference)

            # Convert numpy/tensor to WAV bytes
            if hasattr(wav_data, "cpu"):
                wav_data = wav_data.cpu().numpy()

            buf = io.BytesIO()
            sf.write(buf, wav_data, sr, format="WAV")
            buf.seek(0)

            return Response(content=buf.read(), media_type="audio/wav")

        except Exception as e:
            print(f"[Error on GPU {worker.gpu_id}]: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        finally:
            if temp_file and os.path.exists(temp_file.name):
                try: os.remove(temp_file.name)
                except Exception: pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Qwen3-TTS Multi-GPU FastAPI Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host IP to bind to")
    parser.add_argument("--port", type=int, default=9881, help="Port to listen on")
    parser.add_argument("--model", type=str, default="Qwen/Qwen3-TTS-12Hz-1.7B-Base", help="HuggingFace model name or local path")
    parser.add_argument("--gpus", nargs="+", type=int, default=None, help="Explicit list of GPU IDs to use (e.g. --gpus 0 1). Default: all available GPUs")
    args = parser.parse_args()

    load_qwen3_models(model_name=args.model, target_gpus=args.gpus)

    print(f"Starting Qwen3-TTS Multi-GPU Server on http://{args.host}:{args.port}...")
    uvicorn.run(app, host=args.host, port=args.port)
