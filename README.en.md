# Pizza Order System

[![CI](https://github.com/kaikysousa/PizzariaDjango/actions/workflows/ci.yml/badge.svg)](https://github.com/kaikysousa/PizzariaDjango/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/kaikysousa/PizzariaDjango)](https://github.com/kaikysousa/PizzariaDjango/releases)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Django 5.2](https://img.shields.io/badge/django-5.2-092E20.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Django application for menu browsing, cart, checkout, and receipt printing on an 80 mm thermal printer.

[Ler em português](README.md)

## Screenshots

![Menu](docs/screenshots/cardapio.png)

### 80 mm receipt

<img src="docs/screenshots/recibo.png" alt="80 mm receipt" width="360">

## Features

- Menu with search, category filter, and pagination.
- Browser cart with half-and-half pizzas (two flavors).
- Checkout with customer details and payment method.
- Order persisted with normalized items and server-side total recalculation.
- 80 mm receipt ready for browser printing.
- Product and order management through the Django admin.

## Requirements

- Python 3.12+
- Django 5.2.18 (LTS)
- 80 mm thermal printer paired on Windows (for physical printing)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The admin is at `/admin/`.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_DEBUG` | `1` | `0` in production |
| `DJANGO_SECRET_KEY` | empty | required when `DJANGO_DEBUG=0` |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | comma-separated hosts |
| `DJANGO_DB_PATH` | `db.sqlite3` | SQLite database path |
| `DJANGO_SECURE_SSL_REDIRECT` | `1` | redirects HTTP to HTTPS in production |
| `DJANGO_HSTS_SECONDS` | `31536000` | HSTS in production |
| `PIZZARIA_CNPJ` | empty | optional CNPJ on the receipt |

The `.env` file is loaded automatically by `python-dotenv`.

## Tests

```bash
python manage.py test
```

When `DJANGO_DEBUG=0` is set in the environment, run `DJANGO_DEBUG=1 python manage.py test`. The suite depends on development mode: in production, `collectstatic` requires a manifest and `SECURE_SSL_REDIRECT` returns 301.

### Quality

- 51 tests in `pedidos/tests/` covering catalog, intake, robustness, and views.
- CI in `.github/workflows/ci.yml`: tests, secret gate, security gate, deploy gate, and Ruff.

## Production

```bash
set DJANGO_DEBUG=0
set DJANGO_SECRET_KEY=<long-random-key>
set DJANGO_ALLOWED_HOSTS=your-domain.com
python manage.py collectstatic --noinput
gunicorn DjangoProject.wsgi
```

WhiteNoise serves collected static files. Use HTTPS and a reverse proxy for TLS.

## Printing

1. Pair the thermal printer on Windows and install the driver.
2. Open an order receipt and click **Print**.
3. Select the printer and 80 mm paper in the browser dialog.
4. The CSS uses `@page { size: 80mm auto; size: 80mm 297mm; margin: 0 }`. The second value is the Chrome fallback; the driver must respect the width.

The browser does not send Bluetooth print jobs directly. Pairing and drivers belong to the operating system.

## Structure

```
DjangoProject/        configuration
pedidos/              app: models, services, views, forms, admin, tests
templates/            base, menu, checkout, and receipt
static/css/           tokens, styles, and receipt CSS
static/js/            cart and motion
scripts/              audit gates
```

## Limitations

- Does not process online payments; it records the selected method.
- Does not issue fiscal documents. CNPJ is optional and comes from `PIZZARIA_CNPJ`.
- No customer authentication; the receipt uses a UUID token with `noindex`.
- SQLite is the default development database.
