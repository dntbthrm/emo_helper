from fastapi import FastAPI, File, UploadFile
from faster_whisper import WhisperModel
import tempfile
import torch

app = FastAPI()
if torch.cuda.is_available():
    print("CUDA доступна. Модель 'medium' с GPU.")
    model = WhisperModel("medium", device="cuda", compute_type="int8")
else:
    print("CUDA недоступна. Модель 'base' на CPU.")
    model = WhisperModel("base", device="cpu", compute_type="int8")

@app.post("/transcribe/")
async def transcribe(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_audio.write(await file.read())
        segments, _ = model.transcribe(temp_audio.name)

    result = ""
    for segment in segments:
        result += segment.text + " "
    return {"transcription": result.strip()}
