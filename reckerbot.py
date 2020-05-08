'''
reckerbot, the greatest slackbot ever made
'''

__version__ = '0.17.0'

import asyncio
import collections
import functools
import json
import logging
import os
import platform
import re
import ssl
import sys

import certifi
import slack

here = os.path.dirname(os.path.realpath(__file__))


def wrap_in_fences(txt):
    return f'```\n{txt}\n```'


ParsedArgs = collections.namedtuple(
    'ParsedArgs',
    'command subcommand args'
)


def parse_args(message):
    words = [w.strip() for w in message.split(' ') if w]
    p_username = re.compile('^<@*.+>$')
    p_emoji = re.compile('^:[A-Za-z_-]+:$')
    words = [w for w in words if not p_username.match(w)]
    words = [w for w in words if not p_emoji.match(w)]
    try:
        command = words.pop(0).lower()
    except IndexError:
        command = None
    try:
        subcommand = words.pop(0).lower()
    except IndexError:
        subcommand = None
    args = [w.strip() for w in ' '.join(words).split(',') if w]
    return ParsedArgs(command, subcommand, args)


# logger
logger = logging.getLogger('reckerbot')
_log_handler = logging.StreamHandler(stream=sys.stdout)
_log_formatter = logging.Formatter(fmt='{name}: {message}', style='{')
_log_handler.setFormatter(_log_formatter)
logger.addHandler(_log_handler)
logger.setLevel(level=logging.INFO)


class TokenLoader:
    def __init__(self, secrets_dir=os.path.join(here, 'secrets')):
        self.secrets_dir = secrets_dir

    @functools.cached_property
    def data(self):
        default_path = os.path.join(self.secrets_dir, 'reckerbot.json')
        path = os.environ.get('TOKEN_PATH', default_path)
        logger.info('reading secrets from %s', path)
        with open(path) as f:
            return json.load(f)

    @property
    def token(self):
        return self.data['token']


token_loader = TokenLoader()


class UserLookup(collections.UserDict):
    def __init__(self):
        self.data = {}

    async def populate(self, client):
        if self.data:
            return

        logger.info('fetching member info')
        response = await client.users_list()
        for user in response.data['members']:
            if user['deleted']:
                continue

            self.data[user['name']] = user['id']


user_lookup = UserLookup()


class Message:
    # https://api.slack.com/events/message

    def __init__(self, data, client=None):
        self.data = data
        self.client = client

    @functools.cached_property
    def user(self):
        try:
            return self.data['user']
        except KeyError:
            return self.data['bot_id']

    @property
    def text(self):
        return self.data['text']

    @property
    def subtype(self):
        return self.data.get('subtype')

    def is_from_slackbot(self):
        return self.data.get('user') == 'USLACKBOT'

    def is_from_bot(self):
        return 'bot_id' in self.data

    def is_channel_join(self):
        return self.subtype == 'channel_join'

    def is_edit(self):
        return self.subtype == 'message_changed'

    def is_direct_message(self):
        return self.data['channel'].startswith('D')

    def mentions_reckerbot(self):
        reckerbot_id = user_lookup['reckerbot']
        return f'<@{reckerbot_id}>' in self.text

    def truncate(self, max=30):
        try:
            if len(self.text) > max:
                return self.text[:max] + '...'
            else:
                return self.text
        except KeyError:
            return self.subtype

    @property
    def post_args(self):
        args = {
            'as_user': True,
        }

        if self.channel.startswith('D'):
            args['channel'] = self.data['user']
        else:
            args['channel'] = self.channel

        return args

    @property
    def channel(self):
        return self.data['channel']

    def reply(self, text):
        self.client.chat_postMessage(text=text, **self.post_args)

    def sorry(self):
        text = 'Ope!  Something broke while trying to respond.'
        self.client.chat_postMessage(text=text, **self.post_args)

    def __repr__(self):
        return f'<Message "{self.truncate()}">'


class Module:
    aliases = []
    default = 'help'

    # If a list of usernames, limit this module to these users.
    allowed_user_names = []

    @functools.cached_property
    def allowed_users(self):
        return [user_lookup[u] for u in self.allowed_user_names]

    @property
    def command(self):
        name = type(self).__name__
        return re.sub('Module$', '', name).lower()

    @property
    def shortcut(self):
        return self.command[0]

    @property
    def matching_commands(self):
        return [self.shortcut, self.command] + self.aliases

    @property
    def subcommands(self):
        attrs = [a for a in dir(self) if a.startswith('cmd_')]
        methods = [m for m in attrs if hasattr(getattr(self, m), '__call__')]
        subcmds = [m[4:] for m in methods]
        subcmds.remove('help')
        return subcmds + ['help']

    @property
    def help_entry(self):
        return f'{self.command} ({self.shortcut}) - {self.__doc__.strip()}'

    def _read_doc_string(self, method):
        return getattr(self, method).__doc__.strip()

    def cmd_help(self, args=[], msg='Here are the available commands:'):
        '''
        Print these instructions.
        '''
        entries = []

        for cmd in self.subcommands:
            doc = self._read_doc_string(f'cmd_{cmd}')
            entries.append(f'{cmd} - {doc}')

        entries = '\n'.join(entries)

        return f'{msg}\n{wrap_in_fences(entries)}'

    def subcommand_function(self, name):
        return getattr(self, f'cmd_{name}')

    def matches(self, args):
        return args.command in self.matching_commands

    def is_allowed(self, user=None):
        if not self.allowed_user_names:
            return True

        return user in self.allowed_users

    def handle(self, args, user=None):
        if user and not self.is_allowed(user):
            return f'''
I am sorry!  You are not allowed to run the "{self.command}" commmand!
            '''.strip()

        subcommand = args.subcommand or self.default

        if subcommand not in self.subcommands:
            msg = f'Not sure what "{args.command} {subcommand}" means!'
            return self.cmd_help(msg=msg)

        return self.subcommand_function(subcommand)(args=args.args)


