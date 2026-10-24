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

To store data collection timestamps, define the following setting in the ``configuration.yml`` file in the root directory:

.. code:: yaml

    timestamp: true # false by default

To access the URL for data collection, send a GET request (or navigate) to `http://localhost:8080/measure <http://localhost:8080/measure>`_.

To restrict access to the collected data, define the following setting in the ``configuration.yml`` file in the root directory:

.. code:: yaml

    password: 'password' # Password for data access

The password can be sent with any request (``/measure``, ``/data`` and ``/export``) in one of the following ways:

- ``Authorization: Bearer password`` header (recommended),
- ``X-API-Key: password`` header,
- ``"password": "password"`` field in a JSON body (``/measure`` only),
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