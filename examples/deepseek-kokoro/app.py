import os
import io
import base64
from flask import Flask, request, jsonify
import torch
import torchaudio
from kokoro import Kokoro, KPipeline

app = Flask(__name__)

# Get the model ID from environment variable or use default
MODEL_ID = os.environ.get("MODEL_ID", "hexgrad/Kokoro-82M")
# Get the language code from environment variable or use default (American English)
LANG_CODE = os.environ.get("LANG_CODE", "a")
# Check if GPU is available
USE_GPU = torch.cuda.is_available()

# Global variables for model and pipeline
model = None
pipeline = None

@app.before_first_request
def load_model():
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

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "model_id": MODEL_ID,
        "lang_code": LANG_CODE,
        "gpu_available": USE_GPU
    })

@app.route('/tts', methods=['POST'])
def text_to_speech():
    try:
        data = request.json
        if not data or 'text' not in data:
            return jsonify({"error": "Missing 'text' field in request"}), 400
        
        text = data['text']
        
        # Optional parameters
        speaker_id = data.get('speaker_id', 0)
        speed = float(data.get('speed', 1.0))
        voice = data.get('voice', 'af_heart')  # Default voice
        
        # Generate speech
        if pipeline is not None:
            # Use pipeline approach
            audio_segments = []
            for _, _, audio in pipeline(text, voice=voice, speed=speed, split_pattern=r'\n+'):
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
                    text=text,
                    speaker_id=speaker_id,
                    speed=speed
                )
        
        # Convert to WAV format
        buffer = io.BytesIO()
        torchaudio.save(buffer, audio.unsqueeze(0), 24000, format="wav")
        buffer.seek(0)
        
        # Encode as base64
        audio_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return jsonify({
            "audio": audio_base64,
            "format": "wav",
            "sample_rate": 24000
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/voices', methods=['GET'])
def list_voices():
    # Return a list of available voices
    voices = [
        {"id": "af_heart", "name": "American Female Heart", "language": "English (US)"},
        {"id": "am_dream", "name": "American Male Dream", "language": "English (US)"},
        {"id": "bf_sky", "name": "British Female Sky", "language": "English (UK)"},
        {"id": "bm_nova", "name": "British Male Nova", "language": "English (UK)"}
    ]
    return jsonify({"voices": voices})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080) 