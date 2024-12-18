import asyncio
from io import BytesIO

import pytonconnect
import qrcode
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pytonconnect import TonConnect
from pytoniq_core import Address
from create_bot import logger, db_file
from db_handler.db_funk import get_user_by_telegram_id, add_user, update_user, is_wallet_unique, \
    delete_user_by_telegram_id
from keyboards.kbs import main_kb
from utils.api_methods import get_sms_code, consume_code
from utils.connector import get_connector
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

class Form(StatesGroup):
    sms_code = State()
    ps_login = State()


start_router = Router()


@start_router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext):
    await state.clear()
    user_info = await get_user_by_telegram_id(db_file, message.from_user.id)
    check = False
    if user_info:
        check = True
    mk_b = InlineKeyboardBuilder()
    connector = get_connector(message.chat.id)
    is_connected = await connector.restore_connection()

    if is_connected and check:
        verified = user_info.get('verified')
        wallet_address = user_info.get('wallet')
        if verified == 'да':
            await message.answer(
                f'Вы верифицировали ваш аккаунт как художник. Теперь вы можете создавать постеры NFT в '
                f'блокчейне TON, которые отобразятся в приложении Posterstock. Также, все NFT будут '
                f'отображаться в вашем кошельке.', reply_markup=main_kb()
            )
        else:
            await message.answer(f'Вы подключились с адресом <code>{wallet_address}</code>.  '
                                 f'Укажите пожалуйста ваш username в Posterstock: ')
            logger.info(f'connect with address: {wallet_address}')
            await state.set_state(Form.ps_login)
    else:
        wallets_list = TonConnect.get_wallets()
        for wallet in wallets_list:
            if wallet['name'] in ['Wallet', 'Tonkeeper']:
                mk_b.button(text=wallet['name'], callback_data=f'connect:{wallet["name"]}')
        mk_b.adjust(1)
        await message.answer(text='Для авторизации, пожалуйста, выберите кошелек для подключения ',
                             reply_markup=mk_b.as_markup())


@start_router.callback_query(F.data.startswith('connect:'))
async def connect_wallet(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    message = call.message
    wallet_name = call.data.split(':')[1]
    connector = get_connector(message.chat.id)

    wallets_list = connector.get_wallets()
    wallet = next((w for w in wallets_list if w['name'] == wallet_name), None)
    if wallet is None:
        await message.answer(f'Unknown wallet: {wallet_name}')
        return

    generated_url = await connector.connect(wallet)
    mk_b = InlineKeyboardBuilder()
    mk_b.button(text='Connect', url=generated_url)

    img = qrcode.make(generated_url)
    stream = BytesIO()
    img.save(stream)
    file = BufferedInputFile(file=stream.getvalue(), filename='qrcode')
    await message.answer_photo(photo=file, caption='Connect wallet within 3 minutes', reply_markup=mk_b.as_markup())

    mk_b.button(text='Start', callback_data='start')
    connect_check = {'status': False}
    wallet_address = None
    user_info = await get_user_by_telegram_id(db_file, call.from_user.id)
    for _ in range(180):
        await asyncio.sleep(1)
        print(_, connector.__dict__)
        if connector.connected:
            print(connector.__dict__)
            if connector.account.address:
                wallet_address = Address(connector.account.address).to_str(is_bounceable=False)
                print(wallet_address)
                # Проверка, есть ли уже такой кошелек в системе
                check_uniq = await is_wallet_unique(db_file, wallet_address)
                if not check_uniq:
                    await message.answer(
                        f'Кошелек с адресом <code>{wallet_address}</code> уже зарегистрирован в системе.')
                    return

                # Если пользователь уже существует, обновляем данные
                if user_info:
                    await update_user(db_file,
                                      user_data={'telegram_id': call.from_user.id, 'wallet': wallet_address,
                                                 "full_name": call.from_user.full_name,
                                                 'login': call.from_user.username})
                else:
                    # Если пользователь новый, добавляем его в базу данных
                    await add_user(db_file,
                                   table_name='users',
                                   user_data={'telegram_id': call.from_user.id, 'wallet': wallet_address,
                                              "full_name": call.from_user.full_name,
                                              'login': call.from_user.username})

                logger.info(f'connect with address: {wallet_address}')
                connect_check['status'] = True
                break

    if connect_check['status'] and user_info:
        await message.answer(f'Вы подключились с адресом <code>{wallet_address}</code>.')
        await state.clear()
    elif connect_check['status']:
        await message.answer(f'Вы подключились с адресом <code>{wallet_address}</code>.  '
                             f'Укажите пожалуйста ваш username в Posterstock: '
                             f' ')
        await state.set_state(Form.ps_login)
    else:
        await message.answer(f'Вы не успели выполнить авторизацию за 3 минуты! Пожалуйста, попробуйте еще раз',
                             reply_markup=mk_b.as_markup())


@start_router.message(F.text, Form.ps_login)
async def command_start_handler(message: Message, state: FSMContext):
    ps_login = message.text
    check = await get_sms_code(user_login=ps_login)
    if check:
        await state.update_data(ps_login=ps_login)
        await message.answer(f'Пользователь с ником {ps_login} найден в Posterstock. Сейчас, '
                             f'в приложении вы получили 4-х значный код подтверждения. '
                             f'Пожалуйста, введите его: ')
        await state.set_state(Form.sms_code)
    else:
        await message.answer(f'Пользователь с ником {ps_login} не найден в Posterstock. '
                             f'Пожалуйста, попробуйте еще раз')
        await state.set_state(Form.ps_login)


@start_router.message(F.text, Form.sms_code)
async def command_start_handler(message: Message, state: FSMContext):
    try:
        sms_code = int(message.text)
        user_info = await get_user_by_telegram_id(db_file, message.from_user.id)
        print(user_info)
        user_data = await state.get_data()
        print(user_data)
        check = await consume_code(code=sms_code, tg_nickname=str(message.from_user.id),
                                   ton_address=user_info.get('wallet'), login=user_data.get('ps_login'))
        print(check)
        if sms_code == 4444 or check:
            await update_user(db_file, {'sms_code': sms_code,
                                        'telegram_id': message.from_user.id,
                                        'verified': 'да',
                                        'ps_login': user_data.get('ps_login')})
            await message.answer(
                f'Вы верифицировали ваш аккаунт как художник. Теперь вы можете создавать постеры NFT в '
                f'блокчейне TON, которые отобразятся в приложении Posterstock. Также, все NFT будут '
                f'отображаться в вашем кошельке.', reply_markup=main_kb())
            await state.clear()
        else:
            await message.answer(f'Неверный sms-код (нужно указать 4444 или реальные цифры с смс). Попробуйте еще раз:')
            await state.set_state(Form.sms_code)
    except Exception as E:
        print(E)
        await message.answer(f'Необходимо код отправлять именно цифрами. Без лишних символов. Повторите попытку:')
        await state.set_state(Form.sms_code)


@start_router.message(F.text == "Выйти из профиля")
@start_router.message(Command('exit'))
async def command_start_handler(message: Message, state: FSMContext):
    await state.clear()
    await delete_user_by_telegram_id(db_file, message.from_user.id)
    await message.answer('Вы успешно вышли из системы, отвязав свой кошелек и логин с сайта PosterStock',
                         keyboards=ReplyKeyboardRemove())
    mk_b = InlineKeyboardBuilder()
    wallets_list = TonConnect.get_wallets()
    for wallet in wallets_list:
        if wallet['name'] in ['Wallet', 'Tonkeeper']:
            mk_b.button(text=wallet['name'], callback_data=f'connect:{wallet["name"]}')
    mk_b.adjust(1)
    await message.answer(text='Для повторной авторизации, пожалуйста, выберите кошелек для подключения ',
                         reply_markup=mk_b.as_markup())


# @start_router.message(Command('test'))
# async def command_start_handler(message: Message, state: FSMContext):
#     await state.clear()
#     info = get_storage_path(message.from_user.id)
#     await message.answer(info)
