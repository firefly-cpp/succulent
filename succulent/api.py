from flask import Flask, jsonify, request
from succulent.configuration import Configuration
from succulent.processing import Processing

# Configuration file
conf = Configuration('configuration.yml');
config = conf.load_config()

# Initialise processing
processing = Processing(config)

# Initialise Flask
app = Flask(__name__)

@app.route('/measure', methods=['GET'])
def url():
    # Generate URL
    parameters = processing.parameters()

    # Send response
    return jsonify({'url': f'0.0.0.0:8080/measure?{parameters}' }), 200

@app.route('/measure', methods=['POST'])
def measure():
    # Process request
    processing.process(request)

    # Send response
    return jsonify({'message': 'Data stored'}), 200

app.run(host='0.0.0.0', port=8080)