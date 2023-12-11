import os
import sqlite3
import inspect
import pandas as pd
from datetime import datetime


class Processing:
    """Class for processing and storing data.

    Args:
        format (str): The format of the data ('csv', 'json', 'sqlite', or 'image').
        config (dict): The configuration settings for data processing.
        unittest (bool, optional): If True, the class is being used for unit testing. Default is False.

    Attributes:
        directory (str): The path to storage location.
        format (str): The format of the data ('csv', 'json', 'sqlite', or 'image').
        columns (list): List of feature names in the data.
        boundaries (list): List of minimum and maximum boundaries for each feature in the data.
        enable_results (bool): If True, the results are enabled.
        enable_export (bool): If True, the export is enabled.
        df (pandas.DataFrame): The DataFrame to hold the data (for 'csv', 'json', and 'sqlite' formats).
        key (str): The key to retrieve the image file from the request (for 'image' format).

    Raises:
        ValueError: Invalid format is provided.
    """

    def __init__(self, format, config, unittest=False):
        # Validate format
        if format not in ['csv', 'json', 'sqlite', 'image']:
            raise ValueError(f'Invalid format: {format}')

        # Initialise attributes
        index = 1 if unittest else 2
        self.directory = os.path.join(os.path.dirname(
            os.path.abspath(inspect.stack()[index].filename)), 'data')
        self.format = format
        self.enable_results = False
        self.enable_export = False

        if format in ['csv', 'json', 'sqlite']:
            self.columns = [configuration['name']
                            for configuration in config['data']]
            self.boundaries = [{
                configuration['name']: {
                    key: configuration[key]
                    for key in ['min', 'max']
                    if key in configuration
                }
            } for configuration in config['data'] if configuration.get('min') is not None or configuration.get('max') is not None]

            if 'results' in config:
                for results in config['results']:
                    if 'enable' in results:
                        self.enable_results = results['enable']
                    if 'export' in results:
                        self.enable_export = results['export']

            self.df = pd.DataFrame()  # Initialize df attribute

        if format == 'image':
            self.key = config['data'][0]['key']

    def parameters(self):
        """Generate URL parameters based on data columns.

        Returns:
            str: URL parameters as a string.
        """
        if self.format != 'image':
            parameters = [f'{column}=' for column in self.columns]
            parameters = '&'.join(parameters)
        return parameters if self.format != 'image' else ''

    def boundary(self, value, boundary, column):
        """Check if the value is within the specified boundary for a column.

        Args:
            value (float): The value to check.
            boundary (dict): A dictionary containing 'min' and/or 'max' boundaries for the column.
            column (str): The name of the column being checked.

        Raises:
            ValueError: Value is outside the specified boundary.

        Returns:
            float: The original value (within the boundary).
        """
        if 'min' in boundary and float(value) < float(boundary['min']):
            raise ValueError(
                f'{column} ({value}) is lower than the specified minimum ({boundary["min"]}).')
        if 'max' in boundary and float(value) > float(boundary['max']):
            raise ValueError(
                f'{column} ({value}) is greater than the specified maximum ({boundary["max"]}).')
        return value

    def process(self, req):
        """Process the incoming request and store the data accordingly.

        Args:
            req (Request): The incoming request object.

        Returns:
            None
        """
        # Directory preparation
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

        if self.format in ['csv', 'json', 'sqlite']:
            # Define paths
            path = os.path.join(
                self.directory, f'data.{self.format}'
            )

            # Load existing data
            if os.path.exists(path):
                if self.format == 'csv':
                    self.df = pd.read_csv(path, sep=',')
                elif self.format == 'json':
                    self.df = pd.read_json(path, orient='records')
                elif self.format == 'sqlite':
                    conn = sqlite3.connect(path)
                    self.df = pd.read_sql_query('SELECT * FROM data', conn)
                    conn.close()
                else:
                    raise ValueError(f'Invalid file type: {self.format}')
            # Initialise new data
            else:
                self.df = pd.DataFrame(columns=self.columns)

            # Parse data from request
            data = {}
            for column in self.columns:
                # Request type
                if req.is_json:
                    value = req.json[column] if column in req.json else None
                else:
                    value = req.args.get(column, default=None)

                # Boundary check
                if column in [list(boundaries.keys())[0] for boundaries in self.boundaries]:
                    index = [list(boundaries.keys())[0]
                             for boundaries in self.boundaries].index(column)
                    data[column] = self.boundary(
                        value, self.boundaries[index][column], column)
                else:
                    data[column] = value

            # Convert data to Series
            data = pd.Series(data, index=self.columns)

            # Merge data
            self.df = pd.concat(
                [self.df, data.to_frame().T], ignore_index=True)

            # Store data to device
            if self.format == 'csv':
                self.df.to_csv(path, sep=',', index=False)
            elif self.format == 'json':
                self.df.to_json(path, orient='records', indent=4)
            elif self.format == 'sqlite':
                conn = sqlite3.connect(path)
                self.df.to_sql('data', conn, if_exists='replace', index=False)
                conn.close()

        if self.format == 'image':
            # Retrieve image from request
            file = req.files[self.key]

            # Timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')

            # Store image to device
            file.save(os.path.join(self.directory,
                      f'{timestamp}_{file.filename}'))

    def data(self):
        """Generate results based on the stored data.

        Returns:
            dict: The results as a dictionary.
        """
        if self.enable_results:
            if self.format in ['csv', 'json', 'sqlite']:
                # Define paths
                path = os.path.join(
                    self.directory, f'data.{self.format}'
                )

                # Load existing data
                if os.path.exists(path):
                    if self.format == 'csv':
                        self.df = pd.read_csv(path, sep=',')
                    elif self.format == 'json':
                        self.df = pd.read_json(path, orient='records')
                    elif self.format == 'sqlite':
                        conn = sqlite3.connect(path)
                        self.df = pd.read_sql_query('SELECT * FROM data', conn)
                        conn.close()
                    else:
                        raise ValueError(f'Invalid file type: {self.format}')

                # Check if data is available
                if self.df.empty:
                    return {'valid': False, 'message': 'No data available.'}

                # Send response
                return {'valid': True, 'data': self.df}
            else:
                # Unsupported file type
                return {'valid': False, 'message': f'Results are not supported for the chosen file type ({self.format}).'}
        else:
            # Results are not enabled in configuration
            return {'valid': False, 'message': 'Results are not enabled in your current configuration.'}

    def export(self):
        """Export the stored data.

        Returns:
            dict: The exported data as a dictionary.
        """
        if self.enable_export:
            if self.format in ['csv', 'json', 'sqlite']:
                # Define paths
                path = os.path.join(
                    self.directory, f'data.{self.format}'
                )

                # Load existing data
                if os.path.exists(path):
                    if self.format == 'csv':
                        self.df = pd.read_csv(path, sep=',')
                    elif self.format == 'json':
                        self.df = pd.read_json(path, orient='records')
                    elif self.format == 'sqlite':
                        conn = sqlite3.connect(path)
                        self.df = pd.read_sql_query('SELECT * FROM data', conn)
                        conn.close()
                    else:
                        raise ValueError(f'Invalid file type: {self.format}')

                # Check if data is available
                if self.df.empty:
                    return {'valid': False, 'message': 'No data available.'}

                # Send response
                return {'valid': True, 'data': self.df}
            else:
                # Unsupported file type
                return {'valid': False, 'message': f'Exporting is not supported for the chosen file type ({self.format}).'}
        else:
            # Results are not enabled in configuration
            return {'valid': False, 'message': 'Exporting is not enabled in your current configuration.'}
