import os
import yaml

class Configuration:
    def __init__(self, path):
        self.path = path

    def load_config(self):
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', self.path
        )
        with open(path, 'r') as yml:
            config = yaml.safe_load(yml)
            return config

