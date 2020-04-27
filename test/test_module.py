import unittest

from reckerbot import Module


class HelloModule(Module):
    '''
    Use the hello module to receive a warm greeting.
    '''
    aliases = ['hi']

    def cmd_greet(self, name):
        '''
        Reply to `{name}` with a nice greeting.
        '''
        return 'Why hello there, f{name}!'


class TestModule(unittest.TestCase):
    def setUp(self):
        self.m = HelloModule()

    def test_command(self):
        self.assertEqual(self.m.command, 'hello')

    def test_shortcut(self):
        self.assertEqual(self.m.shortcut, 'h')

    def test_matching_commands(self):
        self.assertEqual(self.m.matching_commands, ['h', 'hello', 'hi'])

    def test_subcommands(self):
        self.assertEqual(self.m.subcommands, ['greet', 'help'])

    def test_default(self):
        self.assertEqual(self.m.default, 'help')

    def test_cmd_help(self):
        expected = '''
Here are the available commands:
greet - Reply to `{name}` with a nice greeting.
help - Print these instructions.
        '''.strip()
        self.assertEqual(self.m.cmd_help(), expected)

    def test_parse_args(self):
        actual = self.m.parse_args('hello greet Alex, Marissa, Rodney')
        self.assertEqual(actual.command, 'hello')
        self.assertEqual(actual.subcommand, 'greet')
        self.assertEqual(actual.args, ['Alex', 'Marissa', 'Rodney'])

        actual = self.m.parse_args('hello')
        self.assertEqual(actual.command, 'hello')
        self.assertEqual(actual.subcommand, 'help')
        self.assertEqual(actual.args, [])


if __name__ == '__main__':
    unittest.main()
