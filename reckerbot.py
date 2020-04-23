import functools
import logging
import os
import sys
import traceback

import slack

here = os.path.dirname(os.path.realpath(__file__))


class SlackLogHandler(logging.Handler):
    @functools.cached_property
    def client(self):
        return slack.WebClient(token=WEB_TOKEN)

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


def read_token(token_type):
    default_path = os.path.join(here, f'secrets/{token_type}-token')
    env_key = f'{token_type.upper()}_TOKEN_PATH'
    path = os.environ.get(env_key, default_path)
    logger.info('reading %s token from %s', token_type, path)
    with open(path, 'r') as f:
        return f.read().strip()


RTM_TOKEN, WEB_TOKEN = read_token('rtm'), read_token('web')


@slack.RTMClient.run_on(event='message')
def reply(**payload):
    logger.info(payload)
    try:
        int('fish')
    except Exception as e:
        logger.error(e, exc_info=True)


def main():
    logger.info('starting reckerbot')

    logger.info('adding slack logging handler')
    handler = SlackLogHandler()
    handler.setLevel(logging.ERROR)
    handler.setFormatter(_log_formatter)
    logger.addHandler(handler)

    logger.info('opening RTM session')
    client = slack.RTMClient(token=RTM_TOKEN)
    client.start()


if __name__ == '__main__':
    main()
