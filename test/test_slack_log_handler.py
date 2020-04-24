import unittest

from reckerbot import SlackLogHandler


class TestSlackLogHandler(unittest.TestCase):
    def test_wrap_in_fences(self):
        handler = SlackLogHandler()
        actual = handler.wrap_in_fences('testing')
        expected = '```\ntesting\n```'
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
