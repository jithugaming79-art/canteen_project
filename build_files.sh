#!/bin/bash

# Mark that we're in the build phase (so settings.py uses SQLite instead of MySQL)
export BUILD_PHASE=1

# Install dependencies (--break-system-packages needed for Vercel's uv-managed Python)
pip install --break-system-packages -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Create the output directory for Vercel static build
mkdir -p staticfiles_build/static
cp -r staticfiles/* staticfiles_build/static/
