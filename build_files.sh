#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Create the output directory for Vercel static build
mkdir -p staticfiles_build/static
cp -r staticfiles/* staticfiles_build/static/
