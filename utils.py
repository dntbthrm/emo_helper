import subprocess
import requests
def convert_to_wav(input_ogg, output_wav):
    command = [
        "ffmpeg", "-y", "-i", input_ogg,
        "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", output_wav
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"Ошибка конвертации: {result.stderr.decode()}")

emodzi_dict = {
    'anger': '😡',
    'disgust' : '🤮',
    'fear': '😱',
    'joy': '😁',
    'sadness': '😢',
    'surprise': '🤩',
    'neutral': '😐'
}

emodzi_dict_audio = {
    'angry': '😡',
    'disgust' : '🤮',
    'fearful': '😱',
    'happy': '😁',
    'sad': '😢',
    'surprised': '🤩',
    'neutral': '😐'
}

audio_to_text = {
    'angry': 'anger',
    'disgust': 'disgust',
    'fearful': 'fear',
    'happy': 'joy',
    'sad': 'sadness',
    'surprised': 'surprise',
    'neutral': 'neutral'
}

audio_russian = {
    'angry': 'злость',
    'disgust': 'отвращение',
    'fearful': 'страх',
    'happy': 'радость',
    'sad': 'грусть',
    'surprised': 'удивление',
    'neutral': 'нейтральная'
}

text_russian = {
    'anger': 'злость',
    'disgust' : 'отвращение',
    'fear': 'страх',
    'joy': 'радость',
    'sadness': 'грусть',
    'surprise': 'удивление',
    'neutral': 'нейтральная'
}

dict_emo = {
    'anger': 1,
    'disgust' : 2,
    'fear': 3,
    'happiness': 4,
    'sadness': 5,
    'enthusiasm': 6,
    'neutral': 7
}


import sqlite3

def init_db():
    conn = sqlite3.connect('bot_state.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_activity (
            chat_id INTEGER PRIMARY KEY,
            is_active BOOLEAN
        )
    ''')
    conn.commit()
    conn.close()


def bot_activate(chat_id):
    conn = sqlite3.connect('bot_state.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO bot_activity (chat_id, is_active) 
        VALUES (?, ?)
        ON CONFLICT(chat_id) 
        DO UPDATE SET is_active = ?
    ''', (chat_id, True, True))
    conn.commit()
    conn.close()


def bot_deactivate(chat_id):
    conn = sqlite3.connect('bot_state.db')
    c = conn.cursor()

    c.execute('''
        INSERT INTO bot_activity (chat_id, is_active) 
        VALUES (?, ?)
        ON CONFLICT(chat_id) 
        DO UPDATE SET is_active = ?
    ''', (chat_id, False, False))
    conn.commit()
    conn.close()


def check_bot_state(chat_id):
    conn = sqlite3.connect('bot_state.db')
    c = conn.cursor()
    c.execute('SELECT is_active FROM bot_activity WHERE chat_id = ?', (chat_id,))
    result = c.fetchone()
    conn.close()
    if result is None:
        return False
    return result[0] == 1

def define_emotion(audio_emotion, text_emotion, message_text):
    if audio_emotion == "none":
        return f"Выявленная в сообщении эмоция – {text_russian.get(text_emotion)}"
    is_equal = audio_to_text.get(audio_emotion) == text_emotion
    if is_equal or (text_emotion == "neutral" and audio_emotion != 'neutral'):
        return f"Выявленная в сообщении эмоция – {audio_russian.get(audio_emotion)}.\nРасшифровка:\n{message_text}"
    return f"Выявлено расхождение между эмоциями голоса ({audio_russian.get(audio_emotion)}) и текста ({text_russian.get(text_emotion)}).\nРасшифровка:\n{message_text}"

import re
def clean_text(text):
    # - markdown (*, _, ^, >, ` и т.п.)
    text = re.sub(r'[*_`^>]', '', text)

    # - упоминания типа @username и спецсимволы
    text = re.sub(r'@\w+', '', text)

    # - ссылки
    text = re.sub(r'http\S+|www\.\S+', '', text)

    # - всякий мусор вроде "^(комментарий)", "^^", "(что-то в скобках)"
    text = re.sub(r'\(\s*[^)]*\s*\)', '', text)  # обычные скобки
    text = re.sub(r'\[\s*[^]]*\s*\]', '', text)  # квадратные скобки
    text = re.sub(r'\{[^}]*\}', '', text)  # фигурные скобки

    # - повторяющиеся пробелы
    text = re.sub(r'\s+', ' ', text)

    # - лидирующие/замыкающие пробелы
    return text.strip()
