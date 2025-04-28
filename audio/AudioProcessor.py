import whisper
import torch
import os
from pydub import AudioSegment
import librosa
import numpy as np
import pandas as pd
import joblib

from models.audio_model.feature_extractor import extract_features

emotion_codes = {
    1: "neutral",
    2: "happy",
    3: "sad",
    4: "angry",
    5: "fearful",
    6: "disgust",
    7: "surprised"
}

class AudioProcessor:
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
            chunk_path = os.path.join(AudioProcessor.TMP_DIR, f"temp_chunk_{i}_{uid}.wav")
            chunk.export(chunk_path, format="wav")

            result = model.transcribe(chunk_path)
            full_text += result["text"] + " "

            os.remove(chunk_path)

        return full_text.strip()



    @staticmethod
    def extract_features(audio_path):
        y, sr = librosa.load(audio_path, sr=22050)
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
        return df

    @staticmethod
    def emo_detection(audio_path):
        model = joblib.load('models/audio_model/audio_classifier.pkl')
        df = AudioProcessor.extract_features(audio_path)
        prediction = model.predict(df)[0]
        pred_value = emotion_codes.get(prediction)
        return pred_value
