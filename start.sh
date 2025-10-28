#!/bin/bash
# Start script for WAF Test Backend

cd /var/www/html/waf.runah.pt/backend-test

# Activate virtual environment
source venv/bin/activate

# Run migrations
python manage.py migrate --noinput

# Start Gunicorn
gunicorn waf_test_project.wsgi:application \
    --bind 127.0.0.1:8081 \
    --workers 2 \
    --timeout 120 \
    --access-logfile /var/www/html/waf.runah.pt/logs/backend.access.log \
    --error-logfile /var/www/html/waf.runah.pt/logs/backend.error.log \
    --log-level info

