from flask import Flask, jsonify, request
from succulent.configuration import Configuration
from succulent.processing import Processing
from datetime import datetime


class SucculentAPI:
    """Succulent API server.

    Args:
        host (str): The host address to run the API server.
        port (int): The port number to run the API server.
        config (str): Path to the configuration file.
        format (str, optional): The format of the data ('csv', 'json', 'sqlite', or 'image').

Attributes:
        host (str): The host address to run the API server.
        port (int): The port number to run the API server.
        config (dict): Configuration file.
        format (str): The format of the data ('csv', 'json', 'sqlite', or 'image').
        app (Flask): Flask application.
        processing (Processing): Instance of the Processing class.
    """

    def __init__(self, host, port, config, format='csv'):
        self.host = host
        self.port = port
        self.format = format

        # Configuration file
        conf = Configuration(config)
        self.config = conf.load_config()

        # Initialise processing
        self.processing = Processing(config=self.config, format=self.format)

        # Initialise Flask
        self.app = Flask(__name__)
        self.app.add_url_rule('/measure', 'url', self.url, methods=['GET'])
        self.app.add_url_rule('/measure', 'measure',
                              self.measure, methods=['POST'])

    def url(self):
        """Generate URL with parameters for measurements.

        Returns:
            Response: JSON response with the generated URL.
        """
        # Generate URL
        parameters = self.processing.parameters()

        # Send response
        return jsonify({'url': f'{self.host}:{self.port}/measure?{parameters}'}), 200

    def measure(self):
        """Process the incoming request and store the timestamp.

        Returns:
            Response: JSON response with a success message and timestamp.
        """
        try:
            # Process request
            self.processing.process(request)

            # Collect and store timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # You can store the timestamp in a database, file, or any other desired storage mechanism.
            # Example: database.insert_timestamp(timestamp)
        except ValueError as err:
            # Invalid file type
            return jsonify({'message': str(err)}), 400

        # Send response
        return jsonify({'message': 'Data stored', 'timestamp': timestamp}), 200

    def start(self):
        """Start the Flask application on the specified host and port.

        Returns:
            None
        """
        self.app.run(host=self.host, port=self.port)
