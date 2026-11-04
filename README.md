# SoulService

SoulService connects **caterers with surplus food** to **NGOs** that can use it.
A caterer posts what is left over, an NGO requests it, the caterer accepts one
request, and the food is collected: all through the website.

Built with **Python (FastAPI)**, **SQLite**, **HTML / CSS / JavaScript**, and an
**XML + XSD** API for posting food.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. On first start the database is created and filled with demo data.

To go back to a clean demo (pickup deadlines are relative to "now", so do this before presenting):

```bash
python -m app.database.seed --reset
```

Run the tests: `python -m pytest`

## Demo accounts

Password for all accounts: `SoulDemo123!`

| Role | Name | Email |
|---|---|---|
| Caterer | Green Leaf Catering | caterer@soulservice.test |
| Caterer | Udupi Spice Kitchen | caterer2@soulservice.test |
| NGO | Hope Foundation | ngo@soulservice.test |
| NGO | Annapurna Trust | ngo2@soulservice.test |

## The six functions

| # | Function | Who | Where |
|---|---|---|---|
| 1 | Login / logout | Everyone | `/login` |
| 2 | Post food | Caterer | `/food/new` → `POST /api/v1/listings` (XML) |
| 3 | Browse available food (search + dietary filter) | Everyone | `/food` |
| 4 | Request food | NGO | "Request this food" button |
| 5 | Accept (or decline) a request | Caterer | Dashboard |
| 6 | Confirm collection | Caterer | Dashboard |

Extras: NGOs can cancel a request, caterers can withdraw a listing, confirmation
prompts before risky actions, and a friendly 404 page.

## How a request travels through the code

```
Browser  ──►  app/web/pages.py  (routes: receive the form)
              app/services/     (business rules: "is this allowed?")
              app/repositories/ (SQL: read and write the database)
              schema.sql        (tables + triggers inside SQLite)
```

Posting food is different: `static/js/app.js` builds an XML document and sends it to
`app/api/routes/listings.py`, which parses it safely, validates it against
`schemas/listing.xsd`, checks the business rules and saves it. See `docs/api-contract.md`.

## Where the database does the work

Some rules live in SQLite itself (`app/database/schema.sql`), so they can't be bypassed:

- only NGOs can request food, and never their own listing
- only one active request per NGO per listing, and only one accepted request per listing
- accepting a request automatically **reserves** the food
- confirming collection automatically marks the food as **collected**
- cancelling an accepted request automatically makes the food **available** again

## Security basics

- Passwords are salted and hashed (PBKDF2), never stored as plain text
- Login uses a signed session cookie
- Every form and the XML API are protected by a CSRF token
- XML is parsed with DTDs and external entities disabled (blocks XXE attacks)
- All values are escaped by Jinja2 when shown on pages (blocks XSS)
- Role checks on the server: NGOs can't post food, caterers can't request it,
  and a caterer can only act on their own listings

## Accessibility

Skip link, header / nav / main / footer landmarks, every input has a visible label,
errors are announced with `role="alert"`, full keyboard use with a clear focus ring,
allergens shown with text (not only colour), and a layout that works on phones.

## Project layout

```
app/
  main.py               app setup, sessions, error pages
  config.py             settings
  web/                  HTML routes + helpers (flash, CSRF, login checks)
  api/routes/           XML API (listings)
  services/             business rules (auth, listings, requests)
  repositories/         SQL queries
  database/             schema.sql, init, demo seed
  xml_api/              safe XML parser, validator, responses, XSD schemas
  static/               css/style.css, js/app.js
templates/              Jinja2 HTML pages
tests/                  51 automated tests
docs/                   API contract + architecture notes
```

### Pickup coordination (additional feature)

Caterers can save an optional contact phone on their dashboard. The number is
stored in SQLite and is only displayed to an NGO on its dashboard after that
NGO's request has been accepted. Accepted requests also include a **Get
directions** link that opens Google Maps using the listing's existing pickup
location. No Google Maps API key or geocoding service is required. Contact
numbers are not displayed on the public food browse page.

Existing databases are upgraded automatically on application startup to add
the optional contact field without deleting listings or requests. Run
`python -m pytest -q` to verify the original and new tests. For real use,
confirm the pickup address and phone number with the caterer before travel.
