import os
import io
import tempfile
import asyncio
import torch
import soundfile as sf
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
from contextlib import asynccontextmanager

app = FastAPI(title="Dual-GPU OmniVoice Server")

models = []
gpu_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global gpu_pool, models
    gpu_count = torch.cuda.device_count()
    print(f"\n========================================================")
    print(f"  DETECTED {gpu_count} NVIDIA GPU(s) ON WINDOWS")
    print(f"========================================================")
    
    from omnivoice import OmniVoice
    
    gpu_pool = asyncio.Queue()
    
    for i in range(gpu_count):
        gpu_name = torch.cuda.get_device_name(i)
        print(f"Loading OmniVoice onto GPU {i}: {gpu_name} (cuda:{i})...")
        model = OmniVoice.from_pretrained("k2-fsa/OmniVoice").to(f"cuda:{i}")
        models.append(model)
        await gpu_pool.put(i)  # Add GPU ID to available pool
        print(f"✓ GPU {i} Ready!")
        
    print(f"\n🚀 Dual-GPU Parallel Synthesis Pool Ready with {gpu_count} Workers!\n")
    yield

app.router.lifespan_context = lifespan

@app.post("/synthesize")
async def synthesize(
    text: str = Form(...),
    language: str = Form("Spanish"),
    instruct: Optional[str] = Form(None),
    guidance_scale: float = Form(2.8),
    speed: float = Form(1.0),
    ref_audio: UploadFile = File(...)
):
    temp_ref_path = None
    gpu_id = await gpu_pool.get()  # Acquire next available GPU (0 or 1)
    try:
        audio_bytes = await ref_audio.read()
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(audio_bytes)
            temp_ref_path = f.name

        gen_kwargs = {
            "text": text,
            "language": language,
            "ref_audio": temp_ref_path,
            "guidance_scale": guidance_scale
        }
        if instruct and instruct.strip():
            gen_kwargs["instruct"] = instruct.strip()
        if speed and speed != 1.0:
            gen_kwargs["speed"] = speed

        # Run synthesis in a thread pool on the acquired GPU
        model = models[gpu_id]
        loop = asyncio.get_event_loop()
        wav = await loop.run_in_executor(None, lambda: model.generate(**gen_kwargs))
        
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
        await gpu_pool.put(gpu_id)  # Release GPU back to pool
        if temp_ref_path and os.path.exists(temp_ref_path):
            os.remove(temp_ref_path)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9880)
