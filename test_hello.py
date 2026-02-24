import unittest
from unittest.mock import patch
from hello import main


class TestHello(unittest.TestCase):
    def test_main_prints_hello_world(self):
        with patch('builtins.print') as mock_print:
            main()
            mock_print.assert_called_once_with("Hello World")


if __name__ == '__main__':
    unittest.main()
