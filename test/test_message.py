import unittest

from reckerbot import Message


class TestMessage(unittest.TestCase):
    def test_as_command(self):
        actual = Message(response={
            'data': {
                'text': '<@UASDF123> :smiley_face: gRoCeries  '
            }
        }).as_command()
        expected = 'groceries', []
        self.assertEqual(actual, expected)

        actual = Message(response={
            'data': {
                'text': '<@UASDF123> :smiley_face: GROCERIES  list something'
            }
        }).as_command()
        expected = 'groceries', ['list', 'something']
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
