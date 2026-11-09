import io
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta

import pandas as pd
import yaml

from succulent.api import SucculentAPI
from succulent.explore import Explorer


PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32


def strict_json(response):
    """Parse a response like JavaScript's JSON.parse (no NaN/Infinity)."""
    def reject(constant):
        raise ValueError(f'Invalid JSON constant: {constant}')
    return json.loads(response.get_data(as_text=True), parse_constant=reject)


class ExploreTestCase(unittest.TestCase):
    """Base class: builds an API from a configuration dictionary."""

    def make_api(self, config, format='csv'):
        handle, path = tempfile.mkstemp(suffix='.yml')
        with os.fdopen(handle, 'w') as f:
            yaml.safe_dump(config, f)
        self.addCleanup(os.remove, path)
        api = SucculentAPI(config=path, format=format)
        self.addCleanup(shutil.rmtree, api.processing.directory, True)
        shutil.rmtree(api.processing.directory, ignore_errors=True)
        return api, api.app.test_client()


TABLE_CONFIG = {
    'timestamp': True,
    'data': [
        {'name': 'temperature', 'min': 15, 'max': 30},
        {'name': 'humidity'},
        {'name': 'status'},
    ],
    'results': [{'enable': True}, {'export': True}],
    'explore': [{'enable': True}, {'refresh': 5}],
}


class TestExploreConfiguration(ExploreTestCase):

    def test_disabled_by_default(self):
        config = dict(TABLE_CONFIG)
        del config['explore']
        api, client = self.make_api(config)
        self.assertIsNone(api.explorer)
        response = client.get('/explore')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {'message': 'Not Found.'})

    def test_enable_false(self):
        config = dict(TABLE_CONFIG, explore=[{'enable': False}])
        api, client = self.make_api(config)
        self.assertEqual(client.get('/explore').status_code, 404)

    def test_mapping_style_and_refresh(self):
        config = dict(TABLE_CONFIG, explore={'enable': True, 'refresh': 0})
        api, client = self.make_api(config)
        self.assertEqual(api.explorer.refresh, 0)
        self.assertIn(b'data-refresh="0"', client.get('/explore').data)

    def test_invalid_settings(self):
        for value in [[{'enable': True}, {'refresh': -1}], [{'enable': True}, {'refresh': 'fast'}], 'yes']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Explorer.settings(value) if isinstance(value, str) else Explorer(None, value)

    def test_existing_endpoints_unchanged(self):
        api, client = self.make_api(TABLE_CONFIG)
        self.assertEqual(client.post('/measure', json={'temperature': 20}).status_code, 200)
        self.assertEqual(client.get('/data').status_code, 200)
        self.assertEqual(client.get('/').status_code, 200)


class TestExplorePage(ExploreTestCase):

    def setUp(self):
        self.api, self.client = self.make_api(TABLE_CONFIG)

    def test_page_and_assets(self):
        response = self.client.get('/explore')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith('text/html'))
        html = response.get_data(as_text=True)
        self.assertIn('/explore/static/explore.js', html)
        self.assertIn('/explore/export', html)
        self.assertNotIn('style=', html)

        for asset in ['explore.js', 'explore.css']:
            with self.subTest(asset=asset):
                response = self.client.get(f'/explore/static/{asset}')
                self.assertEqual(response.status_code, 200)
                expected = 'application/javascript' if asset.endswith('.js') else 'text/css'
                self.assertTrue(response.content_type.startswith(expected))

    def test_security_headers(self):
        response = self.client.get('/explore')
        policy = response.headers['Content-Security-Policy']
        self.assertIn("script-src 'self'", policy)
        self.assertIn("style-src 'self'", policy)
        self.assertNotIn('unsafe-inline', policy)
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_no_export_button_when_export_disabled(self):
        config = dict(TABLE_CONFIG, results=[{'enable': True}])
        api, client = self.make_api(config)
        self.assertNotIn('/explore/export', client.get('/explore').get_data(as_text=True))
        self.assertEqual(client.get('/explore/export').status_code, 400)


class TestExploreData(ExploreTestCase):

    def setUp(self):
        self.api, self.client = self.make_api(TABLE_CONFIG)

    def write_rows(self, rows):
        os.makedirs(self.api.processing.directory, exist_ok=True)
        pd.DataFrame(rows).to_csv(os.path.join(self.api.processing.directory, 'data.csv'), index=False)

    def test_no_data(self):
        data = strict_json(self.client.get('/explore/api/data'))
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['table']['rows'], [])
        self.assertEqual([c['name'] for c in data['columns']], ['temperature', 'humidity', 'status'])

    def test_summary(self):
        # /measure rejects values outside min/max, so the out-of-range row is
        # written directly (as for data stored before the limits were set)
        now = datetime.now()
        stamp = lambda minutes: (now - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
        self.write_rows([
            {'temperature': 20, 'humidity': 40, 'status': 'ok', 'timestamp': stamp(20)},
            {'temperature': 35, 'humidity': 41, 'status': 'ok', 'timestamp': stamp(10)},
        ])
        body = {'temperature': 22, 'status': '<script>alert(1)</script>'}
        self.assertEqual(self.client.post('/measure', json=body).status_code, 200)

        response = self.client.get('/explore/api/data')
        self.assertEqual(response.status_code, 200)
        data = strict_json(response)
        columns = {c['name']: c for c in data['columns']}

        self.assertEqual(data['count'], 3)
        self.assertTrue(data['timestamp'])
        self.assertEqual(data['refresh'], 5)
        self.assertEqual(columns['temperature']['min'], 15.0)
        self.assertEqual(columns['temperature']['max'], 30.0)
        self.assertEqual(columns['temperature']['outside'], 1)
        self.assertTrue(columns['temperature']['numeric'])
        self.assertFalse(columns['status']['numeric'])

        # Missing in the last measurement: last is null, previous value is kept
        self.assertIsNone(columns['humidity']['last'])
        self.assertEqual(columns['humidity']['last_valid'], 41)
        self.assertEqual(columns['humidity']['missing'], 1)

        # Device values are returned as plain data (rendered as text by the page)
        self.assertEqual(columns['status']['last'], '<script>alert(1)</script>')

        self.assertEqual(data['series']['values']['humidity'], [40, 41, None])
        self.assertNotIn('status', data['series']['values'])
        self.assertEqual(data['table']['columns'], ['timestamp', 'temperature', 'humidity', 'status'])
        self.assertEqual([r['temperature'] for r in data['table']['rows']], [22, 35, 20])

    def test_ranges(self):
        now = datetime.now().replace(microsecond=0)
        self.write_rows([
            {'temperature': 20, 'humidity': 1, 'status': 'a',
             'timestamp': (now - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S')},
            {'temperature': 21, 'humidity': 2, 'status': 'b',
             'timestamp': (now - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S')},
            {'temperature': 22, 'humidity': 3, 'status': 'c',
             'timestamp': (now - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')},
        ])
        counts = {r: strict_json(self.client.get(f'/explore/api/data?range={r}'))['count']
                  for r in ['1h', '24h', '7d', '30d', 'all']}
        self.assertEqual(counts, {'1h': 1, '24h': 2, '7d': 2, '30d': 3, 'all': 3})

        data = strict_json(self.client.get('/explore/api/data?range=all'))
        self.assertEqual(data['ranges'], ['1h', '24h', '7d', '30d', 'all'])

        response = self.client.get('/explore/api/data?range=year')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid range', response.get_json()['message'])

    def test_without_timestamps(self):
        config = dict(TABLE_CONFIG, timestamp=False)
        api, client = self.make_api(config)
        client.post('/measure', json={'temperature': 20})
        client.post('/measure', json={'temperature': 21})
        data = strict_json(client.get('/explore/api/data'))
        self.assertFalse(data['timestamp'])
        self.assertEqual(data['ranges'], [])
        self.assertEqual(data['series']['x'], [1, 2])
        self.assertEqual(data['table']['columns'], ['temperature', 'humidity', 'status'])

    def test_long_series_are_averaged(self):
        self.api.explorer.MAX_POINTS = 10
        start = datetime.now() - timedelta(hours=10)
        self.write_rows([{'temperature': i, 'humidity': 1, 'status': 'x',
                          'timestamp': (start + timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S')}
                         for i in range(100)])
        data = strict_json(self.client.get('/explore/api/data?range=all'))
        self.assertEqual(data['count'], 100)
        self.assertEqual(data['bucket'], 10)
        self.assertEqual(len(data['series']['values']['temperature']), 10)
        self.assertEqual(data['series']['values']['temperature'][0], 4.5)
        self.assertEqual(len(data['table']['rows']), 10)
        self.assertEqual(data['interval'], 60.0)

    def test_export(self):
        self.client.post('/measure', json={'temperature': 20})
        response = self.client.get('/explore/export')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'text/csv')
        self.assertTrue(response.get_data(as_text=True).startswith('temperature,humidity,status,timestamp'))

    def test_image_endpoints_not_available(self):
        self.assertEqual(self.client.get('/explore/api/images').status_code, 400)


class TestExplorePassword(ExploreTestCase):

    def setUp(self):
        self.api, self.client = self.make_api(dict(TABLE_CONFIG, password='s3cret'))
        self.client.post('/measure', json={'temperature': 20}, headers={'X-API-Key': 's3cret'})

    def test_requires_login(self):
        response = self.client.get('/explore')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['Location'].endswith('/explore/login'))
        self.assertEqual(self.client.get('/explore/api/data').status_code, 401)
        self.assertEqual(self.client.get('/explore/export').status_code, 401)

    def test_query_password_is_not_accepted(self):
        # The password must not end up in URLs (browser history, logs)
        self.assertEqual(self.client.get('/explore/api/data?password=s3cret').status_code, 401)

    def test_wrong_password(self):
        response = self.client.post('/explore/login', data={'password': 'wrong'})
        self.assertEqual(response.status_code, 401)
        self.assertIn('Wrong password', response.get_data(as_text=True))
        self.assertEqual(self.client.get('/explore/api/data').status_code, 401)

    def test_login_and_logout(self):
        self.assertEqual(self.client.get('/explore/login').status_code, 200)
        response = self.client.post('/explore/login', data={'password': 's3cret'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get('/explore').status_code, 200)
        self.assertEqual(self.client.get('/explore/api/data').status_code, 200)

        self.client.post('/explore/logout')
        self.assertEqual(self.client.get('/explore/api/data').status_code, 401)

    def test_header_for_scripts(self):
        for headers in [{'X-API-Key': 's3cret'}, {'Authorization': 'Bearer s3cret'}]:
            with self.subTest(headers=headers):
                self.assertEqual(self.client.get('/explore/api/data', headers=headers).status_code, 200)
        self.assertEqual(self.client.get('/explore/api/data', headers={'X-API-Key': 'x'}).status_code, 401)

    def test_numeric_password(self):
        api, client = self.make_api(dict(TABLE_CONFIG, password=1234))
        self.assertEqual(client.post('/explore/login', data={'password': '1234'}).status_code, 302)

    def test_secret_key_from_config(self):
        api, client = self.make_api(dict(TABLE_CONFIG, password='x', secret_key='fixed-key'))
        self.assertEqual(api.app.secret_key, 'fixed-key')


class TestExploreImages(ExploreTestCase):

    def setUp(self):
        self.api, self.client = self.make_api(
            {'data': [{'key': 'image'}], 'explore': [{'enable': True}]}, format='image')

    def upload(self, name):
        return self.client.post('/measure', data={'image': (io.BytesIO(PNG), name)},
                                content_type='multipart/form-data')

    def test_gallery(self):
        self.assertIn(b'data-gallery="true"', self.client.get('/explore').data)

        data = strict_json(self.client.get('/explore/api/images'))
        self.assertEqual(data['count'], 0)

        self.assertEqual(self.upload('a.png').status_code, 200)
        self.assertEqual(self.upload('b.png').status_code, 200)

        data = strict_json(self.client.get('/explore/api/images'))
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['count_24h'], 2)
        self.assertEqual(data['bytes'], 2 * len(PNG))

        image = self.client.get(data['images'][0]['url'])
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image.data, PNG)
        self.assertIn('sandbox', image.headers['Content-Security-Policy'])

        self.assertEqual(self.client.get('/explore/api/data').status_code, 400)

    def test_only_stored_images_are_served(self):
        self.upload('a.png')
        os.makedirs(self.api.processing.directory, exist_ok=True)
        with open(os.path.join(self.api.processing.directory, 'notes.txt'), 'w') as f:
            f.write('secret')
        for name in ['notes.txt', '..%2Fapi.py', 'missing.png']:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(f'/explore/images/{name}').status_code, 404)
        names = [f['name'] for f in strict_json(self.client.get('/explore/api/images'))['images']]
        self.assertNotIn('notes.txt', names)


if __name__ == '__main__':
    unittest.main()