class GroceriesModule(Module):
    '''
    View and modify the grocery list.
    '''
    default = 'list'
    allowed_user_names = ['alex', 'marissa']  # TODO: lol hard code

    @property
    def save_target(self):
        target = os.path.join(here, 'data/groceries.json')

        if not os.path.exists(target):
            with open(target, 'w') as f:
                json.dump([], f)

        return target

    def to_grocery_list(self, array):
        return ''.join(['- ' + item + '\n' for item in array])

    def cmd_list(self, args=[]):
        '''
        List the current items in the grocery list.
        '''
        with open(self.save_target, 'r') as f:
            body = self.to_grocery_list(json.load(f))

        if body:
            return f'Here is the current grocery list!\n{body}'
        else:
            return 'The grocery list is currently empty!'

    def cmd_add(self, args=[]):
        '''
        Add items to the grocery list, if they're not already there.
        '''
        new = list(set([i.lower().strip() for i in args]))
        with open(self.save_target, 'r') as f:
            existing = json.load(f)

        these = [i for i in new if i not in existing]

        if not these:
            return 'all of that is covered - nothing to add!'

        logger.info('adding %s to groceries', these)
        with open(self.save_target, 'w') as f:
            json.dump(existing + these, f)

        return f'added {these} to groceries'

    def cmd_delete(self, args=[]):
        '''
        Delete items from the grocery list, if they're listed.
        '''
        with open(self.save_target, 'r') as f:
            items = json.load(f)

        deleted = [items.pop(items.index(i)) for i in args if i in items]

        with open(self.save_target, 'w') as f:
            json.dump(items, f)

        return f'Done!  Deleted {deleted}'

    def cmd_clear(self, args=[]):
        '''
        Delete everything on the grocery list.
        '''
        with open(self.save_target, 'w') as f:
            json.dump([], f)
        return 'grocery list cleared!'


class HelpModule(Module):
    '''
    Print all available module commands
    '''
    def matches(self, *args, **kwargs):
        return True

    def cmd_help(self, args=[], msg='Here are all of my available modules:'):
        entries = wrap_in_fences('\n'.join([m.help_entry for m in modules]))
        return f'{msg}\n{entries}'

    def handle(self, args, **kwargs):
        if not args.command:
            return self.cmd_help()

        if not any([args.command in m.matching_commands for m in modules]):
            msg = f'Not sure what "{args.command}" means, ' + '''
            but here are all my available modules:
            '''.strip()
            return self.cmd_help(msg=msg)

        return super(HelpModule, self).handle(args, **kwargs)


modules = [
    GroceriesModule(),
    HelpModule(),
]


def find_module(args):
    return next((m for m in modules if m.matches(args)))


@slack.RTMClient.run_on(event='message')
async def on_message(web_client=None, data={}, **kwargs):
    await user_lookup.populate(web_client)

    message = Message(data=data, client=web_client)

    try:
        if message.is_channel_join():
            logger.info('message %s is just a channel join, ignoring', message)
            return

        if message.is_edit():
            logger.info('message %s is just an edit, ignoring', message)
            return

        if message.is_from_bot() or message.is_from_slackbot():
            logger.info('ignoring message from bot "%s"', message)
            return

        if not (message.is_direct_message() or message.mentions_reckerbot()):
            logger.info('ignoring message not for reckerbot "%s"', message)
            return

        args = parse_args(message.text)
        logger.info('parsed "%s" to %s', message, args)
        module = find_module(args)
        logger.info('routing %s to %s', args, module)
        message.reply(module.handle(args, user=message.user))
    except Exception:
        logger.error(data, exc_info=True)
        message.sorry()


def main():
    logger.info(
        'starting reckerbot v%s, Python %s',
        __version__, platform.python_version()
    )
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    slack_token = token_loader.token
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    rtm_client = slack.RTMClient(
        token=slack_token,
        ssl=ssl_context,
        run_async=True,
        loop=loop
    )
    logger.info('opening RTM session')
    loop.run_until_complete(rtm_client.start())


if __name__ == '__main__':
    main()
