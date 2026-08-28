import os
import io
import tempfile
import asyncio
import torch
import soundfile as sf
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from contextlib import asynccontextmanager

app = FastAPI(title="Dual-GPU OmniVoice Parallel Synthesis Server", version="1.1.0")

class GPUWorker:
    def __init__(self, gpu_id: int, model):
        self.gpu_id = gpu_id
        self.model = model
        self.lock = asyncio.Lock()

worker_pool: List[GPUWorker] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_pool
    gpu_count = torch.cuda.device_count()
    print(f"\n========================================================")
    print(f"  DETECTED {gpu_count} NVIDIA GPU(s) FOR OMNIVOICE")
    print(f"========================================================")
    
    from omnivoice import OmniVoice
    
    if gpu_count > 0:
        for i in range(gpu_count):
            gpu_name = torch.cuda.get_device_name(i)
            dev_str = f"cuda:{i}"
            print(f"Loading OmniVoice onto GPU {i}: {gpu_name} ({dev_str})...")
            model = OmniVoice.from_pretrained("k2-fsa/OmniVoice").to(dev_str)
            print(f"Pre-warming Whisper ASR pipeline on {dev_str}...")
            try:
                model.load_asr_model(device=dev_str)
            except Exception as e:
                print(f"Note: ASR pre-load on {dev_str}: {e}")
            worker_pool.append(GPUWorker(gpu_id=i, model=model))
            print(f"✓ GPU {i} Ready!")
    else:
        print("Loading OmniVoice on CPU...")
        model = OmniVoice.from_pretrained("k2-fsa/OmniVoice").to("cpu")
        try:
            model.load_asr_model(device="cpu")
        except Exception:
            pass
        worker_pool.append(GPUWorker(gpu_id=-1, model=model))
        print("✓ CPU Ready!")
        
    print(f"\n🚀 Parallel Synthesis Pool Ready with {len(worker_pool)} Worker(s)!\n")
    yield
    print("Shutting down OmniVoice workers...")

app.router.lifespan_context = lifespan

async def get_available_worker() -> GPUWorker:
    """Find an idle GPU worker or wait for the next available one."""
    while True:
        for worker in worker_pool:
            if not worker.lock.locked():
                return worker
        await asyncio.sleep(0.02)

@app.get("/health")
@app.get("/")
async def health_check():
    gpu_stats = []
    if torch.cuda.is_available():
        for w in worker_pool:
            if w.gpu_id >= 0:
                gpu_stats.append({
                    "gpu_id": w.gpu_id,
                    "name": torch.cuda.get_device_name(w.gpu_id),
                    "busy": w.lock.locked()
                })
    return {
        "status": "healthy",
        "service": "OmniVoice Multi-GPU Server",
        "num_workers": len(worker_pool),
        "gpus": gpu_stats
    }

@app.post("/synthesize")
async def synthesize(
    text: str = Form(...),
    language: str = Form("Spanish"),
    instruct: Optional[str] = Form(None),
    guidance_scale: float = Form(2.8),
    speed: float = Form(1.0),
    ref_audio: UploadFile = File(...)
):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    temp_ref_path = None
    worker = await get_available_worker()

    async with worker.lock:
        try:
            audio_bytes = await ref_audio.read()
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(audio_bytes)
                temp_ref_path = f.name

            gen_kwargs = {
                "text": text.strip(),
                "language": language,
                "ref_audio": temp_ref_path,
                "guidance_scale": float(guidance_scale)
            }
            if instruct and instruct.strip():
                gen_kwargs["instruct"] = instruct.strip()
            if speed and float(speed) != 1.0:
                gen_kwargs["speed"] = float(speed)

            def run_generation():
                with torch.no_grad():
                    if torch.cuda.is_available() and worker.gpu_id >= 0:
                        torch.cuda.set_device(worker.gpu_id)
                    return worker.model.generate(**gen_kwargs)

            loop = asyncio.get_event_loop()
            wav = await loop.run_in_executor(None, run_generation)

            wav_data = wav[0] if isinstance(wav, (list, tuple)) else wav
            if hasattr(wav_data, 'cpu'):
                wav_data = wav_data.cpu().numpy()

            out_io = io.BytesIO()
            sf.write(out_io, wav_data, 24000, format='WAV')
            out_io.seek(0)
            return Response(content=out_io.read(), media_type="audio/wav")

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(content=str(e), status_code=500)
        finally:
            if temp_ref_path and os.path.exists(temp_ref_path):
                try:
                    os.remove(temp_ref_path)
                except Exception:
                    pass

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9880)
