"""Web dashboard for exploring the collected data (``/explore``).

The dashboard is optional and separate from the data collection API: it is
only registered when ``explore`` is enabled in the configuration, it does not
change how data is collected or stored, and it only reads the stored data.

Example configuration::

    explore:
      - enable: true
      - refresh: 10   # auto-refresh interval in seconds (optional)
"""
import hmac
import math
import os
import secrets
import sqlite3
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from flask import (Blueprint, abort, jsonify, make_response, redirect,
                   render_template, request, send_from_directory, session,
                   url_for)
from werkzeug.utils import secure_filename


class Explorer:
    """Dashboard for exploring the collected data in a web browser.

    Args:
        processing (Processing): The processing instance of the API, used
            for the format, columns, boundaries, password and storage
            location. The data itself is only read.
        config (dict): The ``explore`` section of the configuration.

    Attributes:
        processing (Processing): The processing instance of the API.
        refresh (int): Auto-refresh interval in seconds (0 disables it).
        blueprint (Blueprint): Flask blueprint with the dashboard routes.
    """

    # Time ranges offered in the dashboard, mapped to their length
    RANGES = {
        '1h': timedelta(hours=1),
        '24h': timedelta(hours=24),
        '7d': timedelta(days=7),
        '30d': timedelta(days=30),
        'all': None,
    }

    # Maximum number of points per chart; longer series are averaged in
    # equal buckets so the browser stays fast
    MAX_POINTS = 1000

    # Number of raw rows shown in the table of latest measurements
    LATEST_ROWS = 10

    # Session key set after a successful password prompt
    SESSION_KEY = 'succulent_explore'

    # Data formats that store measurements in a table
    TABLE_FORMATS = ['csv', 'json', 'sqlite', 'xml']

    def __init__(self, processing, config=None):
        self.processing = processing
        self.refresh = 10

        settings = self.settings(config)
        if 'refresh' in settings:
            refresh = settings['refresh']
            if not isinstance(refresh, (int, float)) or isinstance(refresh, bool) or refresh < 0:
                raise ValueError('"refresh" in "explore" must be a number of seconds (0 disables it).')
            self.refresh = int(refresh)

        self.blueprint = Blueprint(
            'explore', __name__,
            template_folder='explore_templates',
            static_folder='explore_static',
            static_url_path='/explore/static')

        bp = self.blueprint
        bp.add_url_rule('/explore', 'page', self.page, methods=['GET'])
        bp.add_url_rule('/explore/login', 'login', self.login, methods=['GET', 'POST'])
        bp.add_url_rule('/explore/logout', 'logout', self.logout, methods=['POST'])
        bp.add_url_rule('/explore/api/data', 'api_data', self.api_data, methods=['GET'])
        bp.add_url_rule('/explore/export', 'export', self.export, methods=['GET'])
        bp.add_url_rule('/explore/api/images', 'api_images', self.api_images, methods=['GET'])
        bp.add_url_rule('/explore/images/<name>', 'image', self.image, methods=['GET'])
        bp.after_request(self.security_headers)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @staticmethod
    def settings(config):
        """Merge the ``explore`` section into one dictionary.

        Both the list style used by other sections
        (``[{'enable': True}, {'refresh': 10}]``) and a plain mapping
        (``{'enable': True, 'refresh': 10}``) are accepted.

        Args:
            config (list or dict or None): The ``explore`` section.

        Raises:
            ValueError: The section has an unexpected shape.

        Returns:
            dict: The merged settings.
        """
        if config is None:
            return {}
        if isinstance(config, dict):
            return dict(config)
        if isinstance(config, list) and all(isinstance(item, dict) for item in config):
            merged = {}
            for item in config:
                merged.update(item)
            return merged
        raise ValueError('"explore" must be a list of settings, e.g. [{"enable": true}].')

    @classmethod
    def enabled(cls, config):
        """Check whether the dashboard is enabled in the configuration.

        Args:
            config (dict): The whole configuration.

        Returns:
            bool: True if ``explore`` has ``enable: true``.
        """
        return cls.settings(config.get('explore')).get('enable') is True

    def register(self, app):
        """Register the dashboard routes on a Flask application.

        A random secret key is set for the session cookie if the
        application has none. Sessions then last until the server
        restarts; set ``secret_key`` in the configuration to keep them.

        Args:
            app (Flask): The Flask application.

        Returns:
            None
        """
        if not app.secret_key:
            app.secret_key = secrets.token_hex(32)
        app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
        app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
        app.register_blueprint(self.blueprint)

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def allowed(self):
        """Check whether the current request may see the dashboard.

        Without a password everyone may. With a password, a browser needs
        a session from the password prompt; scripts may instead send the
        password in a header, as for ``/data``.

        Returns:
            bool: True if access is allowed.
        """
        if not self.processing.password:
            return True
        if session.get(self.SESSION_KEY) is True:
            return True
        return bool(request.headers.get('Authorization') or request.headers.get('X-API-Key')) \
            and self.processing.authorised(request)

    def login(self):
        """Show the password prompt (GET) or check the password (POST).

        Returns:
            Response: The prompt, or a redirect to the dashboard.
        """
        if not self.processing.password:
            return redirect(url_for('explore.page'))

        error = False
        if request.method == 'POST':
            supplied = request.form.get('password', '')
            expected = str(self.processing.password).encode('utf-8')
            if hmac.compare_digest(supplied.encode('utf-8'), expected):
                session.clear()
                session[self.SESSION_KEY] = True
                return redirect(url_for('explore.page'))
            error = True

        return render_template('explore_login.html', error=error), 401 if error else 200

    def logout(self):
        """End the dashboard session.

        Returns:
            Response: A redirect to the password prompt.
        """
        session.pop(self.SESSION_KEY, None)
        return redirect(url_for('explore.login'))

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def page(self):
        """Show the dashboard.

        Returns:
            Response: The dashboard page, or a redirect to the prompt.
        """
        if not self.allowed():
            return redirect(url_for('explore.login'))

        can_export = (self.processing.format in self.TABLE_FORMATS
                      and getattr(self.processing, 'enable_export', False))

        return render_template(
            'explore.html',
            format=self.processing.format,
            refresh=self.refresh,
            protected=bool(self.processing.password),
            gallery=self.processing.format == 'image',
            export_url=url_for('explore.export') if can_export else None)

    def export(self):
        """Download the stored data as CSV from the dashboard.

        Available only when export is enabled in the configuration
        (``results: - export: true``), like ``/export``; the dashboard
        session is accepted instead of a password header.

        Returns:
            Response: The CSV file.
        """
        if not self.allowed():
            return jsonify({'message': 'Unauthorised access.'}), 401
        if (self.processing.format not in self.TABLE_FORMATS
                or not getattr(self.processing, 'enable_export', False)):
            return jsonify({'message': 'Exporting is not enabled in your current configuration.'}), 400

        df = self.load()
        if df.empty:
            return jsonify({'message': 'No data available.'}), 400

        response = make_response(df.to_csv(index=False))
        response.headers['Content-Disposition'] = 'attachment; filename=data.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def load(self):
        """Read the stored measurements.

        Returns:
            pandas.DataFrame: The stored data (empty if there is none yet).
        """
        path = os.path.join(self.processing.directory, f'data.{self.processing.format}')
        if not os.path.exists(path):
            return pd.DataFrame()

        fmt = self.processing.format
        if fmt == 'csv':
            return pd.read_csv(path, sep=',')
        if fmt == 'json':
            return pd.read_json(path, orient='records')
        if fmt == 'xml':
            return pd.read_xml(path)
        conn = sqlite3.connect(path)
        try:
            return pd.read_sql_query('SELECT * FROM data', conn)
        finally:
            conn.close()

    def bounds(self):
        """Map each column with a boundary to its minimum and maximum.

        Returns:
            dict: Column name mapped to ``{'min': ..., 'max': ...}``.
        """
        result = {}
        for item in self.processing.boundaries:
            for column, bound in item.items():
                result[column] = {
                    'min': float(bound['min']) if 'min' in bound else None,
                    'max': float(bound['max']) if 'max' in bound else None,
                }
        return result

    @staticmethod
    def clean(value):
        """Convert a value to something JSON can represent.

        Args:
            value: A value from a DataFrame.

        Returns:
            The value as a JSON-safe Python type (missing values as None).
        """
        if value is None:
            return None
        if isinstance(value, (pd.Timestamp, datetime)):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating, float)):
            return None if not math.isfinite(float(value)) else float(value)
        if isinstance(value, (np.bool_,)):
            return bool(value)
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        return value

    def api_data(self):
        """Return the data for the dashboard as JSON.

        Query parameters:
            range (str): One of ``1h``, ``24h``, ``7d``, ``30d`` or ``all``
                (default ``24h``). Only used when timestamps are stored.

        Returns:
            Response: JSON with the columns, statistics, chart series and
            the latest measurements.
        """
        if not self.allowed():
            return jsonify({'message': 'Unauthorised access.'}), 401
        if self.processing.format not in self.TABLE_FORMATS:
            return jsonify({'message': f'No table data for the "{self.processing.format}" format.'}), 400

        selected = request.args.get('range', '24h')
        if selected not in self.RANGES:
            return jsonify({'message': f'Invalid range: {selected} (use {", ".join(self.RANGES)}).'}), 400

        df = self.load()
        columns = list(self.processing.columns)
        for column in columns:
            if column not in df.columns:
                df[column] = np.nan
        has_time = self.processing.timestamp or 'timestamp' in df.columns

        times = None
        if has_time and 'timestamp' in df.columns and len(df):
            times = pd.to_datetime(df['timestamp'], errors='coerce')
            df = df.assign(_time=times).sort_values('_time', kind='stable')
            span = self.RANGES[selected]
            if span is not None and df['_time'].notna().any():
                df = df[df['_time'] >= df['_time'].max() - span]
            times = df['_time']

        bounds = self.bounds()
        info = []
        for column in columns:
            numbers = pd.to_numeric(df[column], errors='coerce')
            present = df[column].notna().sum()
            numeric = present > 0 and numbers.notna().sum() >= 0.8 * present
            item = {'name': column, 'numeric': bool(numeric),
                    'min': bounds.get(column, {}).get('min'),
                    'max': bounds.get(column, {}).get('max')}

            # Latest value, and the last value before it if it is missing
            values = df[column]
            item['last'] = self.clean(values.iloc[-1]) if len(values) else None
            valid = values[values.notna()]
            item['last_valid'] = self.clean(valid.iloc[-1]) if len(valid) else None
            item['last_valid_time'] = (self.clean(times.loc[valid.index[-1]])
                                       if times is not None and len(valid) else None)
            item['missing'] = int(values.isna().sum())

            outside = 0
            if numeric:
                if item['min'] is not None:
                    outside += int((numbers < item['min']).sum())
                if item['max'] is not None:
                    outside += int((numbers > item['max']).sum())
            item['outside'] = outside
            info.append(item)

        # Chart series, averaged in buckets when there are many points
        bucket = max(1, math.ceil(len(df) / self.MAX_POINTS))
        groups = np.arange(len(df)) // bucket
        series = {'x': [], 'values': {}}
        if len(df):
            if times is not None:
                series['x'] = [self.clean(t) for t in times.groupby(groups).first()]
            else:
                series['x'] = [int(i) + 1 for i in pd.Series(np.arange(len(df))).groupby(groups).first()]
            for item in info:
                if item['numeric']:
                    numbers = pd.to_numeric(df[item['name']], errors='coerce').reset_index(drop=True)
                    means = numbers.groupby(groups).mean()
                    series['values'][item['name']] = [self.clean(v) for v in means]

        # Latest raw rows, newest first
        shown = ['timestamp'] if has_time and 'timestamp' in df.columns else []
        shown += columns
        latest = []
        for _, row in df.tail(self.LATEST_ROWS).iloc[::-1].iterrows():
            latest.append({key: self.clean(row[key]) for key in shown})

        # Typical interval between measurements
        interval = None
        if times is not None and times.notna().sum() > 1:
            interval = float(times.dropna().diff().dropna().dt.total_seconds().median())

        return jsonify({
            'format': self.processing.format,
            'range': selected,
            'ranges': list(self.RANGES) if times is not None else [],
            'timestamp': times is not None,
            'refresh': self.refresh,
            'count': int(len(df)),
            'cells': int(len(df) * len(columns)),
            'bucket': bucket,
            'interval': interval,
            'last_time': self.clean(times.iloc[-1]) if times is not None and len(times) else None,
            'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'columns': info,
            'series': series,
            'table': {'columns': shown, 'rows': latest},
        })

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    def images(self):
        """List the stored images, newest first.

        Returns:
            list: Dictionaries with ``name``, ``size`` and ``time``.
        """
        directory = self.processing.directory
        if not os.path.isdir(directory):
            return []
        allowed = set(getattr(self.processing, 'allowed_extensions', []))
        files = []
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            extension = name.rpartition('.')[2].lower()
            if os.path.isfile(path) and extension in allowed:
                stat = os.stat(path)
                files.append({'name': name, 'size': stat.st_size, 'mtime': stat.st_mtime})
        files.sort(key=lambda f: (f['mtime'], f['name']), reverse=True)
        for f in files:
            f['time'] = datetime.fromtimestamp(f.pop('mtime')).strftime('%Y-%m-%d %H:%M:%S')
        return files

    def api_images(self):
        """Return the list of stored images as JSON.

        Returns:
            Response: JSON with the images and summary statistics.
        """
        if not self.allowed():
            return jsonify({'message': 'Unauthorised access.'}), 401
        if self.processing.format != 'image':
            return jsonify({'message': 'Images are only available for the "image" format.'}), 400

        files = self.images()
        now = datetime.now()
        recent = [f for f in files
                  if now - datetime.strptime(f['time'], '%Y-%m-%d %H:%M:%S') <= timedelta(hours=24)]
        for f in files:
            f['url'] = url_for('explore.image', name=f['name'])
        return jsonify({
            'format': 'image',
            'refresh': self.refresh,
            'count': len(files),
            'count_24h': len(recent),
            'bytes': sum(f['size'] for f in files),
            'allowed_extensions': list(getattr(self.processing, 'allowed_extensions', [])),
            'server_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'images': files,
        })

    def image(self, name):
        """Serve one stored image.

        Args:
            name (str): The file name.

        Returns:
            Response: The image file.
        """
        if not self.allowed():
            abort(401)
        if self.processing.format != 'image':
            abort(404)
        allowed = set(getattr(self.processing, 'allowed_extensions', []))
        if (secure_filename(name) != name
                or name.rpartition('.')[2].lower() not in allowed
                or not os.path.isfile(os.path.join(self.processing.directory, name))):
            abort(404)
        response = send_from_directory(os.path.abspath(self.processing.directory), name)
        # Never run anything an uploaded file might contain (e.g. an SVG)
        response.headers['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox"
        return response

    # ------------------------------------------------------------------
    # Headers
    # ------------------------------------------------------------------

    @staticmethod
    def security_headers(response):
        """Add security headers to every dashboard response.

        Scripts and styles are only loaded from the server itself, so the
        dashboard works without internet access and values sent by devices
        can never run as code in the browser.

        Args:
            response (Response): The response.

        Returns:
            Response: The response with security headers.
        """
        response.headers.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('Referrer-Policy', 'same-origin')
        if request.path.startswith('/explore/api') or request.path == '/explore':
            response.headers.setdefault('Cache-Control', 'no-store')
        return response
