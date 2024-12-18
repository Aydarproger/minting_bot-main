import aiohttp
from create_bot import logger
import asyncio


async def get_poster_info(poster_name: str):
    url = f'https://api.posterstock.com/api/media/public/search?query={poster_name}&lang=ru-RU'

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()  # Поднимает исключение для HTTP ошибок
            return await response.json()


async def send(poster_name: str):
    url = f'https://api.posterstock.com/api/media/public/search?query={poster_name}&lang=ru-RU'

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()  # Поднимает исключение для HTTP ошибок
            return await response.json()


async def get_sms_code(user_login="mr.mnogo79351"):
    url = f'https://api.posterstock.com/api/external/{user_login}/code/send'
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers={'accept': '*/*'}) as response:
            if response.status == 200:
                return True
            logger.error(f'Request failed with status {response.status}')
            return False


async def consume_code(code, tg_nickname, ton_address, login='mr.mnogo79351'):
    url = f'https://api.posterstock.com/api/external/{login}/code/consume'
    data = {"code": code, "tg_nickname": tg_nickname, "ton_address": ton_address}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers={'accept': '*/*'}, json=data) as response:
            if response.status == 200 or response.status == 500:
                return True
            logger.error(f'Request failed with status {response.status}')
            return False


async def send_poster(collection_address: str):
    url = 'https://api.posterstock.com/api/posters/onchain'
    async with aiohttp.ClientSession() as session:
        d = {"collection": collection_address, "lang": "en-US"}
        async with session.post(url, headers={'accept': '*/*'}, json=d) as response:
            if response.status == 200:
                data = await response.json()
                # Извлекаем `username` и `id` для формирования ссылки
                username = data["user"]["username"]
                poster_id = data["id"]
                # Формируем URL
                poster_url = f"https://posterstock.com/{username}/{poster_id}"
                return poster_url
            else:
                # В случае ошибки возвращаем None
                return None


async def send_telegram_message(link: str, username: str,
                                token: str = "7851556533:AAEAZOXLD0rSNzHC7CClXvSZkIUQ4F0uSyk",
                                chat_id: str = "3063450"):
    formatted_text = (
        f"Новый минт:\n\n"
        f"👤 *Логин в системе:* `{username}`\n"
        f"🔗 *Ссылка:* [Перейти по ссылке]({link})"
    )
    payload = {
        "chat_id": chat_id,
        "text": formatted_text,
        "parse_mode": "Markdown"
    }

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                print("Сообщение успешно отправлено.")
            else:
                print(f"Ошибка отправки сообщения: {response.status}")
                print(await response.text())
