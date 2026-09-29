# Travel Itinerary Planning & Booking API

A complete Django REST Framework backend for discovering destinations, planning
collaborative itineraries, booking accommodation and activities, publishing
reviews, and tracking category-level travel budgets.

## Features

- JWT registration, login, refresh, verification, traveller profiles, and preferences
- Destination search with cost, category, climate, activity, and review information
- Private/public itineraries with owner, editor, admin, and viewer collaboration roles
- Nested daily plans, itinerary duplication, trip reports, analytics, and PDF export
- Accommodation and activity inventory with validated traveller bookings
- Polymorphic reviews for destinations, accommodation, or activities
- Budget allocations, itemized expenses, receipts, and automatic actual-spend totals
- Filtering, full-text search, ordering, bounded pagination, and optimized query loading
- OpenAPI schema with Swagger UI and ReDoc

## Project layout

The Django project lives in `config/`. Domain code is divided into six apps:
`accounts`, `destinations`, `itineraries`, `bookings`, `reviews`, and `budgets`.
Shared pagination and test fixtures live in `config/pagination.py` and
`config/test_helpers.py` respectively.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

SQLite is the zero-configuration default. Set the `DATABASE_*` environment
variables for PostgreSQL or another supported Django database backend. Uploaded
files are stored beneath `media/` in local development.

## API

All API routes are versioned beneath `/api/v1/`. Important entry points include:

| Purpose | Endpoint |
| --- | --- |
| Register / JWT login | `/api/v1/accounts/register/`, `/api/v1/accounts/login/` |
| Profile / preferences | `/api/v1/accounts/profile/`, `/api/v1/accounts/preferences/` |
| Destinations / search | `/api/v1/destinations/`, `/api/v1/destinations/search/` |
| Itineraries | `/api/v1/itineraries/` |
| Nested days / collaborators | `/api/v1/trips/{id}/days/`, `/api/v1/trips/{id}/collaborations/` |
| Accommodation / activities | `/api/v1/accommodations/`, `/api/v1/activities/` |
| Bookings / reviews | `/api/v1/bookings/`, `/api/v1/reviews/` |
| Budgets / expenses | `/api/v1/budgets/`, `/api/v1/expenses/` |
| Analytics / report | `/api/v1/analytics/`, `/api/v1/trips/report/` |
| OpenAPI / Swagger / ReDoc | `/api/v1/schema/`, `/api/v1/docs/swagger/`, `/api/v1/docs/redoc/` |

Object actions are available for itinerary duplication, PDF export, sharing, and
upcoming trips; booking confirmation/cancellation; destination activities/weather;
and helpful review votes. Browse Swagger for the complete request/response schema.

## Tests

The suite contains model, serializer, API, authentication, and role-permission
coverage using a shared `TravelFixtureMixin`:

```bash
pytest
# optional coverage report
coverage run -m pytest && coverage report
```

Configuration is read through `python-decouple`; no secrets are committed.
