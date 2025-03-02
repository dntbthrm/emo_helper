import os
import subprocess
import telebot
from telebot import types
import requests
from audio import AudioProccessor
import config

bot = telebot.TeleBot(config.tg_token)

@bot.message_handler(commands=['start', 'help'])
def send_info(message):
    user = message.from_user
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("/start")
    btn2 = types.KeyboardButton("/help")
    markup.add(btn1, btn2)
    if message.text == "/start":
        bot.send_message(message.chat.id, f"Здравствуйте, {user.first_name}. Я Биба",
                     reply_markup=markup)
    if message.text == "/help":
        bot.send_message(message.chat.id,
                     "Сам себе помоги",
                     reply_markup=markup)


def convert_to_wav(input_ogg, output_wav):
    """Конвертирует OGG (Opus) в WAV (PCM 16-bit)"""
    command = [
        "ffmpeg", "-y", "-i", input_ogg,
        "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", output_wav
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"Ошибка конвертации: {result.stderr.decode()}")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    """Обработка голосового сообщения"""
    try:
        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)

        # Скачать голосовое сообщение (OGG)
        ogg_path = "audio.ogg"
        wav_path = "audio.wav"

        file = bot.download_file(file_info.file_path)
        with open(ogg_path, 'wb') as new_file:
            new_file.write(file)

        bot.send_message(message.chat.id, "🎙 Обрабатываю голосовое сообщение...")

        # Конвертация в WAV
        convert_to_wav(ogg_path, wav_path)

        # Расшифровка голоса
        answer = AudioProccessor.transcription(wav_path)

        bot.send_message(message.chat.id, f"🗣 {answer}", parse_mode='Markdown')

        # Удаление временных файлов
        os.remove(ogg_path)
        os.remove(wav_path)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠ Ошибка: {str(e)}")

bot.polling(none_stop=True, interval=0)
