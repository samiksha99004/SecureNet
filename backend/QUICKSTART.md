# SecureNet Backend — Quick Start Guide

Get the backend running in 10 minutes.

## Prerequisites Check

- ✓ Python 3.10+ installed
- ✓ PostgreSQL 13+ installed and running
- ✓ Git installed (if cloning repository)

## Step 1: Navigate to Backend Directory

```powershell
cd backend
```

## Step 2: Run Setup Script

```powershell
.\setup.ps1
```

This will:
- Create virtual environment
- Install dependencies
- Create .env file
- Create necessary directories

## Step 3: Configure Environment

Edit `.env` file:

```env
# Minimum required configuration
DATABASE_URL=postgresql+asyncpg://securenet:password@localhost:5432/securenet
JWT_SECRET=your-super-secret-key-min-32-characters-long-change-this
CORS_ORIGINS=http://localhost:5173
```

**Important**: Change `JWT_SECRET` to a random string (min 32 chars)

## Step 4: Create Database

```powershell
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE securenet;
CREATE USER securenet WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE securenet TO securenet;
\q
```

## Step 5: Run Migrations

```powershell
# Activate virtual environment (if not already active)
.\venv\Scripts\Activate.ps1

# Run migrations
alembic upgrade head
```

## Step 6: Start Server

```powershell
uvicorn app.main:app --reload
```

Server will start at: `http://localhost:8000`

## Step 7: Test API

Open browser to: `http://localhost:8000/api/docs`

You should see the interactive API documentation (Swagger UI).

## Step 8: Connect Frontend

In your frontend project (SecureNet/frontend):

1. Copy `.env.example` to `.env.local`
2. Set:
   ```
   VITE_API_BASE_URL=http://localhost:8000/api
   ```
3. Start frontend: `npm run dev`

## Verify Installation

### Test Health Endpoint

```powershell
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "connected",
  "ml": "not_loaded",
  "version": "1.0.0"
}
```

### Test User Registration

```powershell
curl -X POST http://localhost:8000/api/auth/signup `
  -H "Content-Type: application/json" `
  -d '{
    "fullName": "Test User",
    "email": "test@example.com",
    "password": "Test1234",
    "confirmPassword": "Test1234"
  }'
```

Expected: Success message + OTP logged to console (if EMAIL_ENABLED=false)

## Common Issues

### Issue: `ModuleNotFoundError`

**Solution**: Ensure virtual environment is activated
```powershell
.\venv\Scripts\Activate.ps1
```

### Issue: Database connection error

**Solution**: 
1. Check PostgreSQL is running: `Get-Service postgresql*`
2. Verify DATABASE_URL in `.env`
3. Ensure database and user exist

### Issue: Port 8000 already in use

**Solution**: Use a different port
```powershell
uvicorn app.main:app --reload --port 8001
```

Then update frontend `.env.local` to use port 8001.

### Issue: CORS errors in frontend

**Solution**: 
1. Add frontend URL to `CORS_ORIGINS` in backend `.env`
2. Restart backend server

## Next Steps

1. **Create an admin user** (via signup + OTP verification)
2. **Configure settings** via frontend UI
3. **Integrate ML models** (see `app/ml/README.md`)
4. **Set up network capture** to generate security events
5. **Enable email notifications** (configure SMTP in `.env`)

## Development Commands

```powershell
# Run with auto-reload
uvicorn app.main:app --reload

# Run tests
pytest

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check alembic status
alembic current
```

## Production Deployment

See `README.md` for production deployment checklist.

Key points:
- Set `DEBUG=false`
- Use strong `JWT_SECRET`
- Enable HTTPS (via reverse proxy)
- Configure proper CORS origins
- Set up database backups
- Enable email notifications
- Configure log rotation

## Support

For detailed documentation, see `README.md`

For ML integration guide, see `app/ml/README.md`
