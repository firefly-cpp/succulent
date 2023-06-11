succulent documentation!
========================================

.. automodule:: succulent

succulent -- Collect POST requests easily

* **Free software:** MIT license
* **Github repository:** https://github.com/firefly-cpp/succulent
* **Python versions:** 3.7.x, 3.8.x, 3.9.x, 3.10.x, 3.11x

General outline of the framework
---------------------------------
Sending sensor measurements, data, or GPS positions from embedded devices, microcontrollers, and [smartwatches](https://github.com/firefly-cpp/AST-Monitor) to the central server is sometimes complicated and tricky. Setting up the primary data collection scripts can be time-consuming (selecting a protocol, framework, API, testing it, etc.). Usually, scripts are written for a specific task; thus, they are not easily adaptive to other tasks. succulent is a pure Python framework that simplifies the configuration, management, collection, and preprocessing of data collected via POST requests. The inspiration for the framework comes from the practical data collection challenges in [smart agriculture](https://github.com/firefly-cpp/smart-agriculture-datasets/tree/main/plant-monitoring-esp32). The main idea of the framework was to speed up the process of configuring different collected parameters and providing several useful functions for data transformations. The framework allows users to configure the whole endpoint for data collection in several minutes and thus not spend time on server-side scripts.

Detailed insights
-----------------------
The current version includes (but is not limited to) the following functions:

- Request URL generation for data collection
- Data collection from POST requests
- Storing data in different formats (CSV, JSON, SQLite, images)
- Defining boundaries for collected data (min, max)
