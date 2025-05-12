import whisper
import torch
import os
from pydub import AudioSegment
import librosa
import numpy as np
import pandas as pd
import joblib
import threading
import requests

from models.audio_model.feature_extractor import extract_features

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
whisper_model = whisper.load_model("small", device=DEVICE)
whisper_lock = threading.Lock()


emotion_codes = {
    1: "neutral",
    2: "happy",
    3: "sad",
    4: "angry",
    5: "fearful",
    6: "disgust",
    7: "surprised"
}

def process_task(task, result_queue):
    audio_path, uid = task

    audio = AudioSegment.from_wav(audio_path)
    if len(audio) < 1000:
        result_queue.put((uid, "⚠ Ошибка: Аудио слишком короткое."))
        return

    chunks = [audio[i : i + 30 * 1000] for i in range(0, len(audio), 30 * 1000)]
    full_text = ""
    tmp_dir = "audio/tmp"

    for i, chunk in enumerate(chunks):
        chunk_path = os.path.join(tmp_dir, f"temp_chunk_{i}_{uid}.wav")
        chunk.export(chunk_path, format="wav")

        result = whisper_model.transcribe(chunk_path)
        full_text += result["text"] + " "

        os.remove(chunk_path)

    result_queue.put((uid, full_text.strip()))

class AudioProcessor:
    TMP_DIR = "audio/tmp"

    @staticmethod
    def make_tmp_dir(tmp_dir):
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

    @staticmethod
    def transcription(audio_path, uid):
        url = "http://127.0.0.1:8000/transcribe/"
        try:
            with open(audio_path, "rb") as f:
                files = {"file": f}
                response = requests.post(url, files=files)

            response.raise_for_status()

            data = response.json()

            full_text = data.get("transcription", "").strip()
            if not full_text:
                raise ValueError("Получен пустой текст распознавания.")

            print("Распознанный текст:", full_text)
            return full_text
        except requests.exceptions.RequestException as e:
            print("Ошибка при запросе к Whisper-серверу:", e)

        except ValueError as ve:
            print("Ошибка в содержимом ответа:", ve)

        except Exception as ex:
            print("Неожиданная ошибка:", ex)


    @staticmethod
    def extract_features(audio_path):
        y, sr = librosa.load(audio_path)
        # акустические признаки
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
        tonnetz = librosa.feature.tonnetz(y=y, sr=sr)
        zcr = librosa.feature.zero_crossing_rate(y)
        rms = librosa.feature.rms(y=y)

        features = np.hstack([
            np.mean(mfccs, axis=1), np.std(mfccs, axis=1),
            np.mean(chroma, axis=1), np.std(chroma, axis=1),
            np.mean(spectral_contrast, axis=1), np.std(spectral_contrast, axis=1),
            np.mean(tonnetz, axis=1), np.std(tonnetz, axis=1),
            np.mean(zcr), np.std(zcr),
            np.mean(rms), np.std(rms)
        ])

        feature_columns = [f"mfcc_{i}" for i in range(13)] + \
                  [f"mfcc_std_{i}" for i in range(13)] + \
                  [f"chroma_{i}" for i in range(12)] + \
                  [f"chroma_std_{i}" for i in range(12)] + \
                  [f"spectral_contrast_{i}" for i in range(7)] + \
                  [f"spectral_contrast_std_{i}" for i in range(7)] + \
                  [f"tonnetz_{i}" for i in range(6)] + \
                  [f"tonnetz_std_{i}" for i in range(6)] + \
                  ["zero_crossing_rate", "zero_crossing_rate_std", "rms", "rms_std"]
        df = pd.DataFrame([features], columns=feature_columns)
        df = df[['mfcc_std_1', 'tonnetz_3', 'rms_std', 'mfcc_2', 'mfcc_std_10', 'chroma_7', 'mfcc_7']]
        return df

    @staticmethod
    def emo_detection(audio_path):
        model = joblib.load('models/audio_model/audio_classifier_big.pkl')
        df = AudioProcessor.extract_features(audio_path)
        prediction = model.predict(df)[0]
        pred_value = emotion_codes.get(prediction)
        return pred_value
