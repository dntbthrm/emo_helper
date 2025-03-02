import whisper
import torch
import os
from pydub import AudioSegment

torch.cuda.empty_cache()
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("small", device=DEVICE)  # Можно выбрать "medium" для скорости

class AudioProccessor:
    @staticmethod
    def transcription(audio_path):
        audio = AudioSegment.from_wav(audio_path)

        # Если аудио длинное, разбиваем на куски по 30 сек
        chunks = [audio[i : i + 30 * 1000] for i in range(0, len(audio), 30 * 1000)]
        full_text = ""

        for i, chunk in enumerate(chunks):
            chunk_path = f"temp_chunk_{i}.wav"
            chunk.export(chunk_path, format="wav")

            result = model.transcribe(chunk_path)
            full_text += result["text"] + " "

            os.remove(chunk_path)

        return full_text.strip()
