import unittest

from reckerbot import wrap_in_fences, parse_args, order_by_list


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

        actual = parse_args('G List')
        self.assertEqual(actual.command, 'g')
        self.assertEqual(actual.subcommand, 'list')

    def test_order_by_list(self):
        expected = ['a', 'd', 'e', 'b']
        actual = order_by_list(
            ['b', 'a', 'd', 'e'],
            ['a', 'c', 'd', 'e']
        )
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
