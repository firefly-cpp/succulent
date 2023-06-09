from flask import Flask, jsonify, request
from succulent.configuration import Configuration
from succulent.processing import Processing
from datetime import datetime

class SucculentAPI:
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
        self.app.add_url_rule('/measure', 'measure', self.measure, methods=['POST'])

    def url(self):
        # Generate URL
        parameters = self.processing.parameters()

        # Send response
        return jsonify({'url': f'{self.host}:{self.port}/measure?{parameters}'}), 200

    def measure(self):
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
        self.app.run(host=self.host, port=self.port)