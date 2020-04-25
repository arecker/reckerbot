import unittest

from reckerbot import wrap_in_fences


class TestFunctions(unittest.TestCase):
    def test_wrap_in_fences(self):
        actual = wrap_in_fences('testing')
        expected = '```\ntesting\n```'
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
