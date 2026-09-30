# Architecture and UML-style diagrams

The application has a Django project package (`pawnshop`) and a primary application (`bits`). The diagrams describe the source tree and configured integrations; optional services are shown even when not configured in a local `.env`.

## Components and request/data flow

```mermaid
flowchart LR
    Browser[Browser / PWA] --> URLConf[Django URL configuration]
    URLConf --> Middleware[Security, CSRF/CORS, custom origin and request middleware]
    Middleware --> PageViews[bits HTML views and forms]
    Middleware --> SessionAPI[Session-oriented /api routes]
    Middleware --> PublicAPI[Read-only /public/api routes]

    PageViews --> OAuth[Google OAuth2 / ID-token verification]
    PageViews --> ORM[Django ORM]
    SessionAPI --> ORM
    PublicAPI --> ORM
    ORM --> SQLite[(SQLite database by default)]
    ORM --> Cache[(Database-backed cache table)]
    ORM --> Signals[Model signals]
    Signals --> Cache
    PageViews --> Uploads[Local media uploads]
    PageViews --> Email[SES, or console email locally]
    PageViews --> Push[Web Push using VAPID]

    Beat[Celery Beat schedule] --> Worker[Celery worker]
    Worker --> Broker[(Redis broker)]
    Worker --> ORM
```

## Domain model

```mermaid
classDiagram
    class Campus {
        <<choices>>
        GOA
        HYDERABAD
        PILANI
        DUBAI
        OTHERS
        GMAIL
    }

    class Person {
        id
        name
        email
        phone
        campus
        is_subscribed
        registered_at
    }
    class Hostel {
        name
        campus
    }
    class Category {
        id
        name
        item_count
        icon_class
        added_at
    }
    class Item {
        id
        name
        description
        price
        is_sold
        added_at
        updated_at
        phone
        whatsapp
    }
    class Image {
        id
        image
        display_order
        added_at
    }
    class Feedback {
        id
        message
        added_at
    }
    class FeedbackImage {
        id
        image
        added_at
    }

    Campus ..> Person : selected campus
    Campus ..> Hostel : selected campus
    Person "1" --> "0..*" Item : seller
    Hostel "0..1" --> "0..*" Person : residents
    Hostel "0..1" --> "0..*" Item : location
    Category "1" --> "0..*" Item : categorizes
    Item "1" --> "0..*" Image : gallery
    Person "0..1" --> "0..*" Feedback : submits
    Feedback "1" --> "0..*" FeedbackImage : attachments
```

`Person.save()` normalizes a stored phone number and derives the campus from a BITS email when possible. `Item.save()` normalizes its effective contact number, builds the WhatsApp link, and stores the absolute value of the price. Image rows use an explicit display order. These are model behaviors, not database-level constraints.

## Listing creation sequence

```mermaid
sequenceDiagram
    actor Member
    participant Browser
    participant Django as Django / bits view
    participant Form as ItemForm
    participant ORM as Django ORM
    participant Media as Media storage
    participant Signal as bits model signals
    participant Cache as Database cache

    Member->>Browser: Enter listing details and select images
    Browser->>Django: Submit form with session cookie
    Django->>Django: Resolve member session to Person
    Django->>Form: Validate fields and uploads
    Form-->>Django: Validated data
    Django->>ORM: Save Item and Image records
    ORM->>Media: Store uploaded image files
    ORM-->>Signal: Item/Image saved
    Signal->>Cache: Invalidate cached catalog data
    Django-->>Browser: Redirect or JSON response
```

## Background task

Celery Beat schedules `bits.tasks.mark_old_items_as_sold` once a day at 09:11 in `Asia/Kolkata`. The task queries listings older than 60 days and marks them sold. Redis is the configured broker; starting the web server alone does not run this task.

## Entry points

- Project URLConf: `pawnshop/pawnshop/urls.py` — admin, allauth, PWA, app, and social-auth routes.
- App URLConf: `pawnshop/bits/urls.py` — pages and JSON endpoints.
- HTML/session views: `pawnshop/bits/views.py`.
- Public read-only endpoints: `pawnshop/bits/public_views.py`.
- Data model: `pawnshop/bits/models.py`.
- Scheduled task: `pawnshop/bits/tasks.py`.
- Model signal handlers: `pawnshop/bits/signals.py`.

The separate historical `bp_bot` utility and its spreadsheet/health-reading runtime data are intentionally not part of the public copy.
