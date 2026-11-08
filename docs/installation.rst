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
| pandas               | >=2.0.1,<3.0.0       |
+----------------------+----------------------+
| pyyaml               | >=6.0,<7.0           |
+----------------------+----------------------+
| flask                | >=2.3.2,<4.0.0       |
+----------------------+----------------------+
| lxml                 | >=5.2.2,<7.0.0       |
+----------------------+----------------------+
| numpy                | >=1.26.0,<3.0.0      |
+----------------------+----------------------+

List of succulent's development dependencies:

+----------------------+------------+
| Package              | Version    |
+======================+============+
| pytest               | ^9.0.3     |
+----------------------+------------+
| sphinx               | >=7.0      |
+----------------------+------------+
| sphinx-rtd-theme     | >=2.0      |
+----------------------+------------+
| sphinxcontrib-bibtex | ^2.6       |
+----------------------+------------+