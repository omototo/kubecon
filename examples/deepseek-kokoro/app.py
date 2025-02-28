import os
import io
import base64
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import torch
import torchaudio
from kokoro import Kokoro, KPipeline
from pydantic import BaseModel

app = FastAPI()

# Get the model ID from environment variable or use default
MODEL_ID = os.environ.get("MODEL_ID", "hexgrad/Kokoro-82M")
# Get the language code from environment variable or use default (American English)
LANG_CODE = os.environ.get("LANG_CODE", "a")
# Check if GPU is available
USE_GPU = torch.cuda.is_available()

# Global variables for model and pipeline
model = None
pipeline = None

class TTSRequest(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 1.0

@app.on_event("startup")
async def load_model():
    global model, pipeline
    
    device = "cuda" if USE_GPU else "cpu"
    print(f"Loading model {MODEL_ID} on {device}...")
    
    try:
        # Try to use the pipeline approach first (recommended)
        pipeline = KPipeline(lang_code=LANG_CODE)
        print(f"Pipeline loaded successfully on {device}!")
    except Exception as e:
        print(f"Failed to load pipeline: {str(e)}")
        print("Falling back to direct model loading...")
        # Fall back to direct model loading
        model = Kokoro.from_pretrained(MODEL_ID)
        if USE_GPU:
            model = model.to("cuda")
        print(f"Model loaded successfully on {device}!")

@app.get('/health')
async def health():
    return {
        "status": "healthy",
        "model_id": MODEL_ID,
        "lang_code": LANG_CODE,
        "gpu_available": USE_GPU
    }

@app.post('/api/tts')
async def text_to_speech(request: TTSRequest):
    try:
        # Generate speech
        if pipeline is not None:
            # Use pipeline approach
            audio_segments = []
            for _, _, audio in pipeline(request.text, voice=request.voice, speed=request.speed, split_pattern=r'\n+'):
                audio_segments.append(audio)
            
            # Concatenate audio segments if multiple
            if len(audio_segments) > 1:
                audio = torch.cat(audio_segments, dim=0)
            else:
                audio = audio_segments[0]
        else:
            # Use direct model approach
            with torch.no_grad():
                audio = model.generate(
                    text=request.text,
                    speaker_id=0,
                    speed=request.speed
                )
        
        # Convert to WAV format
        buffer = io.BytesIO()
        torchaudio.save(buffer, audio.unsqueeze(0), 24000, format="wav")
        buffer.seek(0)
        
        return StreamingResponse(buffer, media_type="audio/wav")
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/voices')
async def list_voices():
    # Return a list of available voices
    voices = [
        {"id": "af_heart", "name": "American Female Heart", "language": "English (US)"},
        {"id": "am_dream", "name": "American Male Dream", "language": "English (US)"},
        {"id": "bf_sky", "name": "British Female Sky", "language": "English (UK)"},
        {"id": "bm_nova", "name": "British Male Nova", "language": "English (UK)"}
    ]
    return {"voices": voices}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080) 