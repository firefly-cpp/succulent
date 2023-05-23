import os
import yaml
import inspect

class Configuration:
    def __init__(self, path):
        self.path = os.path.join(
            os.path.dirname(os.path.abspath(inspect.stack()[2].filename)), path
        )

    def load_config(self):
        with open(self.path, 'r') as yml:
            config = yaml.safe_load(yml)
            return config