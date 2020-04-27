import argparse
import functools
import getpass
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


class User:
    def __init__(self, name=None, id=None):
        self._id = id
        self._name = name

    def as_member_filter(self):
        filters = {}

        if self._id:
            filters['id'] = self._id
        if self._name:
            filters['name'] = self._name

        if not filters:
            raise ValueError('cannot identify user without a name or id')

        filters['deleted'] = False

        return filters

    def as_mention(self):
        return f'<@{self.id}>'

    @functools.cached_property
    def client(self):
        return slack.WebClient(token=token_loader.web_token)

    @functools.cached_property
    def identity(self):
        filters = self.as_member_filter()
        logger.info('fetching identity for user %s', filters)
        members = self.client.users_list().data['members']
        try:
            return next(filter(lambda m: filters.items() <= m.items(), members))
        except StopIteration:
            raise ValueError(f'could not find user that satisfies: {filters}')

    @property
    def name(self):
        if not self._name:
            self._name = self.identity['name']
        return self._name

    @property
    def id(self):
        if not self._id:
            self._id = self.identity['id']
        return self._id

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return f'<User {self.name}>'


reckerbot = User(name='reckerbot')


class Message:
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

    def as_command(self):
        words = self.text.split(' ')
        words = [w.strip() for w in self.text.split(' ') if w]
        p_username = re.compile('^<@*.+>$')
        p_emoji = re.compile('^:[A-Za-z_-]+:$')
        words = [w for w in words if not p_username.match(w)]
        words = [w for w in words if not p_emoji.match(w)]
        words = [w.lower() for w in words]
        return words[0], words[1:]

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


class DefaultHandler:
    replies = [
        '''Hey {user}!  I saw you mentioned me, but I'm not sure what I'm supposed to do? :thinking_face:''',
        '''{user} - you rang?''',
        '''And what I'm I supposed to do now, {user}?''',
        '''Hi {user}.  I don't know what you want, so I'll just assume you want attention.''',
        '''{user}? ¯\_(ツ)_/¯''',
        '''What can I do for you, {user}?''',
    ]

    def handle(self, *args, **kwargs):
        return random.choice(self.replies)


class GroceriesHandler:
    subcommands = ['add', 'list', 'clear', 'delete', 'help']

    @property
    def save_target(self):
        return os.path.join(here, 'data/groceries.json')

    def to_grocery_list(self, array):
        return ''.join(['- ' + item + '\n' for item in array])

    def help(self):
        body = wrap_in_fences(self.parser.format_help())
        return f'I didn\'t understand the command :confused:\n{body}'.strip()

    def list(self):
        with open(self.save_target, 'r') as f:
            body = self.to_grocery_list(json.load(f))

        return f'Here is the current grocery list!\n{body}'

    def add(self, items=[]):
        new = [i.lower().strip() for i in items]
        with open(self.save_target, 'r') as f:
            existing = json.load(f)

        these = [i for i in new if i not in existing]

        if not these:
            return 'all of that is covered - nothing to add!'

        logger.info('adding %s to groceries', these)
        with open(self.save_target, 'w') as f:
            json.dump(existing + these, f)

        return f'added {these} to groceries'

    def delete(self, items=[]):
        return f'normally I would delete {items}, but I cannot do that yet!'

    def clear(self):
        return 'normamly I would clear the grocery list, but I cannot do that yet!'

    def handle(self, args=[]):
        try:
            args = self.parse_args(args)
            if args.action == 'list':
                return self.list()
            elif args.action == 'add':
                return self.add(items=args.items)
            elif args.action == 'delete':
                return self.delete(items=args.items)
            elif args.action == 'clear':
                return self.clear()
            else:
                return self.help()
        except SystemExit:
            return self.help()

    @functools.cached_property
    def parser(self):
        parser = argparse.ArgumentParser(
            prog='groceries',
            description='manage the grocery list'
        )
        parser.add_argument(
            'action', default='list',
            choices=self.subcommands,
            nargs='?', const=1, type=str
        )
        parser.add_argument(
            'items', nargs='*',
        )
        return parser

    def parse_args(self, args):
        return self.parser.parse_args(args)


shortcuts = {
    'g': 'groceries',
}

handlers = {
    'default': DefaultHandler(),
    'groceries': GroceriesHandler()
}


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

        command, args = message.as_command()
        command = shortcuts.get(command, command)

        try:
            handler = handlers[command]
        except KeyError:
            logger.info('falling back to default for "%s"', message.truncate())
            message.reply(handlers['default'].handle())
            return

        logger.info('routing "%s %s" to handler', command, args)
        message.reply(handler.handle(args=args))

    except Exception as e:
        logger.error(e, exc_info=True)


def parse_root_args():
    parser = argparse.ArgumentParser(prog='reckerbot', description='the greatest slackbot ever made')
    parser.add_argument('action', choices=list(handlers.keys()) + ['serve'])
    parser.add_argument('args', nargs='*')
    return parser.parse_args()


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
    args = parse_root_args()
    if args.action == 'serve':
        serve()
    else:
        output = handlers[args.action].handle(args=args.args)
        output = output.replace('{user}', getpass.getuser()).strip()
        print(output)


if __name__ == '__main__':
    main()
