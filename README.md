---

# succulent - Collect POST requests easily

---

## About

sucullent is a pure Python framework that simplifies the configuration, management, collection, and preprocessing of data collected via POST requests. The inspiration for the framework comes from the practical data collection challenges in smart agriculture. The main idea of the framework was to speed up the process of configuring different collected parameters and providing several useful functions for data transformations.

## Detailed insights
The current version includes (but is not limited to) the following functions:

-
-
-

## Installation

### pip

Install succulent with pip:

```sh
pip install sucullent
```

***
## Prerequisites
* [Python](https://www.python.org)
* [poetry](https://python-poetry.org/docs)

***
## Environment
To setup the environment, execute the following command:
```bash
› poetry install
```

***
## Configuration
In the root directory, create a file named `configuration.yml` and define the following:
```yml
filetype: # File type (csv or json)

data:
  - name: # Measure name
```

***
## Launch
To launch the application, execute the following command:
```bash
› poetry run python succulent/api.py
```

The application will be available at the following address: http://localhost:8080/measure. Executing a GET request will return the URL for the POST request based on the parameters defined in the configuration file. A POST request will save the data in ``/succulent/data``. A file type must be defined in the configuration file.
