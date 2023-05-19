from flask import Flask, jsonify, request
from succulent.configuration import Configuration
from succulent.processing import Processing

class SucculentAPI:
    def __init__(self, host, port, config):
        self.host = host
        self.port = port

        # Configuration file
        conf = Configuration(config)
        self.config = conf.load_config()

        # Initialise processing
        self.processing = Processing(self.config)

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
        except ValueError:
            # Invalid file type
            return jsonify({'message': f'Invalid file type: {self.config["filetype"]}. Supported file types: csv, json'}), 400

        # Send response
        return jsonify({'message': 'Data stored'}), 200

    def start(self):
        self.app.run(host=self.host, port=self.port)