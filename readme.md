# GSMArena Phone Lookup Service

A Python-based REST API that retrieves mobile phone manufacturers, phone listings, and technical specifications from [GSMArena](https://www.gsmarena.com/).

The service uses **Requests** and **BeautifulSoup** for web scraping, **FastAPI** for API endpoints, **SQLite** for persistent caching, and **AWS Lambda** for serverless request handling.

## Features

- Retrieve available mobile phone manufacturers.
- Retrieve all phones belonging to a manufacturer.
- Retrieve detailed specifications for a particular phone.
- Scrape multiple manufacturer listing pages.
- Prevent duplicate phone records.
- Retry temporary HTTP and network failures using exponential backoff and jitter.
- Apply request timeouts and request pacing.
- Cache manufacturers, phone listings, and specifications in SQLite.
- Return stale cached data when GSMArena is temporarily unavailable.
- Use versioned SQLite database migrations.
- Provide structured JSON logging and request IDs.
- Validate API query parameters and return meaningful HTTP status codes.
- Support API Gateway REST API (v1) and HTTP API (v2) event formats through an AWS Lambda handler.
- Include automated tests using pytest and mocked HTTP requests.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Application development |
| FastAPI | REST API |
| AWS Lambda | Serverless request handling |
| API Gateway | HTTP event integration with Lambda |
| Requests | HTTP requests |
| BeautifulSoup4 | HTML parsing |
| SQLite | Persistent caching in the local application |
| pytest | Automated testing |
| pytest-cov | Test coverage |
| Ruff | Linting and formatting |
| pre-commit | Automated code checks |
| GitHub Actions | Continuous integration |

## Project Structure

```text
gsmarena-phone-lookup/
│
├── company_lookup/
│   ├── api/
│   │   ├── main.py
│   │   └── routes.py
│   │
│   ├── database/
│   │   ├── connection.py
│   │   ├── repository.py
│   │   └── migrations/
│   │       ├── runner.py
│   │       └── versions/
│   │           ├── v001_initial_schema.py
│   │           ├── v002_add_cache_timestamps.py
│   │           └── v003_add_manufacturer_id_index.py
│   │
│   ├── exceptions/
│   │   └── service.py
│   │
│   ├── models/
│   │   └── phone.py
│   │
│   ├── scraper/
│   │   ├── client.py
│   │   ├── parser.py
│   │   └── retry.py
│   │
│   ├── services/
│   │   └── phone_service.py
│   │
│   ├── config.py
│   └── logging_config.py
│
├── tests/
│   ├── api/
│   ├── database/
│   ├── scraper/
│   ├── services/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_logging_config.py
│   ├── test_models.py
│   └── test_lambda_function.py
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── lambda_function.py
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── pytest.ini
├── requirements.txt
└── requirements-dev.txt
```

## Getting Started

### Prerequisites

- Python 3.12 or later
- pip
- Git

### 1. Clone the repository

```bash
git clone https://github.com/anushka-DT/gsmarena-phone-lookup.git

cd gsmarena-phone-lookup
```

### 2. Create a virtual environment

```bash
python3.12 -m venv .venv
```

Activate it on Linux or macOS:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

Install application dependencies:

```bash
pip install -r requirements.txt
```

For development and testing:

```bash
pip install -r requirements-dev.txt
```

### 4. Configure the application

The application supports the following environment variable:

| Variable | Description | Default |
|---|---|---|
| `CACHE_TTL_DAYS` | Cache validity duration in days | `7` |

Set the variable in your terminal:

```bash
export CACHE_TTL_DAYS=7
```

The application uses seven days as the default cache duration.

## Running the Application

Start the FastAPI application using Uvicorn:

```bash
uvicorn company_lookup.api.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

### API Documentation

FastAPI automatically provides interactive API documentation.

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

Database migrations are applied automatically when the application starts.

The SQLite database is created at:

```text
data/phone_lookup.db
```

## AWS Lambda Integration

The project also includes a Lambda handler in `lambda_function.py`.

The handler reuses the existing `PhoneLookupService` instead of duplicating the scraping, caching, or database business logic.

### Supported API Gateway Events

The handler supports:

- API Gateway REST API (v1) event format.
- API Gateway HTTP API (v2) event format.

### Supported Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check API health |
| GET | `/api/v1/manufacturers` | Retrieve available manufacturers |
| GET | `/api/v1/phones?brand=Samsung` | Retrieve phones for a manufacturer |
| GET | `/api/v1/phones/specifications?brand=Samsung&model=Samsung%20Galaxy%20S24` | Retrieve phone specifications |

The Lambda handler returns API Gateway proxy responses containing a status code, headers, and a JSON response body.

### Lambda Database Storage

The Lambda handler uses the following database path:

```text
/tmp/phone_lookup.db
```

AWS Lambda provides `/tmp` as temporary writable storage. This location is suitable for the handler's SQLite database, but it is not permanent storage. Its contents may not survive execution environment replacement or lifecycle changes.

The handler initializes the database migrations and service lazily, reusing the service instance within a warm execution environment.

### Lambda Error Handling

The handler returns appropriate HTTP status codes:

| Status Code | Description |
|---|---|
| `200 OK` | Request completed successfully |
| `404 Not Found` | Endpoint, manufacturer, or phone model was not found |
| `422 Unprocessable Entity` | Required query parameters are missing |
| `503 Service Unavailable` | GSMArena request failed |
| `500 Internal Server Error` | Unexpected application error |

### Lambda Scope

The Lambda implementation is provided as application code and is tested locally through automated tests.

Actual AWS Lambda deployment and API Gateway configuration are not included in the current project scope.

## API Endpoints

All phone lookup endpoints use the `/api/v1` prefix.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check API health |
| GET | `/api/v1/manufacturers` | Retrieve available manufacturers |
| GET | `/api/v1/phones?brand=Samsung` | Retrieve phones for a manufacturer |
| GET | `/api/v1/phones/specifications?brand=Samsung&model=Samsung%20Galaxy%20S24` | Retrieve phone specifications |

### 1. Health Check

**Request**

```http
GET /health
```

**Example response**

```json
{
  "status": "healthy"
}
```

### 2. Get Manufacturers

**Request**

```http
GET /api/v1/manufacturers
```

**Example response**

```json
{
  "manufacturers": {
    "Samsung": "https://www.gsmarena.com/samsung-phones-9.php",
    "Apple": "https://www.gsmarena.com/apple-phones-48.php"
  }
}
```

The response contains manufacturer names and their corresponding listing URLs.

### 3. Get Phones by Manufacturer

**Request**

```http
GET /api/v1/phones?brand=Samsung
```

**Example response**

```json
{
  "brand": "Samsung",
  "phones": [
    {
      "name": "Samsung Galaxy S24",
      "url": "https://www.gsmarena.com/samsung_galaxy_s24-12773.php"
    }
  ]
}
```

The phone listing includes each phone's name and detail URL.

### 4. Get Phone Specifications

**Request**

```http
GET /api/v1/phones/specifications?brand=Samsung&model=Samsung%20Galaxy%20S24
```

**Example response structure**

```json
{
  "brand": "Samsung",
  "model": "Samsung Galaxy S24",
  "specifications": {
    "Network": {
      "Technology": ["GSM / CDMA / HSPA / EVDO / LTE / 5G"]
    },
    "Launch": {
      "Announced": ["2024, January 17"]
    },
    "Body": {
      "Dimensions": ["147 x 70.6 x 7.6 mm"]
    }
  }
}
```

The example illustrates the response structure. Actual values are retrieved from GSMArena and may change.

## HTTP Status Codes

| Status Code | Description |
|---|---|
| `200 OK` | Request completed successfully |
| `404 Not Found` | Manufacturer or phone model was not found |
| `422 Unprocessable Entity` | Missing or invalid query parameters |
| `503 Service Unavailable` | GSMArena is temporarily unavailable and no usable cached response is available |

The Lambda handler also returns `500 Internal Server Error` for unexpected errors.

## Application Architecture

The application follows a layered architecture.

### 1. API Layer

The FastAPI routes receive requests, validate query parameters, invoke the service layer, and return JSON responses.

### 2. Service Layer

`PhoneLookupService` coordinates data retrieval between the scraper and repository.

Responsibilities include:

- Checking whether cached data is fresh.
- Refreshing expired or missing data.
- Returning stale cached data when scraping fails.
- Handling database read and write failures.
- Resolving manufacturer names without case sensitivity.

### 3. Scraper Layer

`GSMArenaScraper` retrieves HTML pages using Requests and extracts information using BeautifulSoup.

Responsibilities include:

- Extracting manufacturer listings.
- Retrieving phone listings across multiple pages.
- Extracting phone specifications.
- Avoiding duplicate phone URLs.
- Applying request timeouts and pacing.
- Retrying temporary HTTP and network failures.

### 4. Database Layer

The application uses Python's built-in `sqlite3` module.

The database stores:

- Manufacturers and listing URLs.
- Phone names and detail URLs.
- Phone specifications in JSON format.
- Cache refresh timestamps.

Parameterized SQL queries are used for database operations.

### 5. Migration Layer

Database schema changes are managed through versioned migrations.

| Migration | Purpose |
|---|---|
| `v001` | Create initial database tables |
| `v002` | Add cache timestamp columns |
| `v003` | Add an index on `phones.manufacturer_id` |

Pending migrations are applied automatically during application startup. The Lambda handler also initializes migrations when its service is first created.

### 6. Lambda Handler

`lambda_function.py` provides an entry point for API Gateway requests.

Responsibilities include:

- Extracting HTTP methods, paths, and query parameters from API Gateway events.
- Supporting REST API v1 and HTTP API v2 event structures.
- Reusing the existing phone lookup service.
- Returning API Gateway-compatible JSON responses.
- Handling validation errors and application exceptions.

## Caching Strategy

The application uses SQLite to avoid repeatedly scraping the same information.

The default cache duration is seven days and can be configured using `CACHE_TTL_DAYS`.

The caching workflow is:

1. Check whether the requested data exists in SQLite.
2. Return the cached data if it is still fresh.
3. Scrape GSMArena if the cache is missing or expired.
4. Save successfully retrieved data to SQLite.
5. If scraping fails, return available stale cached data where possible.

This reduces unnecessary HTTP requests and improves availability during temporary source website failures.

For the local FastAPI application, the SQLite database is stored in the project's `data` directory. For Lambda, the handler uses `/tmp`, which is temporary storage and should not be considered durable.

## Retry and Request Handling

The scraper includes reusable retry handling for temporary failures.

- Maximum attempts: 3 by default.
- Initial retry delay: 1 second.
- Exponential backoff with random jitter.
- Retryable HTTP status codes: `429`, `500`, `502`, `503`, and `504`.
- Retryable network failures: connection errors and timeouts.
- HTTP request timeout: 15 seconds.
- Minimum request interval: 1 second.

These measures help reduce unnecessary repeated requests and handle temporary network failures.

## Logging

The application uses structured JSON logging.

Each API request receives a request ID.

The request ID is returned in the `X-Request-ID` response header and included in application logs to help trace requests.

The Lambda handler also logs unexpected errors server-side while returning generic error responses to callers.

## Running Tests

Run the complete test suite:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=company_lookup --cov-report=term-missing
```

Enforce the project's CI coverage threshold:

```bash
pytest --cov=company_lookup --cov-report=term-missing --cov-fail-under=80
```

Run an individual test module:

```bash
pytest tests/scraper/test_parser.py -v
```

Run the Lambda handler tests:

```bash
pytest tests/test_lambda_function.py -v
```

The tests cover API routes, scraper behavior, HTML parsing, retry handling, database operations, migrations, caching, service error handling, and Lambda request handling.

External HTTP requests are mocked in tests, and SQLite test databases are isolated from the application database.

## Code Quality

Run Ruff lint checks:

```bash
ruff check .
```

Check code formatting:

```bash
ruff format --check .
```

Run all configured pre-commit hooks:

```bash
pre-commit run --all-files
```

Install the pre-commit hooks for future commits:

```bash
pre-commit install
```

## Continuous Integration

GitHub Actions runs automated checks for pull requests targeting `main` and pushes to `main`.

The workflow contains two jobs:

**Code Quality**
- Install development dependencies.
- Run Ruff lint checks.
- Verify Ruff formatting.

**Automated Tests**
- Run pytest.
- Generate coverage reports.
- Enforce a minimum coverage threshold of 80%.
