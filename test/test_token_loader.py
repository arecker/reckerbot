import unittest

from reckerbot import TokenLoader


class TestTokenLoader(unittest.TestCase):
    def test_to_env_key(self):
        loader = TokenLoader()
        actual = loader.to_env_key('something')
        expected = 'SOMETHING_TOKEN_PATH'
        self.assertEqual(actual, expected)

    def test_to_token_path(self):
        loader = TokenLoader(secrets_dir='test-secrets')
        actual = loader.to_token_path('test')
        expected = 'test-secrets/test-token'
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
