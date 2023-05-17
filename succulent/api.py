import os
import yaml

import pandas as pd

from flask import Flask, jsonify, request

def load_config():
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'configuration.yml'
    )
    with open(path, 'r') as yml:
        config = yaml.safe_load(yml)
        return config

# Configuration file
config = load_config()

# Data configuration
columns = [configuration['name'] for configuration in config['data']]
filetype = config['filetype']

app = Flask(__name__)

@app.route('/measure', methods=['GET'])
def url():
    parameters = [f'{column}=' for column in columns]
    params = '&'.join(parameters)
    return jsonify({'url': f'0.0.0.0:8080/measure?{params}' }), 200

@app.route('/measure', methods=['POST'])
def measure():
    # Define paths
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'data', f'data.{filetype}'
    )
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'data', f'data.{filetype}'
    )
    
    # Load existing data
    if os.path.exists(path):
        if filetype == 'csv':
            df = pd.read_csv(path, sep=',')
        elif filetype == 'json':
            df = pd.read_json(path, orient='records')
    # Initialise new data
    else:
        df = pd.DataFrame(columns=columns)

    # Parse data from request
    data = [request.args.get(column) for column in columns]
    new_data = pd.Series(data, index=columns)

    # Merge data
    df = pd.concat([df, new_data.to_frame().T], ignore_index=True)

    # Store data to device
    match filetype:
        case 'csv':
            df.to_csv(output_path, sep=',', index=False)
        case 'json':
            df.to_json(output_path, orient='records', indent=4)
    
    return jsonify({'success': True}), 200

app.run(host='0.0.0.0', port=8080)
