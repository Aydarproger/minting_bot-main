import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from decouple import config
from pinata_python.pinning import Pinning
from tonutils.client import ToncenterClient
from pinatapy import PinataPy
from tonutils.wallet import WalletV4R2

# получаем список администраторов из .env
admins = [int(admin_id) for admin_id in config('ADMINS').split(',')]

# настраиваем логирование и выводим в переменную для отдельного использования в нужных местах
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# инициируем объект бота, передавая ему parse_mode=ParseMode.HTML по умолчанию
bot = Bot(token="7417711558:AAGNIc3UgKeAtkh93-3TqvEQ_xG7fPP9mo0",
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# инициируем объект бота
dp = Dispatcher(storage=MemoryStorage())

MANIFEST_URL = config('MANIFEST_URL')

# Получаем абсолютный путь к директории, в которой находится текущий скрипт
script_dir = os.path.dirname(os.path.abspath(__file__))

# Создаем путь к директории 'videos' внутри директории скрипта
db_file = os.path.join(script_dir, 'ton_bot.db')
posters = os.path.join(script_dir, 'posters')
pinata = Pinning(PINATA_API_KEY=config("PINATA_API_KEY"), PINATA_API_SECRET=config("PINATA_API_SECRET"))

# TODO: replace all pinata communication the pinatapy
pinata_fixed = PinataPy(config("PINATA_API_KEY"), config("PINATA_API_SECRET"))

client = ToncenterClient(api_key=config("TONCENTER_API_KEY"), is_testnet=True)
# MNEMONIC_FAKE = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about".split()
MNEMONIC_CORRECT = config("MNEMONIC").split()
wallet, _, _, _ = WalletV4R2.from_mnemonic(client, MNEMONIC_CORRECT)
