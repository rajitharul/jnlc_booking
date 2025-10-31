# Deployment Guide - Junior National Law Conference Booking System

## Recommended Deployment Options

### 1. **Railway.app** (Recommended) ⭐
**Best for: Easy deployment with free tier**

**Pros:**
- Free tier with $5 credit monthly
- Very easy setup (connects to GitHub)
- Automatic HTTPS
- Supports PostgreSQL (recommended for production)
- Built-in file storage
- Simple environment variable management

**Cons:**
- Free tier limited to $5/month usage
- May need to upgrade for high traffic

**Deployment Steps:**
1. Push your code to GitHub
2. Sign up at railway.app
3. Click "New Project" → "Deploy from GitHub"
4. Select your repository
5. Add environment variables for email (MAIL_USERNAME, MAIL_PASSWORD, etc.)
6. Deploy!

---

### 2. **Render.com** (Also Great) ⭐
**Best for: Free tier with good features**

**Pros:**
- Generous free tier
- Automatic SSL certificates
- Easy GitHub integration
- Supports PostgreSQL
- File storage available

**Cons:**
- Free tier instances sleep after inactivity (slow first request)
- May need paid plan for production use

**Deployment Steps:**
1. Push code to GitHub
2. Sign up at render.com
3. New → Web Service
4. Connect GitHub repo
5. Set build command: `pip install -r requirements.txt`
6. Set start command: `gunicorn app:app`
7. Add environment variables
8. Deploy!

---

### 3. **PythonAnywhere**
**Best for: Beginner-friendly, Python-focused**

**Pros:**
- Free tier available
- Beginner-friendly interface
- Built for Python apps
- Good documentation

**Cons:**
- Free tier has limitations (no custom domain, webhooks disabled)
- Can be slower than other options

---

### 4. **Fly.io**
**Best for: Good free tier with global deployment**

**Pros:**
- Generous free tier
- Global edge deployment
- Good for production
- Supports PostgreSQL

**Cons:**
- Requires CLI setup
- Slightly more complex

---

## Important Considerations for Your App

### Database
**Current:** SQLite (works but not ideal for production)
**Recommended for production:** PostgreSQL

### File Storage
**Current:** Local file storage (`uploads/` folder)
**Recommended for production:** 
- Cloud storage (AWS S3, Google Cloud Storage)
- Or use a service with persistent volumes (Railway, Render)

### Environment Variables Needed
```bash
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
SECRET_KEY=change-this-to-a-random-secret-key
```

---

## Recommended: Railway.app Deployment

### Why Railway?
1. ✅ Easiest deployment process
2. ✅ Free tier is sufficient for small-medium traffic
3. ✅ Automatic HTTPS
4. ✅ Easy PostgreSQL setup
5. ✅ GitHub integration
6. ✅ File persistence

### Quick Start with Railway:

1. **Prepare your code:**
   - All files are ready! (`Procfile`, `requirements.txt` with gunicorn)
   - Commit and push to GitHub

2. **Sign up and deploy:**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway auto-detects Flask and deploys!

3. **Add PostgreSQL** (recommended for production):
   - In Railway dashboard, click "+ New" → "Database" → "Add PostgreSQL"
   - Railway will automatically set `DATABASE_URL` environment variable
   - Your app will automatically use PostgreSQL (already configured!)
   - **Note:** Add `psycopg2-binary==2.9.9` to `requirements.txt` for PostgreSQL support

4. **Set environment variables in Railway:**
   - Go to your service → Variables tab
   - Add these:
     ```
     SECRET_KEY=your-random-secret-key-here
     MAIL_USERNAME=coderemdev@gmail.com
     MAIL_PASSWORD=xybsrcahxjwsgxnk
     MAIL_DEFAULT_SENDER=coderemdev@gmail.com
     ADMIN_USERNAME=admin
     ADMIN_PASSWORD=your-secure-admin-password
     ```
   - Railway will automatically set `PORT` (don't set it manually)
   - **Important:** Change `ADMIN_PASSWORD` to a strong password in production!

5. **Deploy and test!**
   - Your app will be available at `https://yourappname.railway.app`
   - Test all features

---

## Alternative: Render.com (Free Tier)

1. Push to GitHub
2. Sign up at render.com
3. New → Web Service
4. Connect GitHub
5. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
6. Add environment variables
7. Deploy!

---

## Post-Deployment Checklist

- [ ] Set all environment variables
- [ ] Test registration flow
- [ ] Test receipt upload
- [ ] Test email sending
- [ ] Test admin panel
- [ ] Check file uploads work
- [ ] Verify database persistence
- [ ] Test booking expiration
- [ ] Update CORS settings if needed

---

## Need Help?
If you need help with a specific platform, let me know and I can create platform-specific deployment files!

