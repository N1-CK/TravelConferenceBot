import asyncio
import importlib
import sys
import types
import unittest
from unittest.mock import patch

from utility.telegram_files import telegram_download_name


class ChatRoutingTests(unittest.TestCase):
    def test_department_heading_on_first_reply_and_switch(self):
        fake_db = types.SimpleNamespace(
            get_chat_department=lambda uid: self.value('pr'),
            get_last_outgoing_department=lambda uid: self.value(self.previous),
        )
        async def translate(uid, key, **kwargs):
            return f"Из отдела {kwargs['department']}"

        with patch.dict(sys.modules, {
            'database': types.SimpleNamespace(db=fake_db),
            'utility.lang_utils': types.SimpleNamespace(t=translate),
        }):
            sys.modules.pop('utility.chat_routing', None)
            routing = importlib.import_module('utility.chat_routing')
            self.previous = None
            self.assertEqual(asyncio.run(routing.prepare_department_message(1, 'pr', 'Привет')),
                             'Из отдела PR\n\nПривет')
            self.previous = 'pr'
            self.assertEqual(asyncio.run(routing.prepare_department_message(1, 'pr', 'Ещё раз')),
                             'Ещё раз')
            self.assertEqual(asyncio.run(routing.prepare_department_message(1, 'travel', 'Рейс')),
                             'Из отдела TRAVEL\n\nРейс')
            sys.modules.pop('utility.chat_routing', None)

    @staticmethod
    async def value(result):
        return result

    def test_two_extensionless_photos_have_distinct_jpg_names(self):
        first = telegram_download_name('photos/file_1', 'photo-id-1', b'\xff\xd8\xffimage')
        second = telegram_download_name('photos/file_1', 'photo-id-2', b'\xff\xd8\xffimage')
        self.assertTrue(first.endswith('.jpg'))
        self.assertTrue(second.endswith('.jpg'))
        self.assertNotEqual(first, second)
        self.assertEqual(telegram_download_name('photos/file_2.png', 'id', b'PNG'), 'file_2.png')


if __name__ == '__main__':
    unittest.main()
