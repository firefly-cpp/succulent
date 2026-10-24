import os
import hmac
import sqlite3
import inspect
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename


class Processing:
    """Class for processing and storing data.

    Args:
        format (str): The format of the data ('csv', 'json', 'sqlite', 'image', or 'xml').
        config (dict): The configuration settings for data processing.
        unittest (bool, optional): If True, the class is being used for unit testing. Default is False.

    Attributes:
        directory (str): The path to storage location.
        format (str): The format of the data ('csv', 'json', 'sqlite', 'image', or 'xml').
        columns (list): List of feature names in the data.
        boundaries (list): List of minimum and maximum boundaries for each feature in the data.
        password (str): The password for data access. Default is None.
        timestamp (bool): Enable timestamp storage for the data collection.
        enable_results (bool): Enable access to the collected data via the API.
        enable_export (bool): Enable collected data export via the API.
        df (pandas.DataFrame): The DataFrame to hold the data (for 'csv', 'json', and 'sqlite' formats).
        key (str): The key to retrieve the image file from the request (for 'image' format).

    Raises:
        ValueError: Invalid format is provided.
    """

    def __init__(self, format, config, unittest=False):
        # Validate format
        if format not in ['csv', 'json', 'sqlite', 'image', 'xml']:
            raise ValueError(f'Invalid format: {format}')

        # Initialise attributes
        index = 1 if unittest else 2
        self.directory = os.path.join(os.path.dirname(
            os.path.abspath(inspect.stack()[index].filename)), 'data')
        self.format = format
        self.password = None
        self.timestamp = False
        self.enable_results = False
        self.enable_export = False

        if 'password' in config:
            self.password = config['password']

        if format in ['csv', 'json', 'sqlite', 'xml']:
            self.columns = [configuration['name']
                            for configuration in config['data']]
            if 'timestamp' in self.columns:
                raise ValueError(
                    '\"timestamp\" is a reserved keyword and cannot be used as a column name.')
            if 'password' in self.columns:
                raise ValueError(
                    '\"password\" is a reserved keyword and cannot be used as a column name.')
            self.boundaries = [{
                configuration['name']: {
                    key: configuration[key]
                    for key in ['min', 'max']
                    if configuration.get(key) is not None
                }
            } for configuration in config['data'] if configuration.get('min') is not None or configuration.get('max') is not None]

            if 'timestamp' in config:
                if config['timestamp'] == True:
                    self.timestamp = True

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

        A missing or empty value is not checked and is stored as empty, so a
        device can still send a measurement when one sensor has no reading.

        Raises:
            ValueError: Value is not numeric or is outside the specified boundary.

        Returns:
            float: The original value (within the boundary, or empty).
        """
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return value
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f'{column} ({value}) must be a number.') from None

        if 'min' in boundary and number < float(boundary['min']):
            raise ValueError(
                f'{column} ({value}) is lower than the specified minimum ({boundary["min"]}).')
        if 'max' in boundary and number > float(boundary['max']):
            raise ValueError(
                f'{column} ({value}) is greater than the specified maximum ({boundary["max"]}).')
        return value

    def request_passwords(self, req):
        """Collect all passwords supplied with the request.

        A password can be sent in any of the following places:

        - ``Authorization: Bearer <password>`` header,
        - ``X-API-Key: <password>`` header,
        - ``password`` field in a JSON body,
        - ``password`` query parameter (kept for backward compatibility;
          prefer a header, since URLs are often written to server logs).

        All of them are returned, so a header added by a proxy or API gateway
        does not hide a password sent in another place.

        Args:
            req (Request): The incoming request object.

        Returns:
            list: The supplied passwords (empty if none was given).
        """
        passwords = []

        authorization = req.headers.get('Authorization', '')
        scheme, _, token = authorization.partition(' ')
        if scheme.lower() == 'bearer' and token.strip():
            passwords.append(token.strip())

        api_key = req.headers.get('X-API-Key')
        if api_key:
            passwords.append(api_key)

        if req.is_json and isinstance(req.json, dict) and req.json.get('password') is not None:
            passwords.append(req.json['password'])

        query_password = req.args.get('password', default=None)
        if query_password is not None:
            passwords.append(query_password)

        return passwords

    def authorised(self, req):
        """Check whether the request carries the configured password.

        The request is accepted if the password matches in any of the places
        listed in :meth:`request_passwords`. Each comparison uses
        :func:`hmac.compare_digest`, which takes the same time regardless of
        where the strings differ, to prevent timing attacks.

        Args:
            req (Request): The incoming request object.

        Returns:
            bool: True if no password is configured or a supplied one matches.
        """
        if not self.password:
            return True

        expected = str(self.password).encode('utf-8')

        # Compare every candidate (no early exit) to keep timing uniform
        matches = [
            hmac.compare_digest(str(supplied).encode('utf-8'), expected)
            for supplied in self.request_passwords(req)
        ]
        return any(matches)

    def process(self, req):
        """Process the incoming request and store the data accordingly.

        Args:
            req (Request): The incoming request object.

        Raises:
            ValueError: Unauthorised access.

        Returns:
            datetime: The moment the request was processed. The same value is
            stored in the ``timestamp`` column (if enabled) and used in the
            image filename (for the 'image' format).
        """
        # Single timestamp for this request, reused for storage and response
        now = datetime.now()

        # Directory preparation
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

        # Password check
        if not self.authorised(req):
            raise ValueError('Unauthorised access.')

        if self.format in ['csv', 'json', 'sqlite', 'xml']:
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
                elif self.format == 'xml':
                    self.df = pd.read_xml(path)
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
                elif self.format == 'xml':
                    root = ET.fromstring(req.data)
                    data = {child.tag: child.text for child in root}
                    value = data[column] if column in data else None
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

            # Timestamp
            if self.timestamp:
                data['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')

            # Merge data
            self.df = pd.concat(
                [self.df, data.to_frame().T], ignore_index=True)

            # Store data to device
            if self.format == 'csv':
                self.df.to_csv(path, sep=',', index=False)
            elif self.format == 'json':
                self.df.to_json(path, orient='records', indent=4)
            elif self.format == 'xml':
                self.df.to_xml(path, index=False)
            elif self.format == 'sqlite':
                conn = sqlite3.connect(path)
                self.df.to_sql('data', conn, if_exists='replace', index=False)
                conn.close()

        if self.format == 'image':
            # Retrieve image from request
            file = req.files[self.key]

            filename = secure_filename(file.filename or '')
            if not filename:
                filename = 'upload'

            # Timestamp
            timestamp = now.strftime('%Y-%m-%d_%H%M%S')

            # Build the destination path and verify it stays within the target
            # directory. ``secure_filename`` already prevents traversal; this
            # check is defence in depth in case that behaviour ever changes.
            directory = os.path.abspath(self.directory)
            destination = os.path.abspath(
                os.path.join(directory, f'{timestamp}_{filename}'))
            if os.path.commonpath([directory, destination]) != directory:
                raise ValueError('Invalid file path.')

            # Store image to device
            file.save(destination)

        return now

    def data(self, req):
        """Generate results based on the stored data.

        Returns:
            dict: The results as a dictionary.
        """
        # Configuration check
        if self.enable_results:
            # Password check
            if not self.authorised(req):
                return {'valid': False, 'code': 401, 'message': 'Unauthorised access.'}

            if self.format in ['csv', 'json', 'sqlite', 'xml']:
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
                    elif self.format == 'xml':
                        self.df = pd.read_xml(path)
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

    def export(self, req):
        """Export the stored data.

        Returns:
            dict: The exported data as a dictionary.
        """
        # Configuration check
        if self.enable_export:
            # Password check
            if not self.authorised(req):
                return {'valid': False, 'code': 401, 'message': 'Unauthorised access.'}

            if self.format in ['csv', 'json', 'sqlite', 'xml']:
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
                    elif self.format == 'xml':
                        self.df = pd.read_xml(path)
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
