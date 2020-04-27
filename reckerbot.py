import collections
import functools
import json
import logging
import os
import random
import re
import sys
import traceback

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
    command = words.pop(0)
    try:
        subcommand = words.pop(0)
    except IndexError:
        subcommand = None
    args = [w.strip() for w in ' '.join(words).split(',') if w]
    return ParsedArgs(command, subcommand, args)


class SlackLogHandler(logging.Handler):
    def __init__(self, *args, token='', **kwargs):
        self.token = token
        super(SlackLogHandler, self).__init__(*args, **kwargs)

    @functools.cached_property
    def client(self):
        return slack.WebClient(token=self.token)

    def emit(self, record):
        if record.exc_info:
            stacktrace = wrap_in_fences(traceback.format_exc().strip())
            text = f'{stacktrace}'
        else:
            text = record.getMessage()

        self.client.chat_postMessage(channel='#debug', text=text)


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

    def read_token(self, token_type):
        default_path = self.to_token_path(token_type)
        env_key = self.to_env_key(token_type)
        path = os.environ.get(env_key, default_path)
        logger.info('reading %s token from %s', token_type, path)
        with open(path, 'r') as f:
            return f.read().strip()

    def to_env_key(self, token_type):
        return f'{token_type.upper()}_TOKEN_PATH'

    def to_token_path(self, token_type):
        return os.path.join(self.secrets_dir, f'{token_type}-token')

    @functools.cached_property
    def rtm_token(self):
        return self.read_token('rtm')

    @functools.cached_property
    def web_token(self):
        return self.read_token('web')


token_loader = TokenLoader()


class UserLookup:
    @functools.cached_property
    def client(self):
        return slack.WebClient(token=token_loader.web_token)

    @functools.cached_property
    def members(self):
        logger.info('fetching member info')
        return self.client.users_list().data['members']

    @property
    def active_members(self):
        yield from filter(lambda m: not m['deleted'], self.members)

    def id_by_name(self, name):
        try:
            return next((m['id'] for m in self.active_members if m['name'] == name))
        except StopIteration:
            raise ValueError(f'no user with name "{name}"')

    def name_by_id(self, id):
        try:
            return next((m['name'] for m in self.active_members if m['id'] == id))
        except StopIteration:
            raise ValueError(f'no user with id "{id}"')


user_lookup = UserLookup()


class User:
    def __init__(self, name=None, id=None):
        self._id = id
        self._name = name

    def as_mention(self):
        return f'<@{self.id}>'

    @functools.cached_property
    def client(self):
        return slack.WebClient(token=token_loader.web_token)

    @property
    def name(self):
        if not self._name:
            self._name = user_lookup.name_by_id(self._id)
        return self._name

    @property
    def id(self):
        if not self._id:
            self._id = user_lookup.id_by_name(self._name)
        return self._id

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return f'<User {self.name}>'


reckerbot = User(name='reckerbot')


class Message:
    # https://api.slack.com/events/message
    def __init__(self, response):
        self.web_client = response.get('web_client')
        self.rtm_client = response.get('rtm_client')
        self.data = response['data']

    @functools.cached_property
    def user(self):
        try:
            return User(id=self.data['user'])
        except KeyError:
            return User(id=self.data['bot_id'])

    @property
    def text(self):
        return self.data['text']

    def is_from_bot(self):
        return self.data.get('subtype') == 'bot_message'

    def mentions_reckerbot(self):
        return reckerbot.as_mention() in self.text

    def truncate(self, max=30):
        if len(self.text) > max:
            return self.text[:max] + '...'
        else:
            return self.text

    @property
    def post_args(self):
        return {
            'channel': self.channel,
        }

    @property
    def channel(self):
        return self.data['channel']

    def reply(self, message):
        text = message.replace('{user}', self.user.as_mention())
        reckerbot.client.chat_postMessage(text=text, **self.post_args)

    def __repr__(self):
        return f'<Message "{self.truncate()}">'


class Module:
    aliases = []
    default = 'help'

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

    def _read_doc_string(self, method):
        return getattr(self, method).__doc__.strip()

    def cmd_help(self, args=[], msg='Here are the available commands:'):
        '''
        Print these instructions.
        '''
        for cmd in self.subcommands:
            doc = self._read_doc_string(f'cmd_{cmd}')
            msg += f'\n{cmd} - {doc}'

        return msg.strip()

    def subcommand_function(self, name):
        return getattr(self, f'cmd_{name}')

    def matches(self, args):
        return args.command in self.matching_commands

    def handle(self, args):
        subcommand = args.subcommand or self.default

        if subcommand not in self.subcommands:
            msg = f'Not sure what "{subcommand}" means!'
            return self.cmd_help(msg=msg)

        return self.subcommand_function(subcommand)(args=args.args)


class GroceriesModule(Module):
    '''
    View and modify the grocery list.
    '''
    default = 'list'

    @property
    def save_target(self):
        return os.path.join(here, 'data/groceries.json')

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
        Add `{args}` to the grocery list, if they're not already there.
        '''
        new = [i.lower().strip() for i in args]
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
        Delete `{args}` from the grocery list, if they're listed.
        '''
        return f'normally I would delete {args}, but I cannot do that yet!'

    def cmd_clear(self, args=[]):
        '''
        Delete everything on the grocery list.
        '''
        with open(self.save_target, 'w') as f:
            json.dump([], f)
        return 'grocery list cleared!'


class DefaultModule(Module):
    '''
    Garner some mild shame from reckerbot for typing a nonexistent command.
    '''
    default = 'random'

    replies = [
        '''Hey {user}!  I saw you mentioned me, but I'm not sure what I'm supposed to do? :thinking_face:''',
        '''{user} - you rang?''',
        '''And what I'm I supposed to do now, {user}?''',
        '''Hi {user}.  I don't know what you want, so I'll just assume you want attention.''',
        '''{user}? ¯\_(ツ)_/¯''',
        '''What can I do for you, {user}?''',
    ]

    def matches(self, cmd):
        return True

    def cmd_random(self, args=[]):
        '''
        Hear a random phrase which communicates how lost you are.
        '''
        return random.choice(self.replies)


modules = [
    GroceriesModule(),
    DefaultModule(),
]


@slack.RTMClient.run_on(event='message')
def on_message(**payload):
    message = Message(response=payload)

    try:
        if message.is_from_bot():
            logger.info('ignoring message from bot "%s"', message.truncate())
            return

        if not message.mentions_reckerbot():
            logger.info('ignoring message not for reckerbot "%s"', message.truncate())
            return

        args = parse_args(message.text)
        logger.info('parsed "%s" to %s', message.truncate(), args)

        module = next((m for m in modules if m.matches(args)))
        output = module.handle(args)
        message.reply(output)
    except Exception as e:
        logger.error(e, exc_info=True)


def serve():
    logger.info('starting reckerbot')

    logger.info('adding slack logging handler')
    handler = SlackLogHandler(token=token_loader.web_token)
    handler.setLevel(logging.ERROR)
    handler.setFormatter(_log_formatter)
    logger.addHandler(handler)

    logger.info('opening RTM session')
    client = slack.RTMClient(token=token_loader.rtm_token)
    client.start()


def main():
    args = parse_args(' '.join(sys.argv[1:]))

    if args.command == 'serve':
        serve()
    else:
        module = next((m for m in modules if m.matches(args)))
        print(module.handle(args))


if __name__ == '__main__':
    main()
