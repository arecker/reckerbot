import functools
import logging
import os
import sys
import traceback

import slack

here = os.path.dirname(os.path.realpath(__file__))


class SlackLogHandler(logging.Handler):
    def __init__(self, *args, token='', **kwargs):
        self.token = token
        super(*args, **kwargs)

    @functools.cached_property
    def client(self):
        return slack.WebClient(token=self.token)

    def wrap_in_fences(self, txt):
        return f'```\n{txt}\n```'

    def emit(self, record):
        text = record.getMessage()

        if record.exc_info:
            stacktrace = traceback.format_exc()
            text += f'\n{self.wrap_in_fences(stacktrace)}'

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


@slack.RTMClient.run_on(event='message')
def reply(**payload):
    logger.info(payload)
    try:
        int('fish')
    except Exception as e:
        logger.error(e, exc_info=True)


def main():
    logger.info('starting reckerbot')
    token_loader = TokenLoader()

    logger.info('adding slack logging handler')
    handler = SlackLogHandler(token=token_loader.web_token)
    handler.setLevel(logging.ERROR)
    handler.setFormatter(_log_formatter)
    logger.addHandler(handler)

    logger.info('opening RTM session')
    client = slack.RTMClient(token=token_loader.rtm_token)
    client.start()


if __name__ == '__main__':
    main()
