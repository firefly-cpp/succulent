---

# succulent - Collect POST requests easily

---
![PyPI Version](https://img.shields.io/pypi/v/succulent.svg)
![PyPI - Downloads](https://img.shields.io/pypi/dm/succulent.svg)
[![Downloads](https://pepy.tech/badge/succulent)](https://pepy.tech/project/succulent)
![GitHub repo size](https://img.shields.io/github/repo-size/firefly-cpp/succulent?style=flat-square)
[![GitHub license](https://img.shields.io/github/license/firefly-cpp/succulent.svg)](https://github.com/firefly-cpp/succulent/blob/master/LICENSE)
![GitHub commit activity](https://img.shields.io/github/commit-activity/w/firefly-cpp/succulent.svg)
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/firefly-cpp/succulent.svg)](http://isitmaintained.com/project/firefly-cpp/succulent "Average time to resolve an issue")
[![Percentage of issues still open](http://isitmaintained.com/badge/open/firefly-cpp/succulent.svg)](http://isitmaintained.com/project/firefly-cpp/succulent "Percentage of issues still open")

## About

Sending sensor measurements, data, or GPS positions from embedded devices, microcontrollers, and [smartwatches](https://github.com/firefly-cpp/AST-Monitor) to the central server is sometimes complicated and tricky. Setting up the primary data collection scripts can be time-consuming (selecting a protocol, framework, API, testing it, etc.). Usually, scripts are written for a specific task; thus, they are not easily adaptive to other tasks. succulent is a pure Python framework that simplifies the configuration, management, collection, and preprocessing of data collected via POST requests. The inspiration for the framework comes from the practical data collection challenges in [smart agriculture](https://github.com/firefly-cpp/smart-agriculture-datasets/tree/main/plant-monitoring-esp32). The main idea of the framework was to speed up the process of configuring different collected parameters and providing several useful functions for data transformations. The framework allows users to configure the whole endpoint for data collection in several minutes and thus not spend time on server-side scripts.

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
### Alpine Linux

To install succulent on Alpine Linux, please use:

```sh
$ apk add py3-succulent
```

## Usage

### Example

```python
from succulent.api import SucculentAPI
api = SucculentAPI(host='0.0.0.0', port=8080, config='configuration.yml', format='csv')
api.start()
```

## Configuration
In the root directory, create a file named `configuration.yml` and define the following:
```yml
data:
  - name: # Measure name
```

## License

This package is distributed under the MIT License. This license can be found online at <http://www.opensource.org/licenses/MIT>.

## Disclaimer

This framework is provided as-is, and there are no guarantees that it fits your purposes or that it is bug-free. Use it at your own risk!
