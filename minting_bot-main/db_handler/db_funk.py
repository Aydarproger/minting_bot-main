import aiosqlite
from create_bot import logger


async def create_db(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                login TEXT,
                full_name TEXT,
                verified TEXT,
                wallet TEXT UNIQUE, -- Уникальное значение, допускающее NULL
                sms_code INTEGER,
                ps_login TEXT
            )
        ''')
        await db.commit()


async def create_posters_table(db_path: str, table_name: str):
    try:
        async with aiosqlite.connect(db_path) as db:
            create_table_query = f'''
                CREATE TABLE IF NOT EXISTS {table_name} (
                    telegram_id TEXT,
                    film_id INTEGER,
                    film_type TEXT,
                    film_title TEXT,
                    film_start_year INTEGER,
                    film_end_year INTEGER,
                    film_main_poster TEXT,
                    poster_name_user_type TEXT,
                    poster_lang TEXT,
                    photo_path TEXT,
                    poster_count INTEGER,
                    price_ton REAL,
                    poster_description TEXT,
                    pin_hash TEXT,
                    pin_size TEXT,
                    pin_address TEXT
                )
            '''
            logger.debug(f'Creating table with query: {create_table_query}')
            await db.execute(create_table_query)
            await db.commit()
            logger.info(f"Table {table_name} successfully created.")
    except Exception as e:
        logger.error(f"Error while creating {table_name} table: {e}")


async def add_user(db_path: str, table_name: str, user_data: dict):
    async with aiosqlite.connect(db_path) as db:
        columns = ', '.join(user_data.keys())
        placeholders = ', '.join(['?' for _ in user_data.values()])
        values = list(user_data.values())

        await db.execute(f'''
            INSERT INTO {table_name} ({columns}) 
            VALUES ({placeholders})
        ''', values)
        await db.commit()


async def get_user_by_telegram_id(db_path: str, telegram_id: int):
    try:
        async with aiosqlite.connect(db_path) as db:
            # Установка формата результата как aiosqlite.Row
            db.row_factory = aiosqlite.Row

            query = 'SELECT * FROM users WHERE telegram_id = ?'
            logger.debug(f'Executing query: {query} with telegram_id: {telegram_id}')
            cursor = await db.execute(query, (telegram_id,))
            row = await cursor.fetchone()

            if row is None:
                logger.info(f'No user found with telegram_id: {telegram_id}')
                return None
            else:
                # Преобразование строки в словарь
                user = dict(row)
                logger.info(f'User found: {user}')
                return user
    except Exception as e:
        logger.error(f'An error occurred: {e}')
        return None


async def is_wallet_unique(db_path: str, wallet: str):
    try:
        async with aiosqlite.connect(db_path) as db:
            # Установка формата результата как aiosqlite.Row
            db.row_factory = aiosqlite.Row

            query = 'SELECT * FROM users WHERE wallet = ?'
            logger.debug(f'Executing query: {query} with wallet: {wallet}')
            cursor = await db.execute(query, (wallet,))
            row = await cursor.fetchone()

            if row is None:
                logger.info(f'Wallet {wallet} is unique.')
                return True
            else:
                logger.info(f'Wallet {wallet} already exists in the database.')
                return False
    except Exception as e:
        logger.error(f'An error occurred: {e}')
        return False


async def delete_user_by_telegram_id(db_path: str, telegram_id: int):
    try:
        async with aiosqlite.connect(db_path) as db:
            query = 'DELETE FROM users WHERE telegram_id = ?'
            logger.debug(f'Executing query: {query} with telegram_id: {telegram_id}')
            await db.execute(query, (telegram_id,))
            await db.commit()

            logger.info(f'User with telegram_id {telegram_id} has been deleted from the database.')
            return True
    except Exception as e:
        logger.error(f'An error occurred while deleting user: {e}')
        return False


async def update_user(db_path: str, user_data: dict):
    print(user_data)
    async with aiosqlite.connect(db_path) as db:
        # Извлечение имен столбцов и значений из словаря
        columns = ', '.join(f'{key} = ?' for key in user_data.keys() if key != 'telegram_id')
        values = [value for key, value in user_data.items() if key != 'telegram_id']
        values.append(int(user_data['telegram_id']))  # Добавление telegram_id в конец списка значений

        # Формирование SQL-запроса
        query = f'''
            UPDATE users SET {columns} WHERE telegram_id = ?
        '''
        logger.debug(f'Executing query: {query} with values: {values}')

        # Выполнение запроса
        await db.execute(query, values)
        await db.commit()


async def add_poster(db_path: str, table_name: str, poster_data: dict):
    try:
        async with aiosqlite.connect(db_path) as db:
            columns = ', '.join(poster_data.keys())
            placeholders = ', '.join(['?' for _ in poster_data.values()])
            values = list(poster_data.values())

            query = f'''
                INSERT INTO {table_name} ({columns}) 
                VALUES ({placeholders})
            '''
            logger.debug(f'Executing query: {query} with values: {values}')
            await db.execute(query, values)
            await db.commit()
            logger.info(f"Poster successfully added to {table_name} table.")
    except Exception as e:
        logger.error(f"Error while adding poster to {table_name} table: {e}")


async def get_user_film_ids(db_path: str, telegram_id: int):
    try:
        async with aiosqlite.connect(db_path) as db:
            # Установка формата результата как aiosqlite.Row
            db.row_factory = aiosqlite.Row

            query = 'SELECT film_id FROM posters WHERE telegram_id = ?'
            logger.debug(f'Executing query: {query} with telegram_id: {telegram_id}')
            cursor = await db.execute(query, (telegram_id,))
            rows = await cursor.fetchall()

            # Извлечение всех значений film_id в список
            film_ids = [row['film_id'] for row in rows]

            logger.info(f'Film IDs for user {telegram_id}: {film_ids}')
            return film_ids
    except Exception as e:
        logger.error(f'An error occurred while retrieving film_ids for user {telegram_id}: {e}')
        return []