# api.runah.pt

Public API for Runah.pt with WebSocket support, built with Django and Django Channels.

## Overview

This is the public-facing API that provides giveaway information and real-time updates via WebSocket connections.

## Endpoints

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/giveaway/` | GET | Returns current giveaway info (items, prices, images, rules) |
| `/health/` | GET | Health check endpoint |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `/ws/giveaway/` | Real-time giveaway updates |

## Features

- **No Authentication Required** - Public API accessible from any origin
- **CORS Enabled** - Allows requests from all origins
- **1-Hour Caching** - Built-in caching for DDoS protection
- **WebSocket Support** - Real-time updates via Django Channels
- **Rate Limiting** - Nginx-level rate limiting (10 req/s with burst)

## Tech Stack

- **Django 5.2** - Web framework
- **Django REST Framework** - API toolkit
- **Django Channels** - WebSocket support
- **Daphne** - ASGI server
- **Redis** - Channel layer backend

## Installation

```bash
# Clone the repository
git clone https://github.com/runah1996/api.runah.pt.git
cd api.runah.pt

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create cache directory
mkdir -p cache
```

## Running

### Development
```bash
source venv/bin/activate
python manage.py runserver 0.0.0.0:8501
```

### Production (with Daphne)
```bash
source venv/bin/activate
daphne -b 127.0.0.1 -p 8501 config.asgi:application
```

### Production (in screen)
```bash
screen -S runah-api
cd /var/www/html/api.runah.pt
source venv/bin/activate
daphne -b 127.0.0.1 -p 8501 config.asgi:application
# Ctrl+A, D to detach
```

## API Response Example

### GET /giveaway/

```json
{
  "success": true,
  "cached": false,
  "cache_duration_seconds": 3600,
  "giveaway": {
    "title": "MEGA COMBO GIVEAWAY",
    "total_value": "2 000€",
    "prizes": [
      {
        "name": "★ Butterfly Knife | Slaughter (Factory New)",
        "image": "https://runah.pt/assets/img/knife.png",
        "alt": "★ Butterfly Knife | Slaughter (Factory New)"
      }
    ],
    "rules": {
      "minimum_deposit": "€5",
      "bonus_code": "25RUNAH",
      "additional_info": "Higher deposits = more chances to win",
      "valid_period": "Valid from December 1st to December 31st"
    }
  },
  "partnership": {
    "name": "CSGO.NET",
    "logo": "https://runah.pt/assets/img/csgonet-logo.jpg",
    "url": "https://csgo.net/utm/runah",
    "bonus_code": "25RUNAH",
    "bonus_percentage": "25%"
  },
  "timestamp": "2025-12-24T11:05:57.351200"
}
```

## Project Structure

```
api.runah.pt/
├── config/             # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py         # ASGI config for WebSockets
│   └── wsgi.py
├── public/             # Public API app
│   ├── views.py        # API views
│   ├── urls.py         # URL routing
│   ├── consumers.py    # WebSocket consumers
│   └── routing.py      # WebSocket routing
├── cache/              # File-based cache storage
├── manage.py
└── requirements.txt
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | (insecure default) |
| `DJANGO_DEBUG` | Debug mode | `False` |

## Related Projects

- [runah.pt](https://github.com/runah1996/runah.pt) - Main website and private API

