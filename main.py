import requests
import time
from datetime import datetime
import pygame
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
import json

# Список адресов кошельков для отслеживания
WALLET_ADDRESSES = [
    'UQBSWAsqvMFTp0SWmw2C3-5e7pEABQp9mAaQ7FAM2h73dEPd',
    'UQA6QVH0s4zpyswZ__yj-xKJaDzMo6r4kvu_EiRcTgT_teX4',
    'UQDzN-ugOIobbO7AAOZXUgZ2eY5qbqE5dTzoXgjK9L8s6NJY',
    'UQA6QVH0s4zpyswZ__yj-xKJaDzMo6r4kvu_EiRcTgT_teX4',
    'UQDzN-ugOIobbO7AAOZXUgZ2eY5qbqE5dTzoXgjK9L8s6NJY',
    'UQAKcCSlYbSzRGAmoP29bKJ5E1ewM_kDp74_wS_ch8LeBSJj',
    'UQB_5eSquBNmCp6A4jkr4L8RGhotR0OTfzncvNFNLCZoj3v1',
    'UQAq_6PiODLG2qBpN8i40gEnL6bhbsnNjnlUF_l-9MHlk4SL',
    'UQC25qtyEmq4aZXFHOYubWFDxr_LYEtuzIBvjhjlXJxVBmqQ',
    'UQBDSmN9gHAysazND_b6s21hWtO7LwcpbvOWygL7rJ-8CQiA',
    'UQB41nn_ibgHaEQs9HyJG-eBMqy1aIgU9yOPZlTPNYZFFs3s',
    'UQBDSmN9gHAysazND_b6s21hWtO7LwcpbvOWygL7rJ-8CQiA',
    'UQA6QVH0s4zpyswZ__yj-xKJaDzMo6r4kvu_EiRcTgT_teX4',
    'UQB41nn_ibgHaEQs9HyJG-eBMqy1aIgU9yOPZlTPNYZFFs3s',
    'UQAUmsxRyJNstMPhe0Ku16VlqiOrpB8F9iB28yBKsMCJ8XsW'
]
 ]



TRANSACTION_URL = 'https://tonviewer.com/transaction/{}'

# URL для получения транзакций
API_URL = 'https://toncenter.com/api/v2/getTransactions?address={}'
# Путь к звуковому файлу
SOUND_FILE = 'sound.mp3'

# Инициализация Pygame
pygame.mixer.init()

# Телеграм токен и chat ID
TELEGRAM_TOKEN = '6672587911:AAEZlgUxvMSSR9_z8MdV5LnvP_mFI4Yarak'
CHAT_ID = '401919854'
CHAT_IDS_FILE = 'chat_ids.json'

# Инициализация Telegram бота
bot = Bot(token=TELEGRAM_TOKEN)


# Функция для загрузки chat ID пользователей
def load_chat_ids():
    try:
        with open(CHAT_IDS_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []


# Функция для сохранения chat ID пользователей
def save_chat_ids(chat_ids):
    with open(CHAT_IDS_FILE, 'w') as file:
        json.dump(chat_ids, file)


# Загружаем chat ID пользователей при старте
chat_ids = load_chat_ids()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    if chat_id not in chat_ids:
        chat_ids.append(chat_id)
        save_chat_ids(chat_ids)
        await update.message.reply_text('You have been registered for transaction notifications.')


def get_transactions(wallet_address):
    response = requests.get(API_URL.format(wallet_address))
    if response.status_code == 200:
        return response.json().get('result', [])
    else:
        print(f"Error fetching transactions for {wallet_address}: {response.status_code}")
        return []


def extract_transaction_info(tx):
    value = int(tx.get('in_msg', {}).get('value', '0'))
    in_msg = tx.get('in_msg', {})
    out_msgs = tx.get('out_msgs', [])
    print(out_msgs)
    print(in_msg)

    # Пример извлечения данных из транзакции
    bought = in_msg.get('message')
    token_name = in_msg.get('token_name', 'Unknown Token')
    timestamp = tx.get('utime', 0)
    transaction_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    for out_msg in out_msgs:
        if out_msg.get('destination') in WALLET_ADDRESSES:
            received = out_msg.get('value')
            received_token_name = out_msg.get('token_name', 'Unknown Token')
            break
    else:
        received = None
        received_token_name = 'Unknown Token'

    return {
        'transaction_id': tx['transaction_id'],
        'value': value,
        'bought': bought,
        'token_name': token_name,
        'received': received,
        'received_token_name': received_token_name,
        'transaction_date': transaction_date
    }


async def check_for_new_transactions(wallet_address, latest_tx_id=None):
    transactions = get_transactions(wallet_address)
    if not transactions:
        return latest_tx_id

    for tx in transactions:
        if latest_tx_id and tx['transaction_id'] == latest_tx_id:
            break
        transaction_info = extract_transaction_info(tx)
        if transaction_info['value'] > 0:  # Простая проверка на входящую транзакцию с ненулевой суммой
            transaction_link = TRANSACTION_URL.format(transaction_info['body_hash'])
            message = (f"New transaction detected for {wallet_address}:\n"
                       f"{transaction_info['transaction_date']} - Bought {transaction_info['token_name']} for {transaction_info['value']} "
                       f"and received {transaction_info['received_token_name']} worth {transaction_info['received']}\n"
                       f"View transaction: {transaction_link}")
            pygame.mixer.music.load(SOUND_FILE)
            pygame.mixer.music.play()
            for chat_id in chat_ids:
                await bot.send_message(chat_id=chat_id, text=message)

    if transactions:
        return transactions[0]['transaction_id']
    return latest_tx_id


async def main():
    latest_tx_ids = {address: None for address in WALLET_ADDRESSES}
    while True:
        for address in WALLET_ADDRESSES:
            latest_tx_ids[address] = await check_for_new_transactions(address, latest_tx_ids[address])
        await asyncio.sleep(60)  # Проверка каждые 60 секунд


if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    application.run_polling()

    # Запуск основного цикла
    asyncio.run(main())
