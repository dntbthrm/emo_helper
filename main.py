import os
import subprocess
import telebot
from telebot import types
import requests
import uuid
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
import logging
import time
import concurrent.futures
import uvicorn
from whisper_server import app

import aiogram as aio
# кастомные функции
from audio.AudioProcessor import AudioProcessor
from text.TextProcessor import TextProcessor
import config
import utils as u

# логгирование
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_api():
    uvicorn.run(app, host="127.0.0.1", port=8000)

bot = telebot.TeleBot(config.tg_token)

task_queue = queue.Queue()
#
executor = ThreadPoolExecutor(max_workers=3)
#
u.init_db()


def group_buttons():
    markup = types.InlineKeyboardMarkup(row_width=2)
    button_start = types.InlineKeyboardButton("Инфо", callback_data="start")
    button_help = types.InlineKeyboardButton("Помощь", callback_data="help")
    start_group = types.InlineKeyboardButton("Начать анализ", callback_data="start_analyze")
    stop_group = types.InlineKeyboardButton("Остановить анализ", callback_data="stop_analyze")

    markup.add(button_start, button_help)
    markup.add(start_group, stop_group)

    return markup

def private_buttons():
    markup = types.InlineKeyboardMarkup()
    button_start = types.InlineKeyboardButton("Инфо", callback_data="start")
    button_help = types.InlineKeyboardButton("Помощь", callback_data="help")

    markup.add(button_start, button_help)

    return markup

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    #user = call.message.from_user
    if call.data == "start":
        bot.answer_callback_query(call.id, text="Инфо")
        bot.send_message(call.message.chat.id, "Бот EmoAnalyst распознает эмоции в голосовых и текстовых сообщениях.\nБота можно добавить в чат.")
    elif call.data == "help":
        bot.answer_callback_query(call.id, text="Помощь")
        bot.send_message(call.message.chat.id, "Использование Бота:\n1. Отправьте или перешлите сообщение в диалог с ботом\n"
                                               "2. Для включения Бота в групповом чате вызовите /start и воспользуйтесь появившимися кнопками.\n"
                                               "Бот принимает только АУДИО и ТЕКСТ!")
    elif call.data == "start_analyze":
        bot.answer_callback_query(call.id, text="Начинается анализ...")
        start_analyze(call.message)
    elif call.data == "stop_analyze":
        bot.answer_callback_query(call.id, text="Анализ остановлен.")
        stop_analyze(call.message)

@bot.message_handler(commands=['remove_keyboard'])
def remove_keyboard(message):
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Клавиатура удалена", reply_markup=markup)

@bot.message_handler(content_types=['photo', 'video', 'video_note'])
def send_info(message):
    if message.chat.type == 'private':
        bot.send_message(message.chat.id, "Бот пока умеет распознавать только аудио и текст\n:(")

@bot.message_handler(commands=['start'])
def send_info(message):
    user = message.from_user
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("/start"))
    markup_inline = group_buttons() if message.chat.type != 'private' else private_buttons()
    if message.text == "/start":
        bot.send_message(message.chat.id, f"Здравствуйте, {user.first_name}. Это бот для распознавания эмоций.", reply_markup=markup_inline)



@bot.message_handler(commands=['start_analyze'])
def start_analyze(message):
    if message.chat.type != 'private':
        chat_id = message.chat.id
        if u.check_bot_state(chat_id):
            bot.send_message(message.chat.id, "Распознавание эмоций уже включено")
        else:
            u.bot_activate(chat_id)
            bot.send_message(message.chat.id, "Начинается распознавание эмоций...\nЖду ваших сообщений...")


@bot.message_handler(commands=['stop_analyze'])
def stop_analyze(message):
    if message.chat.type != 'private':
        chat_id = message.chat.id
        if not u.check_bot_state(chat_id):
            bot.send_message(message.chat.id, "Распознавание эмоций уже выключено")
        else:
            u.bot_deactivate(chat_id)
            bot.send_message(message.chat.id, "Распознавание эмоций отключено")


#case_id 0 - private; 1 - group
def process_audio(message, file_id):
    start_time = time.time()
    try:
        username = u.mask_name(message.from_user.first_name or "Unknown")
        logger.info(f"->>> Начата обработка аудио: chat_id={message.chat.id}, user={username}")

        AudioProcessor.make_tmp_dir("audio/tmp")

        file_info = bot.get_file(file_id)
        unique_id = str(uuid.uuid4())
        ogg_path = os.path.join("audio/tmp", f"audio_{unique_id}.ogg")
        wav_path = os.path.join("audio/tmp", f"audio_{unique_id}.wav")

        file = bot.download_file(file_info.file_path)
        with open(ogg_path, 'wb') as new_file:
            new_file.write(file)

        bot.send_message(message.chat.id, "🎙 Обрабатываю голосовое сообщение...")

        # 1. Конвертация
        convert_start = time.time()
        u.convert_to_wav(ogg_path, wav_path)
        convert_duration = time.time() - convert_start
        logger.info(f" --- Конвертация заняла {convert_duration:.2f} сек ---")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_transcribe = executor.submit(u.timed_call, AudioProcessor.transcription, wav_path, unique_id)
            future_audio_emotion = executor.submit(u.timed_call, AudioProcessor.emo_detection, wav_path)

            (answer, transcribe_duration) = future_transcribe.result()
            (audio_emotion, audio_duration) = future_audio_emotion.result()

        logger.info(f" --- Распознавание речи заняло {transcribe_duration:.2f} сек ---")
        logger.info(f" --- Эмоция по аудио заняла {audio_duration:.2f} сек ---")

        text_start = time.time()
        text_emotion = TextProcessor.emo_detection(answer)
        text_duration = time.time() - text_start
        logger.info(f" --- Эмоция по тексту заняла {text_duration:.2f} сек ---")

        define_start = time.time()
        full_answer = u.define_emotion(audio_emotion, text_emotion, answer)
        define_duration = time.time() - define_start
        logger.info(f" --- Объединение эмоций заняло {define_duration:.2f} сек ---")

        bot.send_message(message.chat.id, f"🗣 {full_answer}", parse_mode='Markdown')

        total_duration = time.time() - start_time
        logger.info(f"<<<- Аудио обработано за {total_duration:.2f} сек: chat_id={message.chat.id}, user={username}")

    except Exception as e:
        logger.exception(f"!!!!!!!!!!!!! Ошибка при обработке аудио: {e}")
        bot.send_message(message.chat.id, f"⚠ Ошибка: {str(e)}")

    finally:
        for path in [ogg_path, wav_path]:
            if os.path.exists(path):
                os.remove(path)


def process_audio_group(message, file_id):
    start_time = time.time()
    try:
        logging.info(f"->>> [GROUP] Начата обработка голосового. chat_id={message.chat.id}, message_id={message.message_id}")

        AudioProcessor.make_tmp_dir("audio/tmp")

        file_info = bot.get_file(file_id)
        unique_id = str(uuid.uuid4())
        ogg_path = os.path.join("audio/tmp", f"audio_{unique_id}.ogg")
        wav_path = os.path.join("audio/tmp", f"audio_{unique_id}.wav")

        file = bot.download_file(file_info.file_path)
        with open(ogg_path, 'wb') as new_file:
            new_file.write(file)

        u.convert_to_wav(ogg_path, wav_path)

        answer = AudioProcessor.transcription(wav_path, unique_id)
        audio_emotion = AudioProcessor.emo_detection(wav_path)
        emodzi = u.emodzi_dict_audio.get(audio_emotion)
        reaction = [types.ReactionTypeEmoji(emoji=emodzi)]
        bot.set_message_reaction(message.chat.id, message.message_id, reaction=reaction)

        duration = time.time() - start_time
        logging.info(f"<<<- [GROUP] Обработка завершена. chat_id={message.chat.id}, duration={duration:.2f} сек")

    except Exception as e:
        logging.exception(f" !!!!! [GROUP] Ошибка обработки голосового. chat_id={message.chat.id}, error={e}")
        bot.send_message(message.chat.id, f"⚠ Ошибка: {str(e)}")

    finally:
        for path in [ogg_path, wav_path]:
            if os.path.exists(path):
                os.remove(path)


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    case_id = 0 if message.chat.type == 'private' else 1
    file_id = message.voice.file_id
    task_queue.put((message, file_id, case_id))
    if case_id == 0:
        bot.send_message(message.chat.id, "⏳ Голосовое сообщение поставлено в очередь на обработку.")


@bot.message_handler(content_types=['text'])
def handle_text(message):
    start_time = time.time()
    username = u.mask_name(message.from_user.first_name or "Unknown")
    logger.info(f"->>> Получено текстовое сообщение: chat_id={message.chat.id}, user={username}, text={message.text}")
    try:
        if message.chat.type == 'private':
            emotion = TextProcessor.emo_detection(message.text)
            answer = u.define_emotion("none", emotion, "none")
            bot.send_message(message.chat.id, answer)
        else:
            if u.check_bot_state(message.chat.id):
                emotion = TextProcessor.emo_detection(message.text)
                emodzi = u.emodzi_dict.get(emotion)
                reaction = [types.ReactionTypeEmoji(emoji=emodzi)]
                bot.set_message_reaction(message.chat.id, message.message_id, reaction=reaction)
        duration = time.time() - start_time
        logger.info(f"<<<- Обработка текста завершена за {duration:.2f} сек")

    except Exception as e:
        logger.exception(f"!!! Ошибка при обработке текста: {e}")

def worker():
    while True:
        message, file_id, case_id = task_queue.get()
        if case_id == 0:
            executor.submit(process_audio, message, file_id)
        else:
            if u.check_bot_state(message.chat.id):
                executor.submit(process_audio_group, message, file_id)
        #process_audio(message, file_id)
        task_queue.task_done()


import asyncio

def main():
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()

    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    bot.polling(none_stop=True)

if __name__ == '__main__':
    main()
