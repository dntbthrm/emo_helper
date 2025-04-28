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

def send_reaction(bot_token, chat_id, message_id, emoji):
    url = f"https://api.telegram.org/bot{bot_token}/sendReaction"
    data = {
        'chat_id': chat_id,
        'message_id': message_id,
        'reaction': emoji
    }
    response = requests.post(url, json=data)
    return response.json()