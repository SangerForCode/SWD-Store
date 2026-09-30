# SWD Store

SWD Store is a Django-based campus marketplace for BITS Pilani students. It lets members post pre-owned items, browse listings by category/campus/hostel, contact sellers, and manage their own listings. The original application is named “Bits Pilani Store” in several UI/configuration files.

## What it includes

- Server-rendered storefront and listing pages, with an installable PWA shell.
- Google OAuth2 sign-in and session-backed member profiles.
- Listings with categories, optional hostel location, price, sold status, and multiple images.
- Seller contact links generated for WhatsApp when a phone number is available.
- Feedback and feedback-image records.
- Public, read-only JSON endpoints for items, categories, hostels, and campuses.
- Optional Amazon SES email, Web Push notifications, and Twilio phone lookups.
- A Celery Beat task that marks listings older than 60 days as sold.

See [docs/architecture.md](docs/architecture.md) for the UML-style class, component, and request-flow diagrams.

## Stack

- Python 3.12 recommended (the pinned TensorFlow dependency is not compatible with every Python release).
- Django 5.1, SQLite by default, Django templates/static assets.
- Celery + Redis for scheduled/background work.
- WhiteNoise for static-file serving; Google OAuth, SES, Web Push, and Twilio are optional integrations.

## Repository layout

```text
pawnshop/
├── manage.py
├── requirements.txt
├── .env.example
├── pawnshop/             # Django settings, URLConf, WSGI/ASGI, Celery app
├── bits/                 # Models, views, forms, APIs, templates, middleware, tasks
└── static/               # Source CSS/JS and static assets

docs/
└── architecture.md       # UML-style diagrams and request-flow notes
```

## Run locally

From the repository root:

```bash
cd pawnshop
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `pawnshop/.env` and replace `DJANGO_SECRET_KEY` with a fresh random value. One way to generate it is:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Google sign-in requires a Google OAuth client ID and secret in `.env`. The app can start without SES/Twilio/Web Push credentials; those features remain unavailable until configured. When SES credentials are absent, outgoing email uses Django's console backend.

Initialize the local database and cache table, then run the development server:

```bash
python manage.py migrate
python manage.py createcachetable cache_table
python manage.py collectstatic --noinput
python manage.py check
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. For the Django admin, create a local admin user with `python manage.py createsuperuser`.

### Background jobs (optional)

The website can be explored without starting Celery. To run the scheduled “mark old listings sold” task, start Redis and run these from `pawnshop/` in separate terminals:

```bash
redis-server
celery -A pawnshop worker --loglevel=info
celery -A pawnshop beat --loglevel=info
```

The beat schedule uses the configured Django timezone (`Asia/Kolkata`) and runs daily at 09:11.

## Configuration

All credentials and deployment-specific values belong in the untracked `pawnshop/.env` file. `.env.example` documents the supported names:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django signing/session secret; required |
| `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Development and host configuration |
| `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` | Google sign-in |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SES_REGION_NAME` | Optional SES email delivery |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | Optional phone-number verification |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` | Optional browser push notifications; use a newly generated pair |
| `REDIS_URL` | Optional Celery broker |
| `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` | Explicit browser origins for the deployment |

The default database is SQLite at `pawnshop/db.sqlite3`. Uploaded files, generated static output, logs, local exports, and cache/scheduler state are runtime data and are intentionally excluded from Git. Keep them in deployment storage and back them up separately where appropriate.

## API surface

The URL configuration exposes server-rendered pages and two API groups:

- Session-oriented `/api/...` routes for the application UI.
- Read-only `/public/api/...` routes for items, item detail, categories, hostels, and campuses.

The concrete routes and handlers are in [`pawnshop/bits/urls.py`](pawnshop/bits/urls.py); JSON response shapes are defined in `bits/views.py` and `bits/public_views.py`.

## Security and project status

This repository is published as source code, not as a production deployment recipe. Review authentication, ownership checks, CSRF/CORS policy, upload handling, and production database/storage settings before exposing a live instance. Use fresh credentials and a newly generated Django secret; never reuse credentials that appeared in an earlier private working copy.

The repository does not currently include a `LICENSE` file, so no license to reuse or redistribute the code is granted by this repository.
