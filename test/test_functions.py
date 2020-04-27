import unittest

from reckerbot import wrap_in_fences, parse_args


class TestFunctions(unittest.TestCase):
    def test_wrap_in_fences(self):
        actual = wrap_in_fences('testing')
        expected = '```\ntesting\n```'
        self.assertEqual(actual, expected)

    def test_parse_args(self):
        actual = parse_args('hello greet Alex, Marissa, Rodney')
        self.assertEqual(actual.command, 'hello')
        self.assertEqual(actual.subcommand, 'greet')
        self.assertEqual(actual.args, ['Alex', 'Marissa', 'Rodney'])

        actual = parse_args('<@UASDF123> :hello: hello greet Alex,')
        self.assertEqual(actual.command, 'hello')
        self.assertEqual(actual.subcommand, 'greet')
        self.assertEqual(actual.args, ['Alex'])


if __name__ == '__main__':
    unittest.main()
