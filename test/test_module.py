import unittest

from reckerbot import Module


class HelloModule(Module):
    '''
    receive warm greetings from a computer.
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

    def test_help_entry(self):
        expected = 'hello (h) - receive warm greetings from a computer.'
        self.assertEqual(self.m.help_entry, expected)

    def test_cmd_help(self):
        expected = '''
Here are the available commands:
```
greet - Reply to `{name}` with a nice greeting.
help - Print these instructions.
```
        '''.strip()
        self.assertEqual(self.m.cmd_help(), expected)


if __name__ == '__main__':
    unittest.main()
