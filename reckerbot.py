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
        return slack.WebClient(token=secret_loader.web_token)

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


class SecretLoader:
    def read_token(self, token_type):
        default_path = os.path.join(here, f'secrets/{token_type}-token')
        env_key = f'{token_type.upper()}_TOKEN_PATH'
        path = os.environ.get(env_key, default_path)
        logger.info('reading %s token from %s', token_type, path)
        with open(path, 'r') as f:
            return f.read().strip()

    @functools.cached_property
    def rtm_token(self):
        return self.read_token('rtm')

    @functools.cached_property
    def web_token(self):
        return self.read_token('web')


secret_loader = SecretLoader()


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
    client = slack.RTMClient(token=secret_loader.rtm_token)
    client.start()


if __name__ == '__main__':
    main()
