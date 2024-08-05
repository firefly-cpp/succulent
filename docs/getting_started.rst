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

To store data collection timestamps, create a `configuration.yml` file in the root directory and define the following:

.. code:: yaml

    timestamp: true # false by default

To access the URL for data collection, send a GET request (or navigate) to `http://localhost:8080/measure <http://localhost:8080/measure>`_.

Data access
~~~~~~~~~~~

To access data via the Succulent API, enable the results option in the configuration file:

.. code:: yaml

    results:
      - enable: true # false by default

To access the collected data, send a GET request (or navigate) to `http://localhost:8080/data <http://localhost:8080/data>`_.

Data export
~~~~~~~~~~~

To export the data, enable the export option in the configuration file:

.. code:: yaml

    export:
      - enable: true # false by default

To export the data, send a GET request (or navigate) to `http://localhost:8080/export <http://localhost:8080/export>`_. The data will be downloaded in the format specified in the configuration file.