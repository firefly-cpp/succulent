from succulent import __version__
import unittest
import os
from flask import Flask
from flask.testing import FlaskClient
from unittest.mock import MagicMock
from succulent.processing import Processing
from succulent.api import SucculentAPI
from succulent.configuration import Configuration

class TestProcessing(unittest.TestCase):
    """
    Test case for the Processing class.
    
    This test case focuses on testing the methods and functionality of the Processing class.
    """

    def setUp(self):
        # Load configuration from configuration.yml
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'succulent', 'configuration.yml')
        configuration = Configuration(config_path)
        config = configuration.load_config()
        self.processing = Processing(config['data'], 'csv')

    def test_parameters(self):
        """
        Test the parameters() method of the Processing class.

        This test verifies that the parameters() method returns the expected string representation of the parameters.
        """
        expected_parameters = 'temperature=&humidity=&light=&time=&date='
        self.assertEqual(self.processing.parameters(), expected_parameters)

    def test_process_json(self):
        """
        Test the process() method of the Processing class with JSON data.

        This test ensures that the process() method correctly merges the JSON data with the existing DataFrame.
        """
        # Mock the request object
        request = MagicMock()
        request.is_json = True
        request.json = {
            'temperature': '25',
            'humidity': '50',
            'light': 'high',
            'time': '10:30',
            'date': '2022-01-01'
        }

        # Process the request
        self.processing.process(request)

        # Verify the data is merged correctly
        expected_data = [
            {'temperature': '25', 'humidity': '50', 'light': 'high', 'time': '10:30', 'date': '2022-01-01'}
        ]
        self.assertEqual(self.processing.df.to_dict(orient='records'), expected_data)

    def test_process_args(self):
        """
        Test the process() method of the Processing class with query string arguments.

        This test ensures that the process() method correctly merges the query string arguments with the existing DataFrame.
        """
        # Mock the request object
        request = MagicMock()
        request.is_json = False
        request.args.get.side_effect = ['25', '50', 'high', '10:30', '2022-01-01']

        # Process the request
        self.processing.process(request)

        # Verify the data is merged correctly
        expected_data = [
            {'temperature': '25', 'humidity': '50', 'light': 'high', 'time': '10:30', 'date': '2022-01-01'}
        ]
        self.assertEqual(self.processing.df.to_dict(orient='records'), expected_data)


    def test_process_args(self):
        # Mock the request object
        request = MagicMock()
        request.is_json = False
        request.args.get.side_effect = ['value1', 'value2', 'value3']

        # Process the request
        self.processing.process(request)

        # Verify the data is merged correctly
        expected_data = [
            {'column1': 'value1', 'column2': 'value2', 'column3': 'value3'}
        ]
        self.assertEqual(self.processing.df.to_dict(orient='records'), expected_data)


class TestSucculentAPI(unittest.TestCase):
    """
    Test case for the SucculentAPI class.
    
    This test case focuses on testing the methods and functionality of the SucculentAPI class.
    """

    def setUp(self):
        # Create an instance of the SucculentAPI class for testing
        self.api = SucculentAPI(host='0.0.0.0', port=8080, config='configuration.yml', format='csv')

    def test_version(self):
        """
        Test the version of the SucculentAPI.
        """
        expected_version = '0.1.1'
        self.assertEqual(__version__, expected_version)

    def test_url(self):
        """
        Test the URL generation of the SucculentAPI.
        """
        # Make a request to the URL endpoint
        with self.api.app.test_client() as client:
            response = client.get('/measure')
            data = response.get_json()

            # Verify the URL in the response
            expected_url = '0.0.0.0:8080/measure?temperature=&humidity=&light=&time=&date='
            self.assertEqual(data['url'], expected_url)

    def test_measure(self):
        """
        Test the measurement processing of the SucculentAPI.
        """
        # Create a mock request object
        request = unittest.mock.Mock()
        self.api.processing.process = unittest.mock.Mock()

        # Call the measure endpoint
        response = self.api.measure(request)

        # Verify the response
        self.assertEqual(response[1], 200)
        self.assertEqual(response[0].get_json(), {'message': 'Data stored'})

class TestConfiguration(unittest.TestCase):
    """
    Test case for the Configuration class.

    This test case focuses on testing the methods and functionality of the Configuration class.
    """

    def setUp(self):
        # Get the path to the configuration.yml file
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'succulent', 'configuration.yml')
        self.configuration = Configuration(config_path)

    def test_load_config(self):
        """
        Test the load_config() method of the Configuration class.

        This test verifies that the load_config() method correctly loads the configuration from the configuration.yml file.
        """
        # Load the configuration from the file
        config = self.configuration.load_config()

        # Verify the loaded configuration
        expected_config = {
            'data': [
                {'name': 'temperature'},
                {'name': 'humidity'},
                {'name': 'light'},
                {'name': 'time'},
                {'name': 'date'}
            ]
        }
        self.assertEqual(config, expected_config)


if __name__ == '__main__':
    unittest.main()

