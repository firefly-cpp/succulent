---
<p align="center">
  <img alt="logo" width="300" src=".github/images/logo.png">
</p>


# succulent - Collect POST requests easily

---
![PyPI Version](https://img.shields.io/pypi/v/succulent.svg)
[![Documentation Status](https://readthedocs.org/projects/succulent/badge/?version=latest)](https://succulent.readthedocs.io/en/latest/?badge=latest)
![PyPI - Downloads](https://img.shields.io/pypi/dm/succulent.svg)
[![Downloads](https://static.pepy.tech/badge/succulent)](https://pepy.tech/project/succulent)
![GitHub repo size](https://img.shields.io/github/repo-size/firefly-cpp/succulent?style=flat-square)
[![GitHub license](https://img.shields.io/github/license/firefly-cpp/succulent.svg)](https://github.com/firefly-cpp/succulent/blob/master/LICENSE)
![GitHub commit activity](https://img.shields.io/github/commit-activity/w/firefly-cpp/succulent.svg)
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/firefly-cpp/succulent.svg)](http://isitmaintained.com/project/firefly-cpp/succulent "Average time to resolve an issue")
[![Percentage of issues still open](http://isitmaintained.com/badge/open/firefly-cpp/succulent.svg)](http://isitmaintained.com/project/firefly-cpp/succulent "Percentage of issues still open")
[![All Contributors](https://img.shields.io/badge/all_contributors-5-orange.svg?style=flat-square)](#contributors-)
[![AUR package](https://img.shields.io/aur/version/python-succulent?color=blue&label=Arch%20Linux&logo=arch-linux)](https://aur.archlinux.org/packages/python-succulent)
[![Fedora package](https://img.shields.io/fedora/v/python3-succulent?color=blue&label=Fedora%20Linux&logo=fedora)](https://src.fedoraproject.org/rpms/python-succulent)
[![Packaging status](https://repology.org/badge/tiny-repos/python:succulent.svg)](https://repology.org/project/python:succulent/versions)

* **Free software:** MIT license
* **Documentation:** [https://succulent.readthedocs.io/en/latest/](https://succulent.readthedocs.io/en/latest/)
* **Python versions:** 3.8.x, 3.9.x, 3.10.x, 3.11.x, 3.12.x
* **Tested OS:** Windows, Ubuntu, Fedora, Alpine, Arch, macOS. **However, that does not mean it does not work on others**

## About :information_source:

Do you ever find it challenging and tricky to send sensor measurements :straight_ruler:, data :bar_chart:, or GPS positions from embedded devices :iphone:, microcontrollers, and [smartwatches](https://github.com/firefly-cpp/AST-Monitor) to a central server? :satellite: Setting up the primary data collection scripts can be a time-consuming :hourglass_flowing_sand: process, involving selecting a protocol, framework, API, and testing them out. Moreover, these scripts are often tailored for specific tasks, making them difficult to adapt to different scenarios.

But fear not! Introducing succulent 🌵, a pure Python framework that simplifies the configuration, management, collection, and preprocessing of data collected via POST requests. This framework draws inspiration from real-world data collection challenges in [smart agriculture](https://github.com/firefly-cpp/smart-agriculture-datasets/tree/main/plant-monitoring-esp32) :brain::herb:, specifically plant monitoring using ESP32 devices. The main goal behind succulent is to streamline the process of configuring various data parameters and provide a range of useful functions for data transformations. By leveraging succulent, you can set up your entire data collection endpoint within minutes, freeing you from the hassle of dealing with server-side scripts.:rocket::wrench:

## Detailed Insights :mag:

The current version of succulent comes packed with exciting features, including, but not limited to:

- **Hassle-free generation of request URLs** for seamless data collection 🌐
- **Effortless data retrieval** from POST requests 📥
- **Versatile data storage options**, such as CSV, JSON, SQLite, and even images 🗂️📊🖼️
- **Customizable boundaries for collected data**, allowing you to set minimum and maximum thresholds ⚙️

With succulent, the process of collecting, managing, and preprocessing data becomes a breeze, empowering you to focus on what truly matters—gaining valuable insights from your embedded devices, microcontrollers, and smartwatches. ⌚ So why waste precious time? ⏳ Dive into the world of succulent and unlock the true potential of your data! 💪📈

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

### Arch Linux

To install succulent on Arch Linux, please use an [AUR helper](https://wiki.archlinux.org/title/AUR_helpers):

```sh
$ yay -Syyu python-succulent
```

### Fedora Linux

To install succulent on Fedora, use:

```sh
$ dnf install python3-succulent
```

## Container

[Basic container for succulent](https://github.com/firefly-cpp/succulent-container)

### Configuration
Follow the instructions in the [configuration](##configuration) section to define the configuration file.

### Installation
Build the container using Docker:
```bash
docker build -t succulent-container .
```

Alternatively, you can use ``docker-compose``:
```bash
docker compose build
```

### Usage
Run the container using Docker:
```bash
docker run -p 8080:8080 succulent-container
```

Alternatively, you can use ``docker-compose``:
```bash
docker compose up
```

## Usage

### Example

```python
from succulent.api import SucculentAPI
api = SucculentAPI(host='0.0.0.0', port=8080, config='configuration.yml', format='csv')
api.start()
```

## Configuration
### Data collection
In the root directory, create a file named `configuration.yml` and define the following:
```yml
data:
  - name: # Measure name
    min: # Minimum value (optional)
    max: # Maximum value (optional)
```

To collect images, create a file named ``configuration.yml`` in the root directory and define the following:
```yml
data:
  - key: # Key in POST request
```

To access the URL for data collection, send a GET request or navigate to [http://localhost:8080/measure](http://localhost:8080/measure).

### Data access
To access data via the Succulent API, enable the results in the configuration file:
```yml
results:
  enabled: true # false by default
```

To access the collected data, send a GET request or navigate to [http://localhost:8080/data](http://localhost:8080/data).

### Data export
To export the data, enable the export in the configuration file:
```yml
results:
  export:
    enabled: true # false by default
```

To export the data, send a GET request or navigate to [http://localhost:8080/export](http://localhost:8080/export).


## License

This package is distributed under the MIT License. This license can be found online at <http://www.opensource.org/licenses/MIT>.

## Disclaimer

This framework is provided as-is, and there are no guarantees that it fits your purposes or that it is bug-free. Use it at your own risk!

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/lahovniktadej"><img src="https://avatars.githubusercontent.com/u/57890734?v=4?s=100" width="100px;" alt="Tadej Lahovnik"/><br /><sub><b>Tadej Lahovnik</b></sub></a><br /><a href="https://github.com/firefly-cpp/succulent/commits?author=lahovniktadej" title="Code">💻</a> <a href="https://github.com/firefly-cpp/succulent/issues?q=author%3Alahovniktadej" title="Bug reports">🐛</a> <a href="#ideas-lahovniktadej" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/firefly-cpp/succulent/commits?author=lahovniktadej" title="Documentation">📖</a> <a href="#tutorial-lahovniktadej" title="Tutorials">✅</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/AyanDas348"><img src="https://avatars.githubusercontent.com/u/53610626?v=4?s=100" width="100px;" alt="Ayan Das"/><br /><sub><b>Ayan Das</b></sub></a><br /><a href="https://github.com/firefly-cpp/succulent/commits?author=AyanDas348" title="Code">💻</a> <a href="https://github.com/firefly-cpp/succulent/commits?author=AyanDas348" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://www.iztok-jr-fister.eu/"><img src="https://avatars.githubusercontent.com/u/1633361?v=4?s=100" width="100px;" alt="Iztok Fister Jr."/><br /><sub><b>Iztok Fister Jr.</b></sub></a><br /><a href="https://github.com/firefly-cpp/succulent/commits?author=firefly-cpp" title="Code">💻</a> <a href="#ideas-firefly-cpp" title="Ideas, Planning, & Feedback">🤔</a> <a href="#mentoring-firefly-cpp" title="Mentoring">🧑‍🏫</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://carlosal1015.github.io"><img src="https://avatars.githubusercontent.com/u/21283014?v=4?s=100" width="100px;" alt="Oromion"/><br /><sub><b>Oromion</b></sub></a><br /><a href="https://github.com/firefly-cpp/succulent/issues?q=author%3Acarlosal1015" title="Bug reports">🐛</a> <a href="#platform-carlosal1015" title="Packaging/porting to new platform">📦</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/rhododendrom"><img src="https://avatars.githubusercontent.com/u/3198785?v=4?s=100" width="100px;" alt="rhododendrom"/><br /><sub><b>rhododendrom</b></sub></a><br /><a href="#design-rhododendrom" title="Design">🎨</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/zala-lahovnik"><img src="https://avatars.githubusercontent.com/u/105444201?v=4?s=100" width="100px;" alt="Zala Lahovnik"/><br /><sub><b>Zala Lahovnik</b></sub></a><br /><a href="https://github.com/firefly-cpp/succulent/commits?author=zala-lahovnik" title="Documentation">📖</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
