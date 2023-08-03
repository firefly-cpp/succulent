Getting started
===============

This section demonstrates the usage of the succulent framework.

Installation
------------

To install the succulent package, run the following command:

.. code:: bash

    pip install succulent

Usage
-----

Configuration
~~~~~~~~~~~~~

In the root directory, create a file named ``configuration.yml`` and define the following:

.. code:: yaml

    data:
        - name: # Measure name
            min: # Minimum value (optional)
            max: # Maximum value (optional)

To collect images, create a file named ``configuration.yml`` in the root directory and define the following:

.. code:: yaml

    data:
        - key: # Key in POST request

Example
~~~~~~~

.. code:: python

    from succulent.api import SucculentAPI
    api = SucculentAPI(host='0.0.0.0', port=8080, config='configuration.yml', format='csv')
    api.start()