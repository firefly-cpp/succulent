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
    """

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
        self.app.add_url_rule('/', 'index', self.index, methods=['GET'])
        self.app.add_url_rule('/measure', 'url', self.url, methods=['GET'])
        self.app.add_url_rule('/measure', 'measure',
                              self.measure, methods=['POST'])
        self.app.add_url_rule('/data', 'data', self.data, methods=['GET'])
        self.app.add_url_rule('/export', 'export',
                              self.export, methods=['GET'])

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
        data = self.processing.data()
        if data['valid'] == False:
            return jsonify({'message': data['message']}), 400

        return jsonify({'data': data['data'].to_dict(orient='records')}), 200

    def export(self):
        """Export the stored data to a CSV file.
        """
        data = self.processing.export()
        if data['valid'] == False:
            return jsonify({'message': data['message']}), 400

        # Convert DataFrame to CSV
        csv_data = data['data'].to_csv(index=False)

        # Create a response with CSV content
        response = make_response(csv_data)
        response.headers["Content-Disposition"] = "attachment; filename=data.csv"
        response.headers["Content-Type"] = "text/csv"

        return response, 200

    def start(self):
        """Start the Flask application on the specified host and port.

        Returns:
            None
        """
        self.app.run(host=self.host, port=self.port)
