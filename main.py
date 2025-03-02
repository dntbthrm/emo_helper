import os
import subprocess
import telebot
from telebot import types
import requests
import uuid
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from audio import AudioProccessor
import config

bot = telebot.TeleBot(config.tg_token)

task_queue = queue.Queue()
executor = ThreadPoolExecutor(max_workers=3)


@bot.message_handler(commands=['start', 'help'])
def send_info(message):
    user = message.from_user
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("/start")
    btn2 = types.KeyboardButton("/help")
    markup.add(btn1, btn2)
    if message.text == "/start":
        bot.send_message(message.chat.id, f"Здравствуйте, {user.first_name}. Я Биба", reply_markup=markup)
    if message.text == "/help":
        bot.send_message(message.chat.id, "Сам себе помоги", reply_markup=markup)

def convert_to_wav(input_ogg, output_wav):
    command = [
        "ffmpeg", "-y", "-i", input_ogg,
        "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", output_wav
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"Ошибка конвертации: {result.stderr.decode()}")

def process_audio(message, file_id):
    try:
        file_info = bot.get_file(file_id)
        unique_id = str(uuid.uuid4())
        ogg_path = f"audio_{unique_id}.ogg"
        wav_path = f"audio_{unique_id}.wav"

        file = bot.download_file(file_info.file_path)
        with open(ogg_path, 'wb') as new_file:
            new_file.write(file)

        bot.send_message(message.chat.id, "🎙 Обрабатываю голосовое сообщение...")

        convert_to_wav(ogg_path, wav_path)

        answer = AudioProccessor.AudioProccessor.transcription(wav_path)

        bot.send_message(message.chat.id, f"🗣 {answer}", parse_mode='Markdown')

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠ Ошибка: {str(e)}")

    finally:
        if os.path.exists(ogg_path):
            os.remove(ogg_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    file_id = message.voice.file_id
    task_queue.put((message, file_id))
    bot.send_message(message.chat.id, "⏳ Голосовое сообщение поставлено в очередь на обработку.")

def worker():
    while True:
        message, file_id = task_queue.get()
        executor.submit(process_audio, message, file_id)
        task_queue.task_done()

threading.Thread(target=worker, daemon=True).start()

bot.polling(none_stop=True, interval=0)
