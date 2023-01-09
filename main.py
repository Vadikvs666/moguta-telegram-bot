import logging
import os
import threading
import asyncio
import aiogram
import telebot
from aiogram import types
from dotenv import load_dotenv
from pathlib import Path
import json
import requests

dotenv_path = Path('.env')
load_dotenv(dotenv_path=dotenv_path)
API_TOKEN = os.getenv('API_TOKEN')

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot(API_TOKEN, parse_mode=None)

user_dict = dict()

PAGE_COUNT = 10



class User:
    def __init__(self, url):
        self.url = url
        self.token = None
        self.lst = 0


def get_orders(user: User, count: int):
    params = {'token': user.token, 'method': 'getOrder', 'param': '{"count":1}'}
    r = requests.get('https://' + user.url + '/api', params=params)
    data = json.loads(r.text)
    if data["status"] == "OK":
        print(r.text)
        cnt_orders = data["response"]["countOrder"]
        page = int(int(cnt_orders) / count)
        pages = {"count": count, "page": page}
        params = {'token': user.token, 'method': 'getOrder', 'param': json.dumps(pages)}
        r = requests.get('https://' + user.url + '/api', params=params)
        data = json.loads(r.text)
        orders = data["response"]["orders"]
        if int(cnt_orders) % page != 0:
            page = page + 1
            pages = {"count": count, "page": page}
            params = {'token': user.token, 'method': 'getOrder', 'param': json.dumps(pages)}
            r = requests.get('https://' + user.url + '/api', params=params)
            data = json.loads(r.text)
            orders_1 = data["response"]["orders"]
            orders = orders + orders_1
        return orders


def get_order(user: User, order: str):
    params = {'token': user.token, 'method': 'getOrder', 'param': '{"number":["' + order + '"]}'}
    r = requests.get('https://' + user.url + '/api', params=params)
    data = json.loads(r.text)
    return data["response"]["orders"][0]["order_content"]


def check_orders(chat_id):
    try:
        user = user_dict[chat_id]
        data = get_orders(user, PAGE_COUNT)
        lst_order = 0
        for order in data:
            lst_order = int(order["id"])
            if user.lst < lst_order:
                user.lst = lst_order
                bot.send_message(chat_id,
                                 f'Номер заказа : <a href="tg://msg_url?&text={order["number"]}">{order["number"]}</a>\n'
                                 f'Имя покупателя: {order["name_buyer"]} \n'
                                 f'Сумма: {order["summ_shop_curr"]} \n'
                                 f'Дата: {order["add_date"]} ', parse_mode="HTML")
    except Exception as e:
        start_timer(chat_id)
    start_timer(chat_id)


def start_timer(chat_id):
    t = threading.Timer(30, check_orders, [chat_id])
    t.start()


# Handle '/start' and '/help'
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    msg = bot.reply_to(message, """\
Привет я бот который будет 
присылать тебе заказы из Могуты
Напишите адрес твоего сайта
""")
    bot.register_next_step_handler(msg, process_site_step)


def process_site_step(message):
    try:
        chat_id = message.chat.id
        url = message.text
        user = User(url)
        user_dict[chat_id] = user
        msg = bot.reply_to(message, 'А теперь напишите токен доступа к API из админки сайта')
        bot.register_next_step_handler(msg, process_token_step)
    except Exception as e:
        bot.reply_to(message, 'Ошибочка вышла')


def process_token_step(message):
    try:
        chat_id = message.chat.id
        token = message.text
        user = user_dict[chat_id]
        user.token = token
        bot.send_message(chat_id, 'Ваш сайт:  ' + user.url + '\n Token: ' + user.token)
        start_timer(chat_id)
    except Exception as e:
        bot.reply_to(message, 'Ошибочка вышла')


@bot.message_handler(commands=['info'])
def info_handler(message):
    try:
        user = user_dict[message.chat.id]
        bot.send_message(message.chat.id, 'Ваш сайт:  ' + user.url + '\n Token: ' + user.token)
    except Exception as e:
        error_handler(message)


@bot.message_handler(commands=['last'])
def info_handler(message):
    try:
        chat_id = message.chat.id
        user = user_dict[chat_id]
        data = get_orders(user, 5)
        for order in data:
            bot.send_message(message.chat.id,
                             f'Номер заказа : <a href="tg://msg_url?&text={order["number"]}">{order["number"]}</a>\n'
                             f'Имя покупателя: {order["name_buyer"]} \n'
                             f'Сумма: {order["summ_shop_curr"]} \n'
                             f'Дата: {order["add_date"]} ', parse_mode="HTML")
    except Exception as e:
        error_handler(message)


def error_handler(message):
    bot.send_message(message.chat.id, 'Произошла ошибка:  \n'
                                      'Вы можете проверить параметры по команде /info \n'
                                      'Если ошибка повторяется попробуйте команду /start',
                     parse_mode="HTML")


@bot.message_handler()
def answer_handler(message):
    try:
        user = user_dict[message.chat.id]
        products = get_order(user, message.text)
        msg = f'Товары в заказе {message.text} : \n'
        for prod in products:
            msg = msg + f'Код: <b> {prod["code"]}</b> \n'
            msg = msg + f'Наименование: <b> {prod["name"]}</b>\n'
            msg = msg + f'Цена: <b> {prod["fulPrice"]}</b> \n'
            msg = msg + f'Кол-во: <b> {prod["count"]}</b> \n'
        bot.send_message(message.chat.id, msg, parse_mode="HTML")
        start_timer(message)
    except Exception as e:
        error_handler(message)


bot.enable_save_next_step_handlers(delay=2)
bot.load_next_step_handlers()

if __name__ == '__main__':
    bot.infinity_polling()
