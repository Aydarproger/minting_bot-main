# Описание запука на VPS сервере

1. Устанавливаем Docker и Make
2. Закидываем в корень проекта .env файл
3. Загружаем все файлы бота в дирректорию бота на VPS
4. Создаем Docker образ бота: docker build -t ton_bot_image .
5. Выполняем команду: make run