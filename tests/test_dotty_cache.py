# encoding: utf-8

# SNAGED FROM https://github.com/pawelzny/dotty_dict/blob/98984911a61ae9f1aa4da3f6c4808da991b89847/tests/test_dotty_cache.py
# UNDER THe MIT LICENSE

import unittest
from unittest.mock import MagicMock

from mo_dots import to_data


class TestDottyCache(unittest.TestCase):

    def test_getitem_cache(self):
        dot = to_data()
        dot._data = MagicMock()
        for _ in range(10):
            dot.get('x.y.z')
        self.assertEqual(dot.__getitem__.cache_info().hits, 9)
