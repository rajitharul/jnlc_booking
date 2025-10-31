# Email Setup Instructions

This system uses Flask-Mail with Gmail SMTP for sending confirmation emails. Here's how to configure it:

## Option 1: Using Gmail (Free)

1. **Create a Gmail App Password:**
   - Go to your Google Account settings
   - Navigate to Security → 2-Step Verification (enable if not already)
   - Go to App passwords
   - Create a new app password for "Mail"
   - Copy the 16-character password

2. **Set Environment Variables:**
   
   Before running the application, set these environment variables:
   
   ```bash
   export MAIL_USERNAME="your-email@gmail.com"
   export MAIL_PASSWORD="your-16-char-app-password"
   export MAIL_DEFAULT_SENDER="your-email@gmail.com"
   ```
   
   Or create a `.env` file in the project root:
   ```
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-16-char-app-password
   MAIL_DEFAULT_SENDER=your-email@gmail.com
   ```

3. **Alternative: Modify app.py directly**
   
   You can also edit `app.py` lines 23-25 to set your email credentials directly:
   ```python
   app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
   app.config['MAIL_PASSWORD'] = 'your-app-password'
   app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'
   ```

## Option 2: Using Other SMTP Services

You can use other free SMTP services like:
- **Mailgun** (Free tier: 5,000 emails/month)
- **SendGrid** (Free tier: 100 emails/day)
- **Outlook/Hotmail SMTP**

Just update the SMTP settings in `app.py`:
```python
app.config['MAIL_SERVER'] = 'smtp.office365.com'  # For Outlook
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
```

## Testing Email

After setting up, restart the Flask server and try booking a ticket. A confirmation email will be sent after successful receipt upload.

## Note

If email sending fails, the booking will still be confirmed, but you'll see a message that the email notification could not be sent. Check the Flask console for error messages.

