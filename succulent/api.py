from flask import Flask, jsonify, request, url_for, make_response
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

    Configuration:
        max_content_length (int, optional): Maximum accepted size (in bytes)
            of an incoming request body. Defaults to
            ``DEFAULT_MAX_CONTENT_LENGTH`` (5 MB) when not set in the
            configuration file. Requests exceeding this size are rejected
            with a 413 response before being processed, to protect the
            server against oversized or flooding POST requests.
    """

    # Default maximum size (in bytes) accepted for a single request body.
    DEFAULT_MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB

    def __init__(self, config, host='0.0.0.0', port=8080, format='csv'):
        self.host = host
        self.port = port
        self.format = format

        # Configuration file
        conf = Configuration(config)
        self.config = conf.load_config()

        # Initialise processing
        self.processing = Processing(config=self.config, format=self.format)

        # Initialise Flask
        self.app = Flask(__name__, static_url_path='/succulent/static')

        # Limit the maximum accepted size of incoming request bodies to
        # protect the server against oversized or flooding POST requests.
        # Can be overridden via the 'max_content_length' (bytes) setting
        # in the configuration file.
        self.app.config['MAX_CONTENT_LENGTH'] = int(
            self.config.get('max_content_length', self.DEFAULT_MAX_CONTENT_LENGTH))

        self.app.add_url_rule('/', 'index', self.index, methods=['GET'])
        self.app.add_url_rule('/measure', 'url', self.url, methods=['GET'])
        self.app.add_url_rule('/measure', 'measure',
                              self.measure, methods=['POST'])
        self.app.add_url_rule('/data', 'data', self.data, methods=['GET'])
        self.app.add_url_rule('/export', 'export',
                              self.export, methods=['GET'])
        self.app.register_error_handler(
            413, self.payload_too_large)

    def index(self):
        """Generate index HTML page with information about the API.

        Returns:
            Response: HTML response with the index page.
        """
        img_url = url_for('static', filename='logo.png')

        return f"""
        <div style="font-family: Arial;">
            <center>
                <h1>succulent - Collect POST requests easily</h1>
                <img src="{img_url}" alt="succulent" style="width:500px;">
                <p>The service is currently up and running.</p>
                <p><i>For more information, see the <a href='https://succulent.readthedocs.io/en/latest' target='_blank'>documentation</a>.</i></p>
            </center>
        </div>
        """

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

    def data(self):
        """Display the stored data.

        Returns:
            Response: JSON response with the stored data.
        """
        data = self.processing.data(request)
        if data['valid'] == False:
            return jsonify({'message': data['message']}), data['code'] if data['code'] else 400

        return jsonify({'data': data['data'].to_dict(orient='records')}), 200

    def export(self):
        """Export the stored data to a CSV file.
        """
        data = self.processing.export(request)
        if data['valid'] == False:
            return jsonify({'message': data['message']}), data['code'] if data['code'] else 400

        # Convert DataFrame to CSV
        csv_data = data['data'].to_csv(index=False)

        # Create a response with CSV content
        response = make_response(csv_data)
        response.headers["Content-Disposition"] = "attachment; filename=data.csv"
        response.headers["Content-Type"] = "text/csv"

        return response, 200

    def payload_too_large(self, error):
        """Handle requests whose body exceeds 'MAX_CONTENT_LENGTH'.

        Args:
            error (HTTPException): The raised 413 error.

        Returns:
            Response: JSON response with an error message.
        """
        return jsonify({'message': 'Payload too large.'}), 413

    def start(self):
        """Start the Flask application on the specified host and port.

        Returns:
            None
        """
        self.app.run(host=self.host, port=self.port)
