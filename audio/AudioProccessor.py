import whisper
import torch
import os
from pydub import AudioSegment

class AudioProccessor:
    TMP_DIR = "audio/tmp"

    @staticmethod
    def make_tmp_dir(tmp_dir):
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

    @staticmethod
    def transcription(audio_path, uid):
        torch.cuda.empty_cache()
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model("small", device=dev)

        audio = AudioSegment.from_wav(audio_path)
        if len(audio) < 1000:  # Если аудио < 1 сек, отбрасываем
            return "⚠ Ошибка: Аудио слишком короткое."

        # дробление аудио на куски по 30 с
        chunks = [audio[i : i + 30 * 1000] for i in range(0, len(audio), 30 * 1000)]
        full_text = ""

        for i, chunk in enumerate(chunks):
            chunk_path = os.path.join(AudioProccessor.TMP_DIR, f"temp_chunk_{i}_{uid}.wav")
            chunk.export(chunk_path, format="wav")

            result = model.transcribe(chunk_path)
            full_text += result["text"] + " "

            os.remove(chunk_path)

        return full_text.strip()

    @staticmethod
    def emo_detection(audio_path):
        return 0
