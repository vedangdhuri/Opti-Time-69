#!/bin/bash
# Install Python dependencies
pip install -r requirements.txt

# Run migrations (Optional but recommended if not using a separate process)
python manage.py migrate --noinput

# Collect static files into the `staticfiles` directory
python manage.py collectstatic --noinput
