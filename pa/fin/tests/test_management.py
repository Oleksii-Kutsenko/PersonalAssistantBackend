import os
from unittest.mock import patch, call

from fin.management.commands.parse import Command
from fin.tests.base import BaseTestCase


class ManagementTests(BaseTestCase):
    def test_get_web_driver_path(self):
        """
        Tests that get_web_driver_path returns expected web_driver_path
        """
        expected_web_driver_path = f'{os.getcwd()}/fin/management/commands/webdriver/chromedriver'
        web_driver_path = Command.get_web_driver_path()
        self.assertEqual(expected_web_driver_path, web_driver_path)

    @patch('zipfile.ZipFile')
    @patch('urllib.request.urlretrieve')
    def test_download_web_driver(self, urlretrieve_mock, zipfile_mock):
        """
        Tests that download_web_driver function tries to download driver and unzip it
        """
        expected_call = call().__enter__().extractall('./fin/tests/files')

        driver_dir = './fin/tests/files'
        path = './fin/tests/files/driver_mock'
        urlretrieve_mock.return_value = path, None

        Command.download_web_driver(driver_dir)

        self.assertIn(expected_call, zipfile_mock.mock_calls)
