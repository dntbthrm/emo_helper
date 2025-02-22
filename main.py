# 7517194057:AAGWgt2VIci1bmEgn8CVrsYBPJskaQfeGrw
import telebot
from telebot import types
bot = telebot.TeleBot('7517194057:AAGWgt2VIci1bmEgn8CVrsYBPJskaQfeGrw')

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

bot.polling(none_stop=True, interval=0)
