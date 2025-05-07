import os
import subprocess
import telebot
from telebot import types
import requests
import uuid
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
import aiogram as aio
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
        audio_emotion = AudioProcessor.emot_detection(wav_path)
        text_emotion = TextProcessor.emot_detection(answer)
        #full_answer = answer + audio_emotion + " OOOO " + str(text_emotion)
        full_answer = u.define_emotion(audio_emotion, text_emotion[0], answer)
        bot.send_message(message.chat.id, f"🗣 {full_answer}", parse_mode='Markdown')

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠ Ошибка: {str(e)}")

    finally:
        for path in [ogg_path, wav_path]:
            if os.path.exists(path):
                os.remove(path)


def process_audio_group(message, file_id):
    try:
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
        audio_emotion = AudioProcessor.emot_detection(wav_path)
        emodzi = u.emodzi_dict_audio.get(audio_emotion)
        reaction = [types.ReactionTypeEmoji(emoji=emodzi)]
        bot.set_message_reaction(message.chat.id, message.message_id, reaction=reaction)

    except Exception as e:
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
    print(f"Получено сообщение из чата типа: {message.chat.type} | Текст: {message.text}")
    if message.chat.type == 'private':
        emotion = TextProcessor.emot_detection(message.text)
        answer =  u.define_emotion("none", emotion[0], "none")
        bot.send_message(message.chat.id, answer)
    else:
        if u.check_bot_state(message.chat.id):
            emotion = TextProcessor.emot_detection(message.text)
            emodzi = u.emodzi_dict.get(emotion[0])
            reaction = [types.ReactionTypeEmoji(emoji=emodzi)]
            bot.set_message_reaction(message.chat.id, message.message_id, reaction=reaction)

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


# Запуск обработчика в отдельном потоке
threading.Thread(target=worker, daemon=True).start()

bot.polling(none_stop=True, interval=0)
