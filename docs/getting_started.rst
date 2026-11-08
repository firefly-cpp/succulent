Getting started
===============

This section demonstrates the usage of the succulent framework.

Installation
------------

pip
~~~

To install ``succulent`` with pip, use:

.. code:: bash

    pip install succulent

Alpine Linux
~~~~~~~~~~~~

To install ``succulent`` on Alpine Linux, use:

.. code:: bash

    $ apk add py3-succulent

Arch Linux
~~~~~~~~~~

To install ``succulent`` on Arch Linux, use an `AUR helper <https://wiki.archlinux.org/title/AUR_helpers>`_:

.. code:: bash

    $ yay -Syyu python-succulent

Fedora Linux

To install ``succulent`` on Fedora, use:

.. code:: bash

    $ dnf install python3-succulent

Usage
-----

Example
~~~~~~~

.. code:: python

    from succulent.api import SucculentAPI
    api = SucculentAPI(host='0.0.0.0', port=8080, config='configuration.yml', format='csv')
    api.start()

Configuration
-------------

Data collection
~~~~~~~~~~~~~~~

In the root directory, create a ``configuration.yml`` file and define the following:

.. code:: yaml

    data:
      - name: # Measure name
        min:  # Minimum value (optional)
        max:  # Maximum value (optional)

To collect images, create a ``configuration.yml`` file in the root directory and define the following:

.. code:: yaml

    data:
      - key: # Key in POST request
        allowed_extensions: ['jpg', 'png'] # Optional, see below

Only images are accepted. By default, the allowed extensions are ``jpg``, ``jpeg``, ``png``, ``gif``, ``bmp``, ``webp``, ``tif`` and ``tiff``; use ``allowed_extensions`` to narrow or extend this list. For these image types, the content of the file is checked as well, so a file renamed to ``.jpg`` that is not a JPEG image is rejected. Other extensions you allow (e.g. ``heic``) are checked by extension only. A file without an extension (e.g. from an ESP32-CAM) is accepted if its content is an allowed image, and the matching extension is added. Rejected uploads return a ``400`` response with the reason. Images are stored as ``<timestamp>_<filename>``; an image with the same name in the same second gets a counter (e.g. ``_1``) instead of overwriting the earlier one.

To store data collection timestamps, define the following setting in the ``configuration.yml`` file in the root directory:

.. code:: yaml

    timestamp: true # false by default

To access the URL for data collection, send a GET request (or navigate) to `http://localhost:8080/measure <http://localhost:8080/measure>`_.

To store data, send a POST request to ``/measure`` with the values in one of the following ways:

- query parameters, e.g. ``POST /measure?temperature=21.5&humidity=40`` (works with every format),
- a JSON object body, e.g. ``{"temperature": 21.5, "humidity": 40}`` (works with every format),
- an XML body (with ``format='xml'``), where each child of the root element is one value; the name of the root element is not checked:

.. code:: sh

    curl -X POST http://localhost:8080/measure -H "Content-Type: application/xml" -d '<data><temperature>21.5</temperature><humidity>40</humidity></data>'

A malformed XML body or a JSON body that is not an object (or not valid JSON) is rejected with a ``400`` response. All errors are returned as JSON with a ``message`` field, e.g. ``{"message": "Invalid JSON: the request body could not be parsed."}``. With ``format='xml'``, column names must be valid XML element names: letters, digits, ``_``, ``-`` or ``.``, starting with a letter or ``_``, without spaces, and not starting with ``xml``.

To restrict access to the collected data, define the following setting in the ``configuration.yml`` file in the root directory:

.. code:: yaml

    password: 'password' # Password for data access

The password can be sent with any request (``/measure``, ``/data`` and ``/export``) in one of the following ways:

- ``Authorization: Bearer password`` header (recommended),
- ``X-API-Key: password`` header,
- ``"password": "password"`` field in a JSON body or ``<password>password</password>`` element in an XML body (``/measure`` only),
- ``?password=password`` query parameter (supported for backward compatibility).

Prefer one of the headers, since URLs (including query parameters) are often written to server and proxy logs. For example:

.. code:: sh

    curl -X POST http://localhost:8080/measure -H "Authorization: Bearer password" -H "Content-Type: application/json" -d '{"temperature": 21.5}'

Data access
~~~~~~~~~~~

To access data via the Succulent API, define the following setting in the ``configuration.yml`` file in the root directory:

.. code:: yaml

    results:
      - enable: true # false by default

To access the collected data, send a GET request (or navigate) to `http://localhost:8080/data <http://localhost:8080/data>`_. To access password-protected data, send the password as described above (e.g. the ``Authorization: Bearer password`` header).

Data export
~~~~~~~~~~~

To export the data, enable the export option in the configuration file:

.. code:: yaml

    results:
      - export: true # false by default

To export the data, send a GET request (or navigate) to `http://localhost:8080/export <http://localhost:8080/export>`_. To export password-protected data, send the password as described above. The data will be downloaded in the format specified in the configuration file.

Data exploration
~~~~~~~~~~~~~~~~

succulent includes an optional web dashboard for monitoring the collected data in a browser. To enable it, define the following setting in the ``configuration.yml`` file in the root directory:

.. code:: yaml

    explore:
      - enable: true # false by default
      - refresh: 10  # auto-refresh interval in seconds (optional, 0 disables it)

Then navigate to `http://localhost:8080/explore <http://localhost:8080/explore>`_. The dashboard shows:

- the latest value of each column, with its position between ``min`` and ``max``,
- data quality: the number of measurements, missing values, values outside ``min``/``max`` and the typical interval between measurements,
- a chart for each numeric column, with ``min`` and ``max`` as dashed lines (long ranges are averaged so the page stays fast),
- the latest measurements in a table,
- for the ``image`` format, a gallery of the uploaded images.

With ``timestamp: true``, you can choose the time range (1 h, 24 h, 7 d, 30 d or all). If export is enabled, the data can be downloaded as CSV from the dashboard.

If a password is set, the dashboard asks for it once and keeps the session in a cookie, so the password never appears in the URL. Sessions last until the server restarts; to keep them across restarts, set a ``secret_key`` in the configuration. Scripts can read ``/explore/api/data`` with the ``Authorization: Bearer password`` or ``X-API-Key: password`` header instead.

The dashboard only reads the stored data; data collection works exactly as without it. It needs no internet access (no external scripts or fonts), so it also works on a local network, and values sent by devices are always shown as text.
