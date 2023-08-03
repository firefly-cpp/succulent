Installation
============

Development environment
-----------------------

Requirements
~~~~~~~~~~~~

- Python: https://www.python.org
- Poetry: https://python-poetry.org/docs

After installing Poetry and cloning the project from GitHub, execute the following command in the root directory of the cloned project:

.. code:: sh

    $ poetry install

All of the project's dependencies should be installed and the project should be ready for further development. Note that Poetry creates a separate virtual environment for the project.

Development dependencies
~~~~~~~~~~~~~~~~~~~~~~~~

List of succulent's dependencies:

+----------------------+----------------------+
| Package              | Version              |
+======================+======================+
| pyyaml               | ^6.0                 |
+----------------------+----------------------+
| pandas               | ^2.0.0               |
+----------------------+----------------------+
| flask                | ^2.2.3               |
+----------------------+----------------------+
| sphinx               | ^4.4.0               |
+----------------------+----------------------+
| sphinx-rtd-theme     | ^1.0.0               |
+----------------------+----------------------+
| sphinxcontrib-bibtex | ^2.4.1               |
+----------------------+----------------------+

List of succulent's development dependencies:

+----------------+--------------+
| Package        | Version      |
+================+==============+
| pytest         | ^6.2         |
+----------------+--------------+