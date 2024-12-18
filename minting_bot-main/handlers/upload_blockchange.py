import os
import asyncio
import time
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pytonconnect import TonConnect
from pytonconnect.exceptions import UserRejectsError
from pytonconnect.storage import FileStorage

from create_bot import bot, posters, db_file, MANIFEST_URL
from db_handler.db_funk import add_poster, get_user_film_ids
from keyboards.kbs import main_kb
from utils.api_methods import get_poster_info, send_poster, send_telegram_message
from utils.utils import get_pinata_address, get_poster_dict, delete_file, get_image_resolution, prepare_metadata, \
    is_user_connected
from utils.connector import get_connector
from db_handler.db_funk import get_user_by_telegram_id
from utils.nft import deploy_nft_collection, deploy_nft_items, put_nft_on_sale, wait_for_seqno, calc_fee_amount, \
    get_addr, transfer_ownership


class UploadForm(StatesGroup):
    poster_count = State()
    poster_name = State()
    film = State()
    poster_lang = State()
    poster_img = State()
    price_ton = State()
    poster_description = State()
    poster_check = State()


upload_router = Router()


@upload_router.message(F.text.contains('Загрузить постер'))
async def command_start_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('Введите название фильма или сериала, к которому вы хотите загрузить постер.\n\n'
                         '⚠️ Название можно ввести на русском и на английском языке.',
                         reply_markup=ReplyKeyboardRemove())
    await state.set_state(UploadForm.poster_name)


@upload_router.message(F.text, UploadForm.poster_name)
async def command_start_handler(message: Message, state: FSMContext):
    poster_name = message.text
    rez = await get_poster_info(poster_name.lower())
    if len(rez) > 0:

        await state.update_data(rez_data=rez, poster_name=poster_name)
        builder = InlineKeyboardBuilder()
        stop_list = await get_user_film_ids(db_file, telegram_id=message.from_user.id)
        for i in rez:
            if len(stop_list):
                if i['id'] in stop_list:
                    continue
            builder.button(text=f"{i['title']} {i['start_year']}", callback_data=f'film_{i["id"]}')
        builder.adjust(1)
        await message.answer(f'Найдено {len(rez)} результатов.\n\n'
                             f'Выберите фильм или сериал, постер к которому вы хотите загрузить.',
                             reply_markup=builder.as_markup())
        await state.set_state(UploadForm.film)
    else:
        await message.answer('Не удалось найти фильм или сериал с таким названием.\n\n'
                             '⚠️Название можно ввести на русском и на английском языке.')
        await state.set_state(UploadForm.poster_name)


@upload_router.message(F.text, UploadForm.film)
async def command_start_handler(message: Message, state: FSMContext):
    poster_name = message.text
    rez = await get_poster_info(poster_name.lower())
    if len(rez) > 0:
        await state.update_data(rez_data=rez, poster_name=poster_name)
        builder = InlineKeyboardBuilder()
        stop_list = await get_user_film_ids(db_file, telegram_id=message.from_user.id)
        for i in rez:
            if len(stop_list):
                if i['id'] in stop_list:
                    continue
            builder.button(text=f"{i['title']} {i['start_year']}", callback_data=f"film_{i['id']}")
        builder.adjust(1)
        await message.answer(f'Найдено {len(rez)} результатов.\n\n'
                             f'Выберите фильм или сериал, постер к которому вы хотите загрузить.',
                             reply_markup=builder.as_markup())
        await state.set_state(UploadForm.film)
    else:
        await message.answer('Не удалось найти фильм или сериал с таким названием.\n\n'
                             '⚠️Название можно ввести на русском и на английском языке.')
        await state.set_state(UploadForm.poster_name)


@upload_router.callback_query(F.data.startswith('film_'), UploadForm.film)
async def command_start_handler(call: CallbackQuery, state: FSMContext):
    film_id = int(call.data.replace("film_", ''))
    data = await state.get_data()
    all_data = data['rez_data']
    film = None
    for i in all_data:
        if i['id'] == film_id:
            film = i
            break
    await state.update_data(rez_data=film)
    await call.answer(f'Вы выбрали: {film.get("title")}!')

    builder = InlineKeyboardBuilder()
    for title in ['Без текста', 'Русский', 'Английский']:
        builder.button(text=title, callback_data=title)
    builder.adjust(1)
    await call.message.answer(f'Выберите язык текста на постере: ', reply_markup=builder.as_markup())
    await state.set_state(UploadForm.poster_lang)


@upload_router.callback_query(F.data, UploadForm.poster_lang)
async def command_start_handler(call: CallbackQuery, state: FSMContext):
    poster_lang = call.data.replace("poster_", '')
    await call.answer(f'Вы выбрали {poster_lang}')
    await state.update_data(poster_lang=poster_lang)
    await call.message.answer('Отправьте файл постера. Допустимое разрешение 2000х3000 пикселей. '
                              'Допустимые форматы: JPG, PNG, JPEG.\n\n⚠️После загрузки постера в блокчейн, '
                              'невозможно внести изменения в постер. Загрузить другой постер к этому фильму или сериалу будет нельзя. ')
    await state.set_state(UploadForm.poster_img)


@upload_router.message(F.content_type.in_({'document', 'photo'}), UploadForm.poster_img)
async def handle_poster_image(message: Message, state: FSMContext):
    if message.photo or message.document.mime_type == 'image/png' or message.document.mime_type == 'image/jpeg':
        if message.photo:
            await message.answer('Пожалуйста, отправьте ваше фото "Без сжатия" (файлом)')
            await state.set_state(UploadForm.poster_img)
        else:
            file_id = message.document.file_id
            content_type = 'document'
            file = str(os.path.join(posters, f"{file_id[:5]}.jpg"))
            if not os.path.exists(posters):
                os.makedirs(posters)
            await bot.download(file=file_id, destination=file)
            info = get_image_resolution(file)

            '''=== ТУТ МЕСТО ГДЕ НУЖНО УБРАТЬ NOT В БОЕВОМ РЕЖИМЕ ==='''
            if info.get('width') == 2000 and info.get('height') == 3000:
                await state.update_data(file_id=file_id, photo_path=file, content_type=content_type)
                await message.answer('Введите количество экземпляров от 1 до 30 шт.\n\n'
                                     '⚠ Если вы не обладаете большой аудитрией, рекомендуется не выпускать максимальное '
                                     'количество постеров. Например, выпустив 10 постеров, вы можете '
                                     'больше заработать на более высоком спросе от роялти, чем на количестве. ')
                await state.set_state(UploadForm.poster_count)
            else:
                await message.answer(f'Некорректное разрешение файла: {info}. Допустимое разрешение: 2000х3000 '
                                     f'пикселей.\n\nПожалуйста, отправьте корректный файл!')
                await state.set_state(UploadForm.poster_img)
    else:
        await message.answer('Неверный формат файла. Допустимые форматы: JPG, PNG, JPEG .\n\n'
                             'Пожалуйста, отправьте корректный файл')
        await state.set_state(UploadForm.poster_img)


@upload_router.message(F.text, UploadForm.poster_count)
async def handle_poster_count(message: Message, state: FSMContext):
    try:
        count = int(message.text)
        if 1 <= count <= 30:
            await state.update_data(poster_count=count)
            await message.answer(
                'Введите цену в $TON. Курс можно посмотреть '
                '<a href="https://www.coingecko.com/ru/Криптовалюты/toncoin/rub">здесь</a>\n\n'
                '⚠ К цене будет прибавлено 2,5% сервисной комиссии.\n\n'
                'Вы можете ввести как целое число (например, 1) или дробное число '
                'с использованием точки или запятой (например, 0.5 или 0,5).',
                disable_web_page_preview=True
            )
            await state.set_state(UploadForm.price_ton)
        else:
            await message.answer('Некорректное количество экземпляров. Пожалуйста, введите число от 1 до 30.')
            await state.set_state(UploadForm.poster_count)
    except ValueError:
        await message.answer('Некорректный формат. Пожалуйста, введите целое число от 1 до 30.')
        await state.set_state(UploadForm.poster_count)


@upload_router.message(F.text, UploadForm.price_ton)
async def handle_poster_price(message: Message, state: FSMContext):
    user_input = message.text.replace(',', '.').strip()
    try:
        price_ton = float(user_input)
        if price_ton > 0:
            await state.update_data(price_ton=price_ton)
            await message.answer('Введите описание постера (до 240 символов):')
            await state.set_state(UploadForm.poster_description)
        else:
            await message.answer(
                'Некорректная стоимость. Цена должна быть больше 0. Пожалуйста, введите положительное число.')
            await state.set_state(UploadForm.price_ton)
    except ValueError:
        await message.answer(
            'Некорректный формат. Пожалуйста, введите число, используя цифры и, при необходимости, точку или запятую.')
        await state.set_state(UploadForm.price_ton)


@upload_router.message(F.text, UploadForm.poster_description)
async def handle_poster_image(message: Message, state: FSMContext):
    poster_description = message.text
    if len(poster_description) <= 240:
        await state.update_data(poster_description=poster_description, telegram_id=message.from_user.id)
        data = await state.get_data()
        film = data['rez_data']
        poster_lang = data['poster_lang']
        poster_count = data['poster_count']
        price_ton = data['price_ton']
        poster_description = data['poster_description']
        file_id = data['file_id']

        caption = (f'<u>Проверьте данные создания NFT постера:</u>\n\n'
                   f'🎬 <b>Название фильма:</b> {film["title"]} ({film["start_year"]})\n'
                   f'🔢 <b>Количество экземпляров:</b> {poster_count}\n'
                   f'💰 <b>Цена за экземпляр:</b> {price_ton} TON\n'
                   f'📝 <b>Описание:</b> {poster_description}\n'
                   f'🌐 <b>Язык постера:</b> {poster_lang}\n\n'
                   '<i>Подтвердите правильность данных перед созданием NFT постера.</i>')

        builder = InlineKeyboardBuilder()
        builder.button(text='Создать NFT постер', callback_data='Создать NFT постер')
        builder.button(text='Отменить Создание NFT постера', callback_data='Отменить Создание NFT постера')
        builder.adjust(1)
        await message.answer_photo(photo=FSInputFile(path=data.get('photo_path')), caption=caption,
                                   reply_markup=builder.as_markup())
        await state.set_state(UploadForm.poster_check)
    else:
        await message.answer(
            'Ваше описание превышает 240 символов. Пожалуйста, отправьте корректное описание постера: ')
        await state.set_state(UploadForm.poster_description)


@upload_router.callback_query(F.data, UploadForm.poster_check)
async def command_start_handler(call: CallbackQuery, state: FSMContext):
    if call.data == 'Создать NFT постер':
        data = await state.get_data()
        pinata_data = await get_pinata_address(data.get('photo_path'))
        poster_amount = data.get('poster_count')
        await call.message.answer('Осталось оплатить комиссию блокчейна для создания новой коллекции. '
                                  'Пожалуйста, перейдите в свой кошелек и подтвердите транзакцию.')

        is_connected = await is_user_connected(call.message.chat.id)
        if not is_connected:
            await call.message.answer('Вы не подключены. Пожалуйста, подключитесь и повторите попытку.',
                                      reply_markup=main_kb())
            await state.clear()
            return

        storage_path = f'./connections/{call.message.chat.id}.json'
        storage = FileStorage(storage_path)
        connector = TonConnect(manifest_url=MANIFEST_URL, storage=storage)
        await connector.restore_connection()
        try:
            await connector.send_transaction({
                'valid_until': int(time.time()) + 360 * 5,
                'messages': [
                    {
                        'address': get_addr(),
                        'amount': calc_fee_amount(poster_amount),
                    }
                ]})
        except UserRejectsError:
            await call.message.answer('Сценарий по добавлению постера остановлен. Все данные очищены.',
                                      reply_markup=main_kb())
            await state.clear()
            return

        fin_data = get_poster_dict(data_fsm=data, pinata_data=pinata_data)
        await add_poster(db_file, 'posters', fin_data)
        user_info = await get_user_by_telegram_id(db_file, call.from_user.id)
        metadata = prepare_metadata(user_info["ps_login"], fin_data)
        nft_collection_address = await deploy_nft_collection(metadata + "collection.json", metadata,
                                                             user_info["wallet"])
        await call.message.answer(f'Ваша коллекция успешно размещена в блокчейне TON! Начат минтинг NFT...')

        await send_telegram_message(f'https://getgems.io/collection/{nft_collection_address}',
                                    user_info["ps_login"])

        await wait_for_seqno()
        await deploy_nft_items(poster_amount, nft_collection_address)
        await wait_for_seqno()
        await call.message.answer("Все NFT успешно созданы. Идёт выставление на продажу ваших NFT...")
        await asyncio.sleep(10)
        await put_nft_on_sale(nft_collection_address, poster_amount, fin_data['price_ton'], user_info["wallet"])

        delete_file(data.get('photo_path'))
        await transfer_ownership(nft_collection_address, user_info["wallet"])
        await wait_for_seqno()
        poster_data_rez = await send_poster(nft_collection_address)
        if poster_data_rez:
            await call.message.answer(
                f"Все готово! Ваш NFT готов к продажам. Вы можете найти его в вашем аккаунте "
                f"Posterstock. Ссылка: {poster_data_rez}", reply_markup=main_kb())
    else:
        await call.answer(f'Вы выбрали {call.data}')
        await call.message.answer('Сценарий по добавлению постера остановлен. Все данные очищены.',
                                  reply_markup=main_kb())
    await state.clear()
