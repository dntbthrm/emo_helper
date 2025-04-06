import os
import subprocess
import telebot
from telebot import types
import requests
import uuid
import threading
import queue
from concurrent.futures import ThreadPoolExecutor

# кастомные функции
from audio.AudioProcessor import AudioProcessor
from text.TextProcessor import TextProcessor
import config
import utils as u

bot = telebot.TeleBot(config.tg_token)

task_queue = queue.Queue()
#
executor = ThreadPoolExecutor(max_workers=3)
#

@bot.message_handler(commands=['start', 'help'])
def send_info(message):
    user = message.from_user
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("/start"), types.KeyboardButton("/help"))

    if message.text == "/start":
        bot.send_message(message.chat.id, f"Здравствуйте, {user.first_name}. Я Биба", reply_markup=markup)
    elif message.text == "/help":
        bot.send_message(message.chat.id, "Сам себе помоги", reply_markup=markup)


def process_audio(message, file_id):
    try:
        AudioProcessor.make_tmp_dir("audio/tmp")

        file_info = bot.get_file(file_id)
        unique_id = str(uuid.uuid4())
        ogg_path = os.path.join("audio/tmp", f"audio_{unique_id}.ogg")
        wav_path = os.path.join("audio/tmp", f"audio_{unique_id}.wav")

        file = bot.download_file(file_info.file_path)
        with open(ogg_path, 'wb') as new_file:
            new_file.write(file)

        bot.send_message(message.chat.id, "🎙 Обрабатываю голосовое сообщение...")

        u.convert_to_wav(ogg_path, wav_path)

        answer = AudioProcessor.transcription(wav_path, unique_id)
        audio_emotion = AudioProcessor.emo_detection(wav_path)
        text_emotion = TextProcessor.emo_detection(answer)
        full_answer = answer + audio_emotion + " OOOO " + str(text_emotion)

        bot.send_message(message.chat.id, f"🗣 {full_answer}", parse_mode='Markdown')

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠ Ошибка: {str(e)}")

    finally:
        for path in [ogg_path, wav_path]:
            if os.path.exists(path):
                os.remove(path)


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    file_id = message.voice.file_id
    task_queue.put((message, file_id))
    bot.send_message(message.chat.id, "⏳ Голосовое сообщение поставлено в очередь на обработку.")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    emotion = TextProcessor.emo_detection(str(message))
    bot.send_message(message.chat.id, emotion)

def worker():
    while True:
        message, file_id = task_queue.get()
        executor.submit(process_audio, message, file_id)
        #process_audio(message, file_id)
        task_queue.task_done()


# Запуск обработчика в отдельном потоке
threading.Thread(target=worker, daemon=True).start()

bot.polling(none_stop=True, interval=0)
