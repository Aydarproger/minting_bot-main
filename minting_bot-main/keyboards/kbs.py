from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from create_bot import admins


def main_kb():
    kb_list = [
        [KeyboardButton(text="Загрузить постер в блокчейн TON")],
        [KeyboardButton(text="Выйти из профиля")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb_list,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Воспользуйтесь меню:"
    )
