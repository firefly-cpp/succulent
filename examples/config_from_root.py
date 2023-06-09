"""
Example demonstrates how to load
a configuration file from the root directory.
"""

from succulent.api import SucculentAPI

# Initialise API
# host - Host to run API on
# port - Port to run API on
# config - Path to configuration file
# format - csv, json, sqlite, or image (default: csv)
api = SucculentAPI(host='0.0.0.0', port=8080, config='configuration.yml', format='csv')

# Start API
api.start()