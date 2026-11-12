# Deploy on Render - Complete Guide

Render hosts both the FastAPI backend (Web Service) and the React frontend (Static Site) for free/low cost. This guide deploys the full stack on Render with detailed explanations and troubleshooting.

## Prerequisites

### Required
- **GitHub account** with this repository pushed to a branch (usually `main`)
- **Render account** (https://render.com) - signup is free
- **PostgreSQL database** - either Render's managed PostgreSQL or an external database
- **DNS control** for your custom domain (recommended for production QR menus)

### Optional but helpful
- `curl` command-line tool for testing APIs
- Docker for local testing before deployment
- Text editor with Git integration

---

## Step 1 — Prepare repository for deployment

### 1.1 Generate Python requirements.txt
Render does not auto-discover `pyproject.toml`. Generate a `requirements.txt` file:

```bash
cd backend
pip install --no-cache-dir -r requirements.txt  # if it exists
pip freeze > requirements.txt
```

If `requirements.txt` already exists, update it to include all dependencies:

```bash
cd backend
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt  # or install from pyproject.toml
pip freeze > requirements.txt
```

### 1.2 Commit the changes
Make sure everything is committed and pushed to GitHub:

```bash
cd /path/to/repo
git add backend/requirements.txt apps/web/package-lock.json  # any generated files
git add -A  # add all other changes
git commit -m "prepare for render deploy"
git push origin main
```

**Important**: The repository must be public on GitHub for Render to access it.

---

## Step 2 — Create the backend on Render

Render runs the FastAPI backend as a **Web Service**. This service handles all API endpoints, authentication, database access, and business logic.

### 2.1 Create PostgreSQL database

**Option A: Use Render's managed PostgreSQL (recommended)**
1. In Render dashboard, click **New → Database → PostgreSQL**
2. Choose a plan (free tier is sufficient for testing)
3. Select a region close to your users
4. Wait for the database to provision (5-10 minutes)
5. Click the database → **Connect** → copy the **Internal Database URL**

**Option B: Use external PostgreSQL**
If you already have a PostgreSQL database elsewhere, use its connection string:
```
postgresql://username:password@host:5432/database_name
```

### 2.2 Create the Web Service

1. In Render dashboard, click **New → Web Service**
2. Select your GitHub repository
3. Configure the **Web Service**:

| Setting | Detailed Value |
|---------|----------------|
| **Runtime** | Python 3 |
| **Build Command** | `pip install --no-cache-dir -r backend/requirements.txt` |
| **Start Command** | `cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Region** | Choose the region closest to your target users |
| **Branch** | `main` (or your default branch) |
| **Auto Deploy** | Enabled (recommended) |

### 2.3 Configure environment variables

Go to the Web Service → **Environment** tab → **Add Environment Variable**:

| Key | Value | Purpose |
|-----|-------|---------|
| `DATABASE_URL` | `postgresql+psycopg2://username:password@host:5432/database_name` | Database connection |
| `SECRET_KEY` | `[generate-a-secure-random-string]` | JWT signing, session security |
| `ACCESS_TOKEN_MINUTES` | `480` | JWT token validity (8 hours) |
| `REDIS_URL` | `` | Optional - leave blank if not using Redis |
| `CORS_ORIGINS` | `https://your-frontend.onrender.com,http://localhost:5173` | Frontend access control |
| `CLOUDINARY_CLOUD_NAME` | `[your-cloudinary-cloud-name]` | Cloudinary integration |
| `CLOUDINARY_API_KEY` | `[your-cloudinary-api-key]` | Cloudinary integration |
| `CLOUDINARY_API_SECRET` | `[your-cloudinary-api-secret]` | Cloudinary integration |
| `APP_ENV` | `production` | Application environment |

**How to generate a secure SECRET_KEY:**
```python
import secrets
print(secrets.token_urlsafe(32))
```

**Note**: All sensitive values should be kept secret and not committed to version control.

### 2.4 Deploy the backend

Click **Create Web Service**. Render will:
1. Build the Docker image
2. Run the build command
3. Start the web service
4. Display the deployment logs

Wait for the deployment to complete (2-5 minutes). After completion, note the service URL (e.g., `https://your-backend.onrender.com`).

---

## Step 3 — Create the frontend on Render

Render hosts the React frontend as a **Static Site**. This service serves the compiled HTML, CSS, and JavaScript files to customers.

### 3.1 Create the Static Site

1. In Render dashboard, click **New → Static Site**
2. Select your GitHub repository
3. Configure the **Static Site**:

| Setting | Detailed Value |
|---------|----------------|
| **Build Command** | `cd apps/web && npm ci && npm run build` |
| **Publish Directory** | `apps/web/dist` |
| **Region** | Choose region closest to your users |
| **Branch** | `main` |
| **Auto Deploy** | Enabled |

### 3.2 Environment variables (optional)

Frontend build-time environment variables are not typically required, but you might need them for:

| Key | Value | Purpose |
|-----|-------|---------|
| `VITE_API_URL` | `https://your-backend.onrender.com` | Override API base URL |

### 3.3 Deploy the frontend

Click **Create Static Site**. Render will:
1. Install Node.js dependencies
2. Build the React application
3. Upload the compiled files to their CDN
4. Display deployment logs

Wait for completion (2-5 minutes). Note the Static Site URL (e.g., `https://your-frontend.onrender.com`).

---

## Step 4 — Connect frontend to backend

This step ensures the frontend can communicate with the backend API.

### 4.1 Understand the API structure

The frontend API client (`apps/web/src/lib/api.ts`) currently has:
```ts
baseUrl: "", // relative URLs
```

On local development with Vite, relative URLs work because both frontend and backend run on the same origin (localhost:5173 and localhost:8000 respectively).

On Render, frontend and backend are on different origins, so relative URLs won't work correctly.

### 4.2 Option A: Configure frontend API URL (Recommended)

This is the simplest and most reliable approach.

**Edit `apps/web/src/lib/api.ts`:**
```ts
baseUrl: import.meta.env.VITE_API_URL ?? "",
```

**Add environment variable in Render Static Site:**
1. Go to Static Site → **Environment** tab
2. Add `VITE_API_URL` with value: `https://your-backend.onrender.com`
3. **Important**: Click **Reload env vars** button before deploying

**Rebuild the frontend:**
Render will automatically rebuild on environment variable changes. Wait for the deployment to complete.

### 4.1 Option B: Use Render redirect rules (Advanced)

If you prefer to keep frontend API calls relative, you can use Render's redirect functionality:

1. Create a `render.yaml` file in the repository root:
```yaml
services:
  - type: web
    name: frontend
    plan: free
    buildCommand: "cd apps/web && npm ci && npm run build"
    startCommand: "serve -s dist -l $PORT"
    envVars:
      - key: VITE_API_URL
        value: "https://your-backend.onrender.com"
    routes:
      - path: "/api/*"
        service: backend
        stripPrefix: true

  - type: web
    name: backend
    plan: free
    buildCommand: "pip install --no-cache-dir -r backend/requirements.txt"
    startCommand: "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    envVars:
      # ... backend environment variables
```

**Note**: This approach is more complex and requires additional configuration. Option A is simpler and more maintainable.

---

## Step 5 — Configure customer QR menu domain

The QR codes displayed to customers use the `customer_hostname` field from your database to generate menu URLs.

### 5.1 QR code URL structure

QR codes link to: `https://<customer_hostname>/t/{qr_token}`

### 5.2 Local development setup (for testing)

For local testing without a public domain:

1. Connect to your database
2. Update the restaurant(s) `customer_hostname` to `localhost`
3. Ensure frontend runs on port 5173: `http://localhost:5173/t/{qr_token}`

### 5.3 Production setup (recommended)

**Option A: Use Render's custom domain (recommended)**

1. Purchase a domain (e.g., `menu.yourrestaurant.com`) and point it to Render
2. In Render Static Site dashboard → **Custom Domains** → **Add Custom Domain**
3. Complete DNS verification (Render provides CNAME/A record instructions)
4. Update restaurant `customer_hostname` in database to your custom domain

**Example DNS setup for `menu.yourrestaurant.com`:**
```
# If your provider supports it:
Type: A
Value: YOUR_RENDER_STATIC_SITE_IP

# Or CNAME (if supported):
Type: CNAME  
Value: your-frontend.onrender.com
```

**Option B: Use a subdomain of your main website**

If you have a custom backend domain, use that for the QR menu:
```
https://order.yourrestaurant.com/t/{qr_token}
```

### 5.4 Testing QR functionality

1. Go to the frontend and log in as staff
2. Navigate to `/staff/tables`
3. Click on any table to view QR codes
4. Scan QR with phone camera
5. Verify it loads the customer menu page

**Common issues:**
- If QR shows "site can\'t be reached", check that `customer_hostname` has public DNS
- If menu fails to load, check browser console for network errors
- If authentication fails, verify the backend URL is correct

---

## Step 6 — Run database migrations

Render PostgreSQL starts empty. The backend creates basic schema on startup, but for production, you should run Alembic migrations to ensure all tables, indexes, and constraints are properly created.

### 6.1 Method 1: Run migrations via Render Shell

1. In Render dashboard → Web Service → **Shell** tab
2. Run:
```bash
cd backend
alembic upgrade head
```

### 6.2 Method 2: Include in build command

Edit the Web Service build command to include migrations:
```
pip install --no-cache-dir -r backend/requirements.txt && alembic upgrade head
```

### 6.3 Seed initial data (if needed)

Some applications include seed data for initial setup:
```bash
cd backend
python -m app.seed
```

**Note**: Always backup your database before running migrations, especially if you have existing data.

---

## Step 7 — Comprehensive smoke testing

Thoroughly test the deployment before going live.

### 7.1 Basic connectivity test

```bash
# Test backend health
#!/bin/bash
BACKEND_URL="https://your-backend.onrender.com"
FRONTEND_URL="https://your-frontend.onrender.com"

echo "Testing backend..."
curl -f "$BACKEND_URL/health" && echo "✓ Backend is healthy" || echo "✗ Backend health check failed"

echo "Testing frontend..."
curl -f "$FRONTEND_URL" && echo "✓ Frontend is accessible" || echo "✗ Frontend access failed"
```

### 7.2 Functional testing

1. **Open the frontend URL** in a browser
2. **Log in as staff user**:
   - Use existing staff credentials or create a test user
   - Navigate to `/staff/tables`
3. **Test QR code generation**:
   - Click on a table to view QR codes
   - Scan QR with phone
   - Verify customer menu loads correctly
4. **Test ordering process**:
   - Place a test order from customer menu
   - Verify order appears in `/staff/pending`
   - Complete the order
5. **Test API endpoints manually**:
   ```bash
   # Get menu items
   curl "https://your-backend.onrender.com/api/v1/catalog/menu?restaurant_id=1"
   
   # Get tables
   curl "https://your-backend.onrender.com/api/v1/operations/tables"
   ```

### 7.3 Performance testing (optional)

For production deployment, consider:
- Using tools like `ab` (Apache benchmark) or `k6` for load testing
- Testing with multiple concurrent connections
- Checking page load times

---

## Monitoring and maintenance

### 8.1 Monitor deployment status

1. **Render Dashboard**: Check the **Overview** tab for service health
2. **Logs**: Monitor deployment logs for errors
3. **Metrics**: Track response times and error rates
4. **Alerts**: Set up notifications for deployment failures

### 8.2 Common issues and solutions

| Symptom | Cause | Solution |
|---------|-------|----------|
| Build fails with `requirements.txt not found` | File missing or wrong path | Generate `pip freeze > requirements.txt` in backend directory and commit |
| Frontend calls fail with CORS errors | Backend CORS not configured | Add frontend URL to `CORS_ORIGINS` in backend |
| QR codes show "site can\'t be reached" | No public DNS for `customer_hostname` | Set custom domain or use Render's default domain |
| Images fail to upload | Cloudinary credentials missing | Add Cloudinary env vars to backend |
| Frontend blank after deploy | API URL not configured | Set `VITE_API_URL` environment variable |
| Intermittent 500 errors | Database connection issues | Check database connection string and permissions |

### 8.3 Debugging tips

**Backend logs:**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level debug
```

**Frontend console:**
- Open browser developer tools (F12)
- Check Network tab for failed requests
- Check Console tab for JavaScript errors
- Use `curl` to test API endpoints directly

---

## Deployment checklist

### Before deploying:
- [ ] Code is committed to GitHub
- [ ] All required environment variables are set
- [ ] `requirements.txt` exists in backend directory
- [ ] Database connection string is valid
- [ ] Cloudinary credentials are correct (if using images)
- [ ] `customer_hostname` is set in database
- [ ] Frontend API URL configuration is complete

### After deploying:
- [ ] Verify backend health endpoint
- [ ] Verify frontend loads correctly
- [ ] Test QR code functionality
- [ ] Test complete ordering flow
- [ ] Check for any error messages in logs
- [ ] Verify environment variables are loaded correctly
- [ ] Test with custom domain (if applicable)

---

## Files changed during this deployment

### Frontend changes
- `apps/web/src/lib/api.ts` - Added `VITE_API_URL` support for Render deployment
- `apps/web/src/pages/staff/TablesPage.tsx` - Updated QR URL generation to use `/t/{token}` route

### Backend changes
- `backend/app/core/config.py` - Added `customer_qr_domain` configuration and Cloudinary settings
- `backend/app/modules/catalog/router.py` - Added menu image upload/download endpoints
- `backend/app/modules/catalog/schemas.py` - Updated `image_path` field to allow Cloudinary URLs
- `backend/app/modules/catalog/services/menu.py` - Implemented Cloudinary image upload service
- `backend/app/modules/tenancy/services/hostname.py` - Enabled shared domain support for all restaurants

### Deployment configuration
- `deploy.md` - This comprehensive deployment guide

## Need help?

If you encounter issues during deployment:
1. **Render documentation**: https://render.com/docs
2. **GitHub issues**: Report issues in the repository
3. @{ai-assistant} assistance: Ask for specific troubleshooting help

This deployment guide will help you successfully launch your restaurant management system on Render. The key is to follow each step carefully and thoroughly test before going live.

lol