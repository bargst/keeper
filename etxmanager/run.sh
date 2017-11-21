#!/bin/bash
export FLASK_APP=account.py
source $(pipenv --venv)/bin/activate
flask run
