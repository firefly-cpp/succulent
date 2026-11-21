import json
import multiprocessing
import os
import shutil
import sqlite3
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

import pandas as pd
import yaml

from succulent.api import SucculentAPI


CONFIG = {
    'data': [
        {'name': 'temperature', 'min': -20, 'max': 60},
        {'name': 'humidity'},
        {'name': 'sensor'},
    ],
    'results': [{'enable': True}],
}


class StorageTestCase(unittest.TestCase):
    """Base class: builds an API from a configuration dictionary."""

    def make_api(self, config=None, format='csv', clear=True):
        handle, path = tempfile.mkstemp(suffix='.yml')
        with os.fdopen(handle, 'w') as f:
            yaml.safe_dump(config or CONFIG, f)
        self.addCleanup(os.remove, path)
        api = SucculentAPI(config=path, format=format)
        if clear:
            shutil.rmtree(api.processing.directory, ignore_errors=True)
        self.addCleanup(shutil.rmtree, api.processing.directory, True)
        return api, api.app.test_client()

    def path(self, api):
        return os.path.join(api.processing.directory, f'data.{api.processing.format}')

    def post(self, client, **values):
        response = client.post('/measure', json=values)
        self.assertEqual(response.status_code, 200, response.get_json())
        return response


class TestCsvAppend(StorageTestCase):

    def setUp(self):
        self.api, self.client = self.make_api()

    def read(self):
        with open(self.path(self.api), newline='') as f:
            return f.read().splitlines()

    def test_rows_are_appended(self):
        self.post(self.client, temperature=20, humidity=40, sensor='a')
        self.post(self.client, temperature=21.5, sensor='b')
        self.post(self.client, humidity=42)
        self.assertEqual(self.read(), [
            'temperature,humidity,sensor',
            '20,40,a',
            '21.5,,b',
            ',42,',
        ])

    def test_stored_data_is_not_read(self):
        self.post(self.client, temperature=20)
        real = pd.read_csv
        calls = []

        def spy(*args, **kwargs):
            calls.append(kwargs.get('nrows'))
            return real(*args, **kwargs)

        with mock.patch('succulent.processing.pd.read_csv', side_effect=spy):
            self.post(self.client, temperature=21)
        # Only the header is read
        self.assertEqual(calls, [0])

    def test_earlier_values_are_not_changed(self):
        # Before, the whole file was read and written again on every
        # measurement, so e.g. "007" became 7 and 20 became 20.0
        self.post(self.client, temperature=20, sensor='007')
        self.post(self.client, temperature=21.5, sensor='008')
        self.post(self.client, sensor='009')
        self.assertEqual(self.read()[1:], ['20,,007', '21.5,,008', ',,009'])

    def test_new_column_in_configuration(self):
        self.post(self.client, temperature=20)
        config = dict(CONFIG, data=CONFIG['data'] + [{'name': 'light'}])
        api, client = self.make_api(config, clear=False)
        self.post(client, temperature=21, light=300)
        self.post(client, temperature=22, light=310)
        self.assertEqual(self.read(), [
            'temperature,humidity,sensor,light',
            '20,,,',
            '21,,,300',
            '22,,,310',
        ])

    def test_timestamp_enabled_later(self):
        self.post(self.client, temperature=20)
        api, client = self.make_api(dict(CONFIG, timestamp=True), clear=False)
        self.post(client, temperature=21)
        lines = self.read()
        self.assertEqual(lines[0], 'temperature,humidity,sensor,timestamp')
        self.assertEqual(lines[1], '20,,,')
        self.assertRegex(lines[2], r'^21,,,\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')

    def test_column_removed_from_configuration(self):
        self.post(self.client, temperature=20, sensor='a')
        config = dict(CONFIG, data=CONFIG['data'][:2])
        api, client = self.make_api(config, clear=False)
        self.post(client, temperature=21)
        # The stored column stays, empty for new rows
        self.assertEqual(self.read(), ['temperature,humidity,sensor', '20,,a', '21,,'])

    def test_file_without_trailing_newline(self):
        os.makedirs(self.api.processing.directory, exist_ok=True)
        with open(self.path(self.api), 'w', newline='') as f:
            f.write('temperature,humidity,sensor\n20,40,a')
        self.post(self.client, temperature=21)
        self.assertEqual(self.read(), ['temperature,humidity,sensor', '20,40,a', '21,,'])

    def test_empty_file(self):
        os.makedirs(self.api.processing.directory, exist_ok=True)
        open(self.path(self.api), 'w').close()
        self.post(self.client, temperature=21)
        self.assertEqual(self.read(), ['temperature,humidity,sensor', '21,,'])

    def test_values_with_commas_and_quotes(self):
        self.post(self.client, sensor='a, "b"')
        self.post(self.client, sensor='c')
        data = self.client.get('/data').get_json()['data']
        self.assertEqual([row['sensor'] for row in data], ['a, "b"', 'c'])

    def test_last_row_is_kept_in_memory(self):
        self.post(self.client, temperature=20)
        self.post(self.client, temperature=21)
        self.assertEqual(len(self.api.processing.df), 1)
        self.assertEqual(self.api.processing.df.iloc[-1]['temperature'], 21)


