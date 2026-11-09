# CO2 Monitoring System for Industrial Facilities

## Environment & Stack

* **Language:** Python 3
* **Framework:** Django
* **Databases:** MongoDB, SQLite
* **Server:** uWSGI, Supervisor, Nginx

## Installation Guide

1. **Clone the repository.**

   ```bash
   git clone https://github.com/dlazarchuk1312/co2_monitoring.git
   cd co2_monitoring
   ```

2. **Create and activate a virtual environment.**

   ```bash
   python3 -m venv env
   source env/bin/activate
   ```

3. **Install dependencies and apply migrations.**

   ```bash
   python -m pip install django pymongo pandas numpy scikit-learn
   python manage.py migrate
   ```

4. **Start the development server.**

   ```bash
   python manage.py runserver
   ```
