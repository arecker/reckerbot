import unittest

from reckerbot import Message


class TestMessage(unittest.TestCase):
    def test_is_direct_message(self):
        actual = Message(data={'channel': 'D0120K8DHQX'}).is_direct_message()
        self.assertEqual(actual, True)
        actual = Message(data={'channel': 'C012MGSMG5S'}).is_direct_message()
        self.assertEqual(actual, False)


if __name__ == '__main__':
    unittest.main()
