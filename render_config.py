"""
Render infrastructure configuration for PocketPlot Universe.

Used by the Render REST API to:
  1. Create a Web Service (Flask app)
  2. Attach a Persistent Disk (SQLite database)
  3. Configure environment variables
  4. Set up health checks
  5. Configure auto-deploy from Git
  6. Connect the custom domain (pocketplot.app)
  7. Issue SSL automatically (required for .app TLD)

API documentation: https://api-docs.render.com/
"""

import os
import json

OWNER_ID = 'tea-da88lvjtqb8s73e6k1k0'
RENDER_API_KEY = os.environ.get('RENDER_API_KEY', 'rnd_HRvlrROhKdPAi9YWvY4INmwM9HgS')
SERVICE_NAME = 'pocketplot'
DOMAIN = 'pocketplot.app'
REGION = 'oregon'  # west coast US - cheapest region on Render
PLAN = 'starter'    # $7/month always-on. Use 'free' for free tier.
RUNTIME = 'python'
REPO_URL = 'https://github.com/render-examples/flask-hello-world.git'  # placeholder - we use Render Git

# Build command - install dependencies
BUILD_CMD = 'pip install --upgrade pip && pip install -r requirements.txt'

# Start command - run gunicorn (production WSGI server)
# Using 1 worker + 4 threads for SQLite (more workers = file lock contention with SQLite)
START_CMD = 'gunicorn --workers 1 --threads 4 --bind 0.0.0.0:$PORT --timeout 120 app:app'

# Persistent disk for SQLite
# 1 GB is plenty for PocketPlot (the DB is currently <2MB)
DISK_NAME = 'pocketplot-data'
DISK_SIZE_GB = 1
DISK_MOUNT_PATH = '/var/data'


def make_service_payload():
    """Payload for POST /v1/services"""
    return {
        'type': RUNTIME,
        'name': SERVICE_NAME,
        'ownerId': OWNER_ID,
        'region': REGION,
        'plan': PLAN,
        'runtime': RUNTIME,
        'buildCommand': BUILD_CMD,
        'startCommand': START_CMD,
        'healthCheckPath': '/healthz',
        'autoDeploy': True,
        'numInstances': 1,
        'envVars': [
            {'key': 'POCKETPLOT_SECRET', 'value': _generate_secret(), 'generateValue': False},
            {'key': 'POCKETPLOT_ADMIN_EMAIL', 'value': 'admin@pocketplot.app'},
            {'key': 'POCKETPLOT_DELIVERY_EMAIL', 'value': 'stories@pocketplot.app'},
            {'key': 'FLASK_ENV', 'value': 'production'},
            {'key': 'DB_PATH', 'value': f'{DISK_MOUNT_PATH}/pocketplot.db'},
            {'key': 'STATIC_DIR', 'value': '.', 'generateValue': False},
            {'key': 'PORT', 'value': '10000'},
        ],
        'disk': {
            'name': DISK_NAME,
            'sizeGB': DISK_SIZE_GB,
            'mountPath': DISK_MOUNT_PATH,
        },
        'domains': [
            {'domain': DOMAIN, 'type': 'web'},
            {'domain': f'www.{DOMAIN}', 'type': 'web', 'redirectFor': DOMAIN},
        ],
    }


def _generate_secret():
    """Generate a strong session secret."""
    import secrets
    return secrets.token_hex(32)
