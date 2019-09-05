"""
Работает с этими модулями:
python-telegram-bot==11.1.0
redis==3.2.1
"""
import os
import logging
import redis

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from moltin import get_products, get_product, get_product_image_url, add_cart_item, get_cart, remove_cart_item, \
    add_customer

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_PROXY = os.getenv('TG_PROXY')

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_PASWORD = os.getenv('REDIS_PASWORD')

REQUEST_KWARGS = {
    'proxy_url': TG_PROXY,
}

logger = logging.getLogger('tg_bot')

_database = None


def handle_menu(bot, update):
    query = update.callback_query
    button = query.data
    logger.debug(f'BUTTON {button} pressed')
    if button == 'cart':
        return send_cart(bot, update)
    else:
        return send_product_detail(bot, update)


def handle_description(bot, update):
    query = update.callback_query
    button = query.data
    logger.debug(f'BUTTON {button} pressed')
    if button == 'menu':
        return send_menu(bot, update)
    else:
        chat_id = update.callback_query.message.chat_id
        product_id, quantity = button.split(',')
        add_cart_item(chat_id, product_id, int(quantity))
        bot.answer_callback_query(query.id, text=f'{quantity} kg added to cart', show_alert=False)
        return 'HANDLE_DESCRIPTION'


def handle_cart(bot, update):
    query = update.callback_query
    button = query.data
    logger.debug(f'BUTTON {button} pressed')
    if button == 'menu':
        return send_menu(bot, update)
    if button == 'checkout':
        bot.edit_message_text(text='Пришлите email', chat_id=query.message.chat_id, message_id=query.message.message_id)
        return 'WAITING_EMAIL'
    else:
        chat_id = update.callback_query.message.chat_id
        cart_item_id = button
        remove_cart_item(chat_id, cart_item_id)
        bot.answer_callback_query(query.id, text=f'removed from cart', show_alert=False)
        return send_cart(bot, update)


def send_menu(bot, update):
    keyboard = [[InlineKeyboardButton(product['name'], callback_data=product['id'])] for product in get_products()]
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        chat_id = update.message.chat_id
    elif update.callback_query:
        query = update.callback_query
        chat_id = update.callback_query.message.chat_id
        bot.delete_message(chat_id=chat_id,
                           message_id=query.message.message_id)

    bot.send_message(chat_id=chat_id, text='Please choose:', reply_markup=reply_markup)

    logger.debug(f'MENU sent')
    return 'HANDLE_MENU'


def send_product_detail(bot, update):
    query = update.callback_query
    product_id = query.data
    product = get_product(product_id)

    name = product['name']
    price = product['price_formatted']
    availability = product['availability']
    description = product['description']
    image_id = product['image_id']

    message = f'{name}\n\n{price} per KG\n{availability} on stock\n\n{description}'
    product_image_url = get_product_image_url(image_id)

    keyboard = [[InlineKeyboardButton("1 KG", callback_data=f'{product_id},1'),
                 InlineKeyboardButton("5 KG", callback_data=f'{product_id},5'),
                 InlineKeyboardButton("10 KG", callback_data=f'{product_id},10')],
                [InlineKeyboardButton('Назад', callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.delete_message(chat_id=query.message.chat_id,
                       message_id=query.message.message_id)

    bot.send_photo(
        chat_id=query.message.chat_id,
        photo=product_image_url,
        caption=message,
        reply_markup=reply_markup)

    logger.debug(f'Product detail {name} sent')
    return 'HANDLE_DESCRIPTION'


def send_cart(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    cart = get_cart(chat_id)
    keyboard = [[InlineKeyboardButton('В меню', callback_data='menu')]]

    if cart['products']:
        text_rows = [
            '{0}\n{1}\n{2} per kg\n{3} kg in cart for {4}'.format(product['name'],
                                                                  product['description'],
                                                                  product['unit_price'],
                                                                  product['quantity'],
                                                                  product['total_price'])
            for product in cart['products']]
        text_rows.append(f'Total: {cart["total_price"]}')
        text = '\n\n'.join(text_rows)

        keyboard.extend(
            [[InlineKeyboardButton(f' Убрать {product["name"]}', callback_data=product['id'])] for product in
             cart['products']])
        keyboard.append([InlineKeyboardButton('Оформить заказ', callback_data='checkout')])

    else:
        text = 'You don\'t have any items in your cart.'

    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.edit_message_text(text=text, chat_id=chat_id, message_id=query.message.message_id, reply_markup=reply_markup)

    logger.debug(f'Cart sent')
    return 'HANDLE_CART'


def checkout(bot, update):
    users_reply = update.message.text
    logger.debug(f'received email {users_reply}')

    customer_id = add_customer('TG customer', users_reply)
    logger.debug(f'customer_id {customer_id} received')

    if customer_id:
        logger.debug(f'Order {update.message.chat_id} has been registered')
        update.message.reply_text(f'Номер вашего заказа {update.message.chat_id}')
        return 'START'
    else:
        update.message.reply_text(f'Ошибка в адресе электронной почты. Отправьте еще раз')
        logger.debug(f'Wrong email received')
        return 'WAITING_EMAIL'


def handle_users_reply(bot, update):
    """
    Функция, которая запускается при любом сообщении от пользователя и решает как его обработать.
    Эта функция запускается в ответ на эти действия пользователя:
        * Нажатие на inline-кнопку в боте
        * Отправка сообщения боту
        * Отправка команды боту
    Она получает стейт пользователя из базы данных и запускает соответствующую функцию-обработчик (хэндлер).
    Функция-обработчик возвращает следующее состояние, которое записывается в базу данных.
    Если пользователь только начал пользоваться ботом, Telegram форсит его написать "/start",
    поэтому по этой фразе выставляется стартовое состояние.
    Если пользователь захочет начать общение с ботом заново, он также может воспользоваться этой командой.
    """
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': send_menu,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': checkout,
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(bot, update)
        logger.debug(f'Transit to {next_state} state')
        db.set(chat_id, next_state)
    except Exception as err:
        logger.error(err)


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = REDIS_PASWORD
        database_host = REDIS_HOST
        database_port = REDIS_PORT
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


def start_bot():
    logger.info(f'TG bot started')
    updater = Updater(TELEGRAM_TOKEN, request_kwargs=REQUEST_KWARGS)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()


if __name__ == '__main__':
    start_bot()
