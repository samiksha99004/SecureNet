# SecureNet Backend

Network-Based Behavioural Intrusion Detection System - Backend API

## Overview

SecureNet is a two-stage ML-powered intrusion detection system:
- **Stage 1**: Isolation Forest for anomaly detection (78 features)
- **Stage 2**: XGBoost for attack classification

This backend provides REST APIs and WebSocket support for real-time security event monitoring.

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy (async)
- **Migrations**: Alembic
- **Authentication**: JWT
- **ML**: scikit-learn, XGBoost
- **Real-time**: WebSockets
- **Task Queue**: Celery + Redis

## Prerequisites

- Python 3.10+
- PostgreSQL 13+
- Redis (optional, for background tasks)

## Quick Start

### 1. Install Dependencies

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

```powershell
# Copy example env file
Copy-Item .env.example .env

# Edit .env with your configuration
# Important: Set DATABASE_URL, JWT_SECRET, and CORS_ORIGINS
```

### 3. Setup Database

```powershell
# Create PostgreSQL database
createdb securenet

# Run migrations
alembic upgrade head
```

### 4. Start Server

```powershell
# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/api/docs`

## Database Setup

### PostgreSQL Installation (Windows)

1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Install and remember your superuser password
3. Create database:

```powershell
# Using psql
psql -U postgres
CREATE DATABASE securenet;
CREATE USER securenet WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE securenet TO securenet;
\q
```

### Connection String

Update DATABASE_URL in `.env`:

```
DATABASE_URL=postgresql+asyncpg://securenet:your_secure_password@localhost:5432/securenet
```

### Migrations

```powershell
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Show current version
alembic current
```

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/otp/verify` - Verify OTP
- `POST /api/auth/otp/resend` - Resend OTP
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Get current user
- `POST /api/auth/change-password` - Change password

### Dashboard
- `GET /api/dashboard/summary` - Dashboard KPIs
- `GET /api/dashboard/host-status` - System resources
- `GET /api/dashboard/protocol-distribution` - Protocol stats
- `GET /api/dashboard/top-sources` - Top source IPs

### Security Events
- `GET /api/events` - List events (paginated, filtered)
- `GET /api/events/{id}` - Get event details
- `POST /api/events/{id}/resolve` - Mark as resolved
- `POST /api/events/{id}/false-positive` - Mark as false positive

### Settings
- `GET /api/settings` - Get all settings
- `GET /api/settings/detection` - Get detection settings
- `PUT /api/settings/detection` - Update detection settings
- `GET /api/settings/protection` - Get protection settings
- `PUT /api/settings/protection` - Update protection settings
- `GET /api/settings/notifications` - Get notification settings
- `PUT /api/settings/notifications` - Update notification settings
- `GET /api/settings/system` - Get system settings
- `PUT /api/settings/system` - Update system settings
- `GET /api/settings/whitelist` - List whitelist entries
- `POST /api/settings/whitelist` - Add whitelist entry
- `DELETE /api/settings/whitelist/{id}` - Remove whitelist entry

### ML Model
- `GET /api/model/info` - Get model information

### Reports
- `GET /api/reports/summary` - Report statistics
- `GET /api/reports` - List reports
- `POST /api/reports` - Generate new report
- `DELETE /api/reports/{id}` - Delete report

### Health
- `GET /health` - System health check

## Authentication

The API uses JWT Bearer tokens. Include the token in the Authorization header:

```
Authorization: Bearer <your_access_token>
```

Tokens are obtained via `/api/auth/login` and expire after 60 minutes (configurable).

## Frontend Integration

The backend is designed to integrate with the existing SecureNet frontend.

### Configure Frontend

Update the frontend `.env.local`:

```
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

### CORS Configuration

Add your frontend URL to `CORS_ORIGINS` in backend `.env`:

```
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

## ML Pipeline Integration

### Feature Requirements

The system expects **78 features** for each network flow:
- Flow duration, packet counts, byte counts
- Protocol information
- Port statistics
- Timing features
- Statistical aggregations

### Model Files

Place trained models in the `models/` directory:
- `isolation_forest.joblib` - Stage 1 anomaly detector
- `xgboost_classifier.joblib` - Stage 2 attack classifier
- `feature_scaler.joblib` - Feature preprocessing scaler

Update paths in `.env`:

```
ISOLATION_FOREST_MODEL_PATH=./models/isolation_forest.joblib
XGBOOST_MODEL_PATH=./models/xgboost_classifier.joblib
FEATURE_SCALER_PATH=./models/feature_scaler.joblib
```

### Model Loading (TODO)

Model loading logic needs to be implemented in `app/ml/` directory:
- `isolation_forest.py` - Load and run Stage 1 model
- `xgboost_classifier.py` - Load and run Stage 2 model
- `preprocessing.py` - Feature preprocessing
- `inference.py` - ML inference pipeline

## Development

### Running Tests

```powershell
pytest
```

### Code Quality

```powershell
# Format code (if ruff/black installed)
ruff format .

# Lint
ruff check .
```

### Logging

Logs are written to stdout and optionally to `LOG_FILE` (configured in `.env`).

Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Deployment

### Environment Variables

Ensure these are set in production:
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - Strong secret key (min 32 characters)
- `CORS_ORIGINS` - Frontend URLs
- `EMAIL_ENABLED=true` - Enable email notifications
- `SMTP_*` - Email server configuration

### Security Checklist

- [ ] Strong `JWT_SECRET` configured
- [ ] Database credentials secured
- [ ] CORS restricted to known origins
- [ ] HTTPS/TLS enabled (reverse proxy)
- [ ] Rate limiting configured
- [ ] Firewall rules applied
- [ ] Database backups enabled
- [ ] Secrets not committed to git

### Docker (Optional)

```dockerfile
# Dockerfile example
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Database Connection Error

- Verify PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Ensure database exists and user has permissions

### Import Errors

- Activate virtual environment
- Install dependencies: `pip install -r requirements.txt`

### OTP Not Received

- Check `EMAIL_ENABLED` in `.env`
- In development, OTPs are logged to console if email disabled
- Verify SMTP configuration if email enabled

### CORS Errors

- Add frontend URL to `CORS_ORIGINS` in `.env`
- Restart backend after changing `.env`

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── core/                # Core configuration
│   │   ├── config.py        # Settings
│   │   └── security.py      # Auth utilities
│   ├── db/                  # Database
│   │   └── base.py          # Session management
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── api/                 # API routes
│   │   ├── dependencies.py  # Shared dependencies
│   │   └── routes/          # Route handlers
│   ├── ml/                  # ML pipeline (TODO)
│   └── utils/               # Utilities
├── alembic/                 # Database migrations
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
└── README.md               # This file
```

## Contributing

1. Create feature branch
2. Make changes
3. Write/update tests
4. Ensure tests pass
5. Submit pull request

## License

[Your License]

## Support

For issues and questions, please contact [your-email@example.com]
.