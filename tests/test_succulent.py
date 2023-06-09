from succulent import __version__
import unittest
import os
import shutil
import pytest
import inspect
from flask import Flask
from unittest.mock import MagicMock, Mock
from succulent.processing import Processing
from succulent.api import SucculentAPI
from succulent.configuration import Configuration
from datetime import datetime
from werkzeug.datastructures import FileStorage

@pytest.fixture(autouse=True)
def teardown(request):
    yield
    directory = os.path.join(os.path.dirname(os.path.abspath(inspect.stack()[0].filename)), 'data')
    if os.path.exists(directory):
        shutil.rmtree(directory)

class TestProcessing(unittest.TestCase):
    """
    Test case for the Processing class.
    
    This test case focuses on testing the methods and functionality of the Processing class.
    """

    def setUp(self):
        # Load configuration from configuration.yml
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'configuration.yml')
        configuration = Configuration(config_path)
        config = configuration.load_config()
        self.processing = Processing(config=config, format='csv', unittest=True)

    def test_parameters(self):
        """
        Test the parameters() method of the Processing class.

        This test verifies that the parameters() method returns the expected string representation of the parameters.
        """
        expected_parameters = 'temperature=&humidity=&light=&time=&date='
        self.assertEqual(self.processing.parameters(), expected_parameters)

    def test_process_json(self):
        try:
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
                {
                    'temperature': '25',
                    'humidity': '50',
                    'light': 'high',
                    'time': '10:30',
                    'date': '2022-01-01'
                }
            ]
            actual_data = self.processing.df.to_dict(orient='records')
            self.assertEqual(actual_data, expected_data)
        except PermissionError:
            pytest.skip('Permission denied.')

    def test_process_args(self):
        """
        Test the process() method of the Processing class with query string arguments.

        This test ensures that the process() method correctly merges the query string arguments with the existing DataFrame.
        """   
        try:
            # Mock the request object
            request = MagicMock()
            request.is_json = False
            request.args.get.side_effect = ["25", "50", "high", "10:30", "2022-01-01"]

            # Process the request
            self.processing.process(request)

            # Verify the data is merged correctly
            expected_data = [
                {'temperature': '25', 'humidity': '50', 'light': 'high', 'time': '10:30', 'date': '2022-01-01'}
            ]
            self.assertEqual(self.processing.df.to_dict(orient='records'), expected_data)
        except PermissionError:
            pytest.skip('Permission denied.')

class TestImageProcessing(unittest.TestCase):
    """
    Test case for the Processing class with the image format.

    This test case focuses on image upload, processing, and storage.
    """
    def setUp(self):
        # Load configuration from configuration.yml
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'image.yml')
        configuration = Configuration(config_path)
        config = configuration.load_config()
        self.processing = Processing(config=config, format='image', unittest=True)
    
    def test_process_image(self):
        # Temporary file to simulate an image
        image_data = b'Test image data'
        with open('temp_image.jpg', 'wb') as f:
            f.write(image_data)

        # Create a FileStorage object to simulate the uploaded file
        file = FileStorage(stream=open('temp_image.jpg', 'rb'), filename='test_image.jpg')

        # Send a POST request to the image upload endpoint
        request = MagicMock()
        request.files = {'image': file}

        # Process the request
        self.processing.process(request)

        # Timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')

        # Assert the file exists in the data directory
        self.assertTrue(os.path.exists(os.path.join(self.processing.directory, f'{timestamp}_test_image.jpg')))

        # Clean up the temporary file
        file.close()
        os.remove('temp_image.jpg')

class TestSucculentAPI(unittest.TestCase):
    """
    Test case for the SucculentAPI class.
    
    This test case focuses on testing the methods and functionality of the SucculentAPI class.
    """

    def setUp(self):
        # Create an instance of the SucculentAPI class for testing
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'configuration.yml')
        self.api = SucculentAPI(host='0.0.0.0', port=8080, config=config_path, format='csv')

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
        # Create a mock request object
        mock_request = Mock()
        mock_request.is_json = True
        mock_request.json = {
            'temperature': 25.0,
            'humidity': 60.0,
            'light': 'high',
            'time': '10:30 AM',
            'date': '2023-05-21'
        }

        # Call the measure endpoint
        response = self.api.app.test_client().post('/measure', json=mock_request.json)

        # Assert the response and timestamp
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['message'], 'Data stored')
        # Compare the timestamp with the current time
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.assertEqual(response.json['timestamp'], current_time)

    def test_upper_boundary(self):
        # Create a mock request object
        mock_request = Mock()
        mock_request.is_json = True
        mock_request.json = {
            'temperature': 100.0, # This is above the upper boundary of 50.0
            'humidity': 60.0,
            'light': 'high',
            'time': '10:30 AM',
            'date': '2023-05-21'
        }

        # Call the measure endpoint
        response = self.api.app.test_client().post('/measure', json=mock_request.json)

        # Assert the response
        self.assertEqual(response.status_code, 400)

    def test_lower_boundary(self):
        # Create a mock request object
        mock_request = Mock()
        mock_request.is_json = True
        mock_request.json = {
            'temperature': -100.0, # This is below the lower boundary of -20.0
            'humidity': 60.0,
            'light': 'high',
            'time': '10:30 AM',
            'date': '2023-05-21'
        }

        # Call the measure endpoint
        response = self.api.app.test_client().post('/measure', json=mock_request.json)

        # Assert the response
        self.assertEqual(response.status_code, 400)

class TestConfiguration(unittest.TestCase):
    """
    Test case for the Configuration class.

    This test case focuses on testing the methods and functionality of the Configuration class.
    """

    def setUp(self):
        # Get the path to the configuration.yml file
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'configuration.yml')
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
                {'name': 'temperature', 'min': -20.0, 'max': 50.0},
                {'name': 'humidity'},
                {'name': 'light'},
                {'name': 'time'},
                {'name': 'date'}
            ]
        }
        self.assertEqual(config, expected_config)


if __name__ == '__main__':
    unittest.main()

