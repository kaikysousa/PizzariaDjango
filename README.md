# Django Orders Management System

A Django-based web application for managing orders and processing checkouts. This project provides a robust system for handling order management with a focus on user-friendly interfaces and efficient data processing.

## Requirements

The project requires the following main dependencies:
- Django 5.1.6
- Python 3.8+
- django-bootstrap5
- Pillow
- Other dependencies are listed in `requirements.txt`

## Installation and Setup

1. Clone the repository:
```bash
git clone [repository-url]
cd [project-directory]
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Apply database migrations:
```bash
python manage.py migrate
```

5. Create a superuser (optional):
```bash
python manage.py createsuperuser
```

## Project Structure

```
.
├── DjangoProject/          # Main project directory
│   ├── settings.py         # Project settings
│   ├── urls.py             # Main URL configuration
│   └── wsgi.py            # WSGI configuration
├── pedidos/               # Main application directory
│   ├── models.py          # Database models
│   ├── views.py           # View logic
│   ├── urls.py            # App URL configuration
│   └── templates/         # HTML templates
├── static/                # Static files (CSS, JS, images)
├── media/                 # User-uploaded files
├── manage.py              # Django management script
└── requirements.txt       # Project dependencies
```

## Configuration

### Database
The project uses SQLite3 as the default database. The configuration is in `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### Static and Media Files
Static and media files are configured in settings.py:

```python
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

## Development Setup

1. Configure your development environment:
- Set `DEBUG = True` in settings.py for development
- Ensure all required environment variables are set
- Configure your IDE/editor with proper linting and formatting

2. Install development tools:
```bash
pip install black flake8  # Optional but recommended
```

## Running the Project

1. Start the development server:
```bash
python manage.py runserver
```

2. Access the application:
- Main application: http://localhost:8000
- Admin interface: http://localhost:8000/admin

3. For development:
- Make migrations after model changes: `python manage.py makemigrations`
- Apply migrations: `python manage.py migrate`
- Collect static files: `python manage.py collectstatic`

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Run tests
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

