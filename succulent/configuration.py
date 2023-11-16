import os
import yaml
import inspect


class Configuration:
    """Class for loading configuration settings from a YAML file.

    Args:
        path (str): The path to the YAML configuration file.

    Attributes:
        path (str): The path to the YAML configuration file.
    """

    def __init__(self, path):
        self.path = os.path.join(
            os.path.dirname(os.path.abspath(inspect.stack()[2].filename)), path
        )

    def load_config(self):
        """Load the configuration settings from the YAML file.

        Returns:
            dict: The loaded configuration settings as a dictionary.

        Raises:
            FileNotFoundError: The specified file does not exist.
        """
        if not os.path.isfile(self.path):
            raise FileNotFoundError(f'File not found: {self.path}')

        with open(self.path, 'r') as yml:
            config = yaml.safe_load(yml)
            return config