class TestSqliteAppend(StorageTestCase):

    def setUp(self):
        self.api, self.client = self.make_api(format='sqlite')

    def rows(self, api=None):
        conn = sqlite3.connect(self.path(api or self.api))
        try:
            cursor = conn.execute('SELECT * FROM data')
            return [d[0] for d in cursor.description], cursor.fetchall()
        finally:
            conn.close()

    def test_rows_are_inserted(self):
        self.post(self.client, temperature=20, humidity=40, sensor='a')
        self.post(self.client, temperature=21.5, sensor='b')
        columns, rows = self.rows()
        self.assertEqual(columns, ['temperature', 'humidity', 'sensor'])
        self.assertEqual(rows, [(20, 40, 'a'), (21.5, None, 'b')])

    def test_stored_data_is_not_read(self):
        self.post(self.client, temperature=20)
        with mock.patch('succulent.processing.pd.read_sql_query') as read:
            self.post(self.client, temperature=21)
        read.assert_not_called()
        self.assertEqual(len(self.rows()[1]), 2)

    def test_new_column_in_configuration(self):
        self.post(self.client, temperature=20)
        config = dict(CONFIG, timestamp=True, data=CONFIG['data'] + [{'name': 'light "lux"'}])
        api, client = self.make_api(config, format='sqlite', clear=False)
        self.post(client, temperature=21, **{'light "lux"': 300})
        columns, rows = self.rows(api)
        self.assertEqual(columns, ['temperature', 'humidity', 'sensor', 'light "lux"', 'timestamp'])
        self.assertEqual(rows[0], (20, None, None, None, None))
        self.assertEqual(rows[1][:4], (21, None, None, 300))

    def test_lists_and_objects_are_stored_as_json(self):
        self.post(self.client, sensor={'id': 7, 'tags': ['a', 'b']})
        self.post(self.client, sensor=[1, 2])
        self.assertEqual([r[2] for r in self.rows()[1]], ['{"id": 7, "tags": ["a", "b"]}', '[1, 2]'])

    def test_first_value_missing_keeps_numbers(self):
        self.post(self.client, sensor='a')
        self.post(self.client, temperature=21.5, humidity=40)
        self.assertEqual(self.rows()[1][1], (21.5, 40, None))
        data = self.client.get('/data').get_json()['data']
        self.assertEqual(data[1]['temperature'], 21.5)

    def test_existing_database_from_older_version(self):
        # Table created by pandas (with declared types), as before
        os.makedirs(self.api.processing.directory, exist_ok=True)
        conn = sqlite3.connect(self.path(self.api))
        pd.DataFrame([{'temperature': 20.0, 'humidity': 40.0, 'sensor': 'a'}]).to_sql('data', conn, index=False)
        conn.close()
        self.post(self.client, temperature=21, sensor='b')
        self.assertEqual(self.rows()[1], [(20.0, 40.0, 'a'), (21.0, None, 'b')])

    def test_data_endpoint(self):
        self.post(self.client, temperature=20, sensor='a')
        self.post(self.client, temperature=21, sensor='b')
        data = self.client.get('/data').get_json()['data']
        self.assertEqual([r['sensor'] for r in data], ['a', 'b'])


class DocumentAppendMixin:
    """Shared tests for the JSON and XML formats (one document per file)."""

    FORMAT = None
    READER = None   # pandas reader that would read the whole file

    def setUp(self):
        self.api, self.client = self.make_api(format=self.FORMAT)

    def full_write(self, rows, path):
        df = pd.DataFrame(rows, dtype=object)
        if self.FORMAT == 'json':
            df.to_json(path, orient='records', indent=4)
        else:
            df.to_xml(path, index=False)

    def stored(self):
        with open(self.path(self.api), 'rb') as f:
            return f.read()

    def test_same_file_as_writing_everything_again(self):
        rows = [
            {'temperature': 20.5, 'humidity': None, 'sensor': 'a'},
            {'temperature': 21.5, 'humidity': 40, 'sensor': 'b <&> "č" ] </data> }'},
            {'temperature': None, 'humidity': 41.25, 'sensor': 'ž' * 20000},
            {'temperature': -3.5, 'humidity': None, 'sensor': None},
        ]
        for row in rows:
            self.post(self.client, **{k: v for k, v in row.items() if v is not None})
        reference = os.path.join(self.api.processing.directory, 'reference')
        self.full_write(rows, reference)
        with open(reference, 'rb') as f:
            self.assertEqual(self.stored(), f.read())

        data = self.client.get('/data').get_json()['data']
        self.assertEqual([r['temperature'] for r in data], [20.5, 21.5, None, -3.5])

    def test_stored_data_is_not_read(self):
        self.post(self.client, temperature=20)
        with mock.patch(f'succulent.processing.pd.{self.READER}') as read:
            self.post(self.client, temperature=21)
            self.post(self.client, temperature=22)
        read.assert_not_called()
        data = self.client.get('/data').get_json()['data']
        self.assertEqual([r['temperature'] for r in data], [20, 21, 22])

    def test_file_from_older_version(self):
        # Written as a whole by pandas, as older versions did on every measurement
        os.makedirs(self.api.processing.directory, exist_ok=True)
        self.full_write([{'temperature': 20.0, 'humidity': 40.0, 'sensor': 'a'}], self.path(self.api))
        self.post(self.client, temperature=21, sensor='b')
        data = self.client.get('/data').get_json()['data']
        self.assertEqual([r['sensor'] for r in data], ['a', 'b'])

    def test_new_column_in_configuration(self):
        self.post(self.client, temperature=20)
        config = dict(CONFIG, timestamp=True, data=CONFIG['data'] + [{'name': 'light'}])
        api, client = self.make_api(config, format=self.FORMAT, clear=False)
        self.post(client, temperature=21, light=300)
        self.post(client, temperature=22, light=310)
        data = client.get('/data').get_json()['data']
        self.assertEqual([r['light'] for r in data], [None, 300, 310])
        self.assertIsNone(data[0]['timestamp'])
        self.assertIsNotNone(data[2]['timestamp'])

    def test_column_removed_from_configuration(self):
        self.post(self.client, temperature=20, sensor='a')
        config = dict(CONFIG, data=CONFIG['data'][:2])
        api, client = self.make_api(config, format=self.FORMAT, clear=False)
        with mock.patch(f'succulent.processing.pd.{self.READER}') as read:
            self.post(client, temperature=21)
        read.assert_not_called()
        data = client.get('/data').get_json()['data']
        self.assertEqual([r['sensor'] for r in data], ['a', None])

    def test_unexpected_end_of_file_is_rewritten(self):
        self.post(self.client, temperature=20)
        with open(self.path(self.api), 'ab') as f:
            f.write(b'\n\n   \n')     # trailing whitespace is fine
        self.post(self.client, temperature=21)
        self.assertEqual(len(self.client.get('/data').get_json()['data']), 2)

    def test_windows_line_endings(self):
        os.makedirs(self.api.processing.directory, exist_ok=True)
        path = self.path(self.api)
        self.full_write([{'temperature': 20.0, 'humidity': None, 'sensor': 'a'}], path)
        with open(path, 'rb') as f:
            content = f.read().replace(b'\n', b'\r\n')
        with open(path, 'wb') as f:
            f.write(content)
        self.post(self.client, temperature=21, sensor='b')
        stored = self.stored()
        self.assertNotIn(b'\n', stored.replace(b'\r\n', b''))
        data = self.client.get('/data').get_json()['data']
        self.assertEqual([r['sensor'] for r in data], ['a', 'b'])

    def test_empty_file(self):
        os.makedirs(self.api.processing.directory, exist_ok=True)
        open(self.path(self.api), 'w').close()
        self.post(self.client, temperature=21)
        self.assertEqual(len(self.client.get('/data').get_json()['data']), 1)


class TestJsonAppend(DocumentAppendMixin, StorageTestCase):
    FORMAT = 'json'
    READER = 'read_json'

    def test_compact_json_file(self):
        # A valid JSON array written without indentation, e.g. by another tool
        os.makedirs(self.api.processing.directory, exist_ok=True)
        with open(self.path(self.api), 'w') as f:
            f.write('[{"temperature":20,"humidity":null,"sensor":"a"}]')
        self.post(self.client, temperature=21, sensor='b')
        with open(self.path(self.api)) as f:
            records = json.load(f)
        self.assertEqual([r['sensor'] for r in records], ['a', 'b'])

    def test_nested_values_in_first_record(self):
        self.post(self.client, sensor={'id': 1, 'tags': ['a', '}']})
        with mock.patch('succulent.processing.pd.read_json') as read:
            self.post(self.client, sensor='b')
        read.assert_not_called()
        with open(self.path(self.api)) as f:
            records = json.load(f)
        self.assertEqual(records[0]['sensor'], {'id': 1, 'tags': ['a', '}']})
        self.assertEqual(records[1]['sensor'], 'b')

    def test_not_an_array_is_rewritten(self):
        os.makedirs(self.api.processing.directory, exist_ok=True)
        with open(self.path(self.api), 'w') as f:
            f.write('[]')
        self.post(self.client, temperature=21)
        with open(self.path(self.api)) as f:
            self.assertEqual(len(json.load(f)), 1)


class TestXmlAppend(DocumentAppendMixin, StorageTestCase):
    FORMAT = 'xml'
    READER = 'read_xml'

    def test_file_stays_valid_xml(self):
        for i in range(3):
            self.post(self.client, temperature=20 + i, sensor=f'<s{i}>')
        root = ET.parse(self.path(self.api)).getroot()
        self.assertEqual(root.tag, 'data')
        self.assertEqual([row.find('sensor').text for row in root], ['<s0>', '<s1>', '<s2>'])


def store_in_process(config_path, fmt, number, count):
    """Send measurements from a separate process (like a gunicorn worker)."""
    from succulent.api import SucculentAPI
    client = SucculentAPI(config=config_path, format=fmt).app.test_client()
    failed = 0
    for i in range(count):
        response = client.post('/measure', json={'temperature': number, 'humidity': i})
        failed += response.status_code != 200
    return failed


class TestConcurrentWrites(StorageTestCase):
    """Measurements sent at the same time must all be stored."""

    THREADS = 8
    PER_THREAD = 15

    def run_threads(self, api):
        errors = []

        def worker(n):
            client = api.app.test_client()
            for i in range(self.PER_THREAD):
                response = client.post('/measure', json={'temperature': n, 'humidity': i})
                if response.status_code != 200:
                    errors.append(response.get_json())

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(self.THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])

    def test_all_rows_are_stored(self):
        for fmt in ['csv', 'sqlite', 'json', 'xml']:
            with self.subTest(format=fmt):
                api, client = self.make_api(format=fmt)
                self.run_threads(api)
                data = client.get('/data').get_json()['data']
                self.assertEqual(len(data), self.THREADS * self.PER_THREAD)
                pairs = {(int(r['temperature']), int(r['humidity'])) for r in data}
                self.assertEqual(len(pairs), self.THREADS * self.PER_THREAD)
                shutil.rmtree(api.processing.directory, ignore_errors=True)

    def test_all_rows_are_stored_from_several_processes(self):
        processes, per_process = 4, 20
        for fmt in ['csv', 'sqlite', 'json', 'xml']:
            with self.subTest(format=fmt):
                handle, config_path = tempfile.mkstemp(suffix='.yml')
                with os.fdopen(handle, 'w') as f:
                    yaml.safe_dump(CONFIG, f)
                self.addCleanup(os.remove, config_path)
                api = SucculentAPI(config=config_path, format=fmt)
                shutil.rmtree(api.processing.directory, ignore_errors=True)
                self.addCleanup(shutil.rmtree, api.processing.directory, True)

                context = multiprocessing.get_context('spawn')
                with context.Pool(processes) as pool:
                    failed = pool.starmap(store_in_process,
                                          [(config_path, fmt, n, per_process) for n in range(processes)])
                self.assertEqual(sum(failed), 0)

                data = api.app.test_client().get('/data').get_json()['data']
                pairs = {(int(r['temperature']), int(r['humidity'])) for r in data}
                self.assertEqual(len(data), processes * per_process)
                self.assertEqual(len(pairs), processes * per_process)
                shutil.rmtree(api.processing.directory, ignore_errors=True)

    def test_reading_while_writing(self):
        api, client = self.make_api()
        self.post(client, temperature=1)
        failures = []
        stop = threading.Event()

        def reader():
            reader_client = api.app.test_client()
            while not stop.is_set():
                response = reader_client.get('/data')
                if response.status_code != 200:
                    failures.append(response.get_json())

        threads = [threading.Thread(target=reader) for _ in range(2)]
        for t in threads:
            t.start()
        try:
            self.run_threads(api)
        finally:
            stop.set()
            for t in threads:
                t.join()
        self.assertEqual(failures, [])


if __name__ == '__main__':
    unittest.main()
