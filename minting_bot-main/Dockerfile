FROM python:3.12

ENV USER_NAME=nobody \
   USER_UID=65534 \
   WORKDIR=/usr/src/app

WORKDIR $WORKDIR

# Копируем и устанавливаем зависимости Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы из текущей директории в рабочую директорию контейнера
COPY . .

RUN chown -R $USER_UID:0 $WORKDIR && \
    chmod -R ug+rwx $WORKDIR

# Команда запуска контейнера
CMD ["/bin/bash", "-c", "python aiogram_run.py"]