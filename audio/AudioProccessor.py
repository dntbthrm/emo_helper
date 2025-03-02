import vosk as v
import os
import wave
import json

path_to_vosk = "/home/boss/diplom/vosk-model-ru-0.22"

def transcription(audio_file):
    if not os.path.exists(path_to_vosk):
        raise FileNotFoundError("Модель не найдена")
    v_model = v.Model(path_to_vosk)

    with wave.open(audio_file, "rb") as wf:
        rec = v.KaldiRecognizer(v_model, wf.getframerate())

        text = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text.append(result.get("text", ""))

        final_result = json.loads(rec.FinalResult())
        text.append(final_result.get("text", ""))

    return " ".join(text).strip() or "Не удалось распознать речь."