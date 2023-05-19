---

# succulent - Collect POST requests easily

---

## About

succulent is a pure Python framework that simplifies the configuration, management, collection, and preprocessing of data collected via POST requests. The inspiration for the framework comes from the practical data collection challenges in smart agriculture. The main idea of the framework was to speed up the process of configuring different collected parameters and providing several useful functions for data transformations.

## Detailed insights
The current version includes (but is not limited to) the following functions:

- Request URL generation for data collection
- Data collection from POST requests

## Installation

### pip

Install succulent with pip:

```sh
pip install succulent
```

## Usage

### Example

```python
from succulent.api import SucculentAPI
api = SucculentAPI(host='0.0.0.0', port=8080, config='configuration.yml')
api.start()
```

## Configuration
In the root directory, create a file named `configuration.yml` and define the following:
```yml
filetype: # File type (csv or json)

data:
  - name: # Measure name
```