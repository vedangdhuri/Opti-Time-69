#!/bin/bash
# Install Python dependencies overriding the PEP-668 system packages block
python3 -m pip install -r requirements.txt --break-system-packages

python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput
