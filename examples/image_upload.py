"""
Example shows usage of the 
Succulent API for image upload.
"""

import os
from succulent.api import SucculentAPI

# Load configuration file from ./configuration/configuration.yml
path = os.path.join(os.path.dirname(__file__), 'configuration', 'image.yml')

# Initialise API
# host - Host to run API on
# port - Port to run API on
# config - Path to configuration file
# format - csv, json, sqlite, or image (default: csv)
api = SucculentAPI(host='0.0.0.0', port=8080, config=path, format='image')

# Start API
api.start()