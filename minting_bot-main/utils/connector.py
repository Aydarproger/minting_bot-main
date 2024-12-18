from pytonconnect import TonConnect
from pytonconnect.storage import FileStorage
from create_bot import MANIFEST_URL

storage = {}


class TcStorage(FileStorage):

    def __init__(self, chat_id: int):
        super().__init__(f'./connections/{chat_id}.json')
        self.chat_id = chat_id

    # def _get_key(self, key: str):
    #     return str(self.chat_id) + key

    # async def set_item(self, key: str, value: str):
    #     storage[self._get_key(key)] = value

    # async def get_item(self, key: str, default_value: str = None):
    #     return storage.get(self._get_key(key), default_value)

    # async def remove_item(self, key: str):
    #     storage.pop(self._get_key(key))


def get_connector(chat_id: int):
    return TonConnect(MANIFEST_URL, storage=TcStorage(chat_id))
