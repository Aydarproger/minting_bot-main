import asyncio
import os
import shutil

from create_bot import logger, pinata, pinata_fixed, db_file
from PIL import Image
import json
import uuid
from pytonconnect import TonConnect
from db_handler.db_funk import get_user_by_telegram_id
from utils.connector import get_connector
from pytonconnect import TonConnect
from pytonconnect.storage import FileStorage
from create_bot import MANIFEST_URL


# Определяем путь к файлу хранения данных для конкретного пользователя
async def is_user_connected(chat_id: int) -> bool:
    storage_path = f'./connections/{chat_id}.json'
    if not os.path.exists(storage_path):
        return False
    storage = FileStorage(storage_path)
    connector = TonConnect(manifest_url=MANIFEST_URL, storage=storage)
    is_connected = await connector.restore_connection()
    return is_connected


async def ensure_wallet_connection(user_id: int) -> bool:
    """
    Проверяет и восстанавливает подключение к кошельку для указанного пользователя.
    Возвращает True, если подключение успешно, иначе False.
    """
    try:
        connector = get_connector(user_id)
        is_connected = await connector.restore_connection()
        if not is_connected:
            user_info = await get_user_by_telegram_id(db_file, user_id)
            if user_info:
                wallet_address = user_info.get('wallet')
                wallets_list = connector.get_wallets()
                wallet = next((w for w in wallets_list if w['name'] == wallet_address), None)
                if wallet:
                    await connector.connect(wallet)
                    return await connector.restore_connection()
        return is_connected
    except Exception as e:
        print(f"Ошибка при проверке подключения: {e}")
        return False


def prepare_metadata(username, fin_data):
    name = username + " - " + fin_data["film_title"]
    description = fin_data["poster_description"]
    image = fin_data["pin_address"]
    amount = fin_data["poster_count"]
    collection_metadata = {
        "name": name,
        "description": description,
        "image": image
    }
    dirname = f'./{uuid.uuid4()}/'
    os.mkdir(dirname)
    with open(f'{dirname}/collection.json', 'w') as f:
        json.dump(collection_metadata, f)
    d = {
        'Без текста': "Textless",
        'Русский': "Russian",
        'Английский': "English"
    }
    for index in range(amount):
        item_metadata = {
            "name": f"#{index + 1}",
            "image": image,
            "attributes": [
                {
                    "trait_type": "Type",
                    "value": fin_data["film_type"].title()
                },
                {
                    "trait_type": "Year",
                    "value": fin_data["film_start_year"]
                },
                {
                    "trait_type": "Language",
                    "value": d[fin_data["poster_lang"]]
                },
                {
                    "trait_type": "MediaID",
                    "value": fin_data["film_id"]
                }
            ]
        }
        with open(f'{dirname}/{index}.json', 'w') as f:
            json.dump(item_metadata, f, indent=4)

    metadata_url = f"https://ipfs.io/ipfs/{pinata_fixed.pin_file_to_ipfs(dirname, save_absolute_paths=False)['IpfsHash']}/"
    shutil.rmtree(dirname, ignore_errors=True)
    return metadata_url


def get_image_resolution(file_path):
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            return {'width': int(width), 'height': int(height)}
    except IOError:
        print(f"Не удалось открыть файл: {file_path}")
        return None


async def get_pinata_address(photo_path: str):
    for _ in range(10):
        try:
            photo_path = photo_path.replace("\\", "/")
            pinata_data = pinata.pin_file_to_ipfs(photo_path)
            return {
                'pin_hash': pinata_data['IpfsHash'],
                'pin_size': pinata_data['PinSize'],
                'pin_address': f"https://ipfs.io/ipfs/{pinata_data['IpfsHash']}"
            }

        except Exception as e:
            logger.error(e)
            await asyncio.sleep(1)


def get_poster_dict(data_fsm: dict, pinata_data: dict):
    fin_data = {}
    fin_data.update(data_fsm)
    fin_data.update(pinata_data)
    film_data = fin_data['rez_data']

    try:
        price_ton_int = int(fin_data['price_ton'])
    except:
        price_ton_int = 0

    return {'telegram_id': fin_data['telegram_id'], 'film_id': film_data['id'], 'film_type': film_data['type'],
            'film_title': film_data['title'], 'film_start_year': film_data['start_year'],
            'film_end_year': film_data['end_year'], 'film_main_poster': film_data['main_poster'],
            'poster_name_user_type': fin_data['poster_name'], 'poster_lang': fin_data['poster_lang'],
            'photo_path': fin_data['photo_path'], 'poster_count': fin_data['poster_count'],
            'price_ton': price_ton_int, 'poster_description': fin_data['poster_description'],
            'pin_hash': fin_data['pin_hash'], 'pin_size': fin_data['pin_size'], 'pin_address': fin_data['pin_address']}


def delete_file(file_path):
    try:
        os.remove(file_path)
        logger.info("Deleted file '{file_path}'")
    except OSError as e:
        logger.error(f"Ошибка при удалении файла '{file_path}': {e}")
