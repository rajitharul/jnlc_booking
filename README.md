# Junior National Law Conference - Ticket Booking System

A Flask-based ticket booking system for the Junior National Law Conference with automatic booking expiration and receipt upload functionality.

## Features

- **Registration & Booking**: Lawyers can register and reserve tickets (Gold or Platinum)
- **Ticket Limits**: Each lawyer can book up to 3 tickets total
- **Availability Tracking**: Real-time tracking of available tickets (30 Gold, 30 Platinum)
- **Automatic Expiration**: Bookings expire after 5 minutes if receipt is not uploaded
- **Receipt Upload**: Upload bank transfer receipt to confirm booking
- **SQLite Database**: Simple SQLite database for data storage

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

## How It Works

1. **Landing Page**: Users see available ticket counts
2. **Registration**: Lawyers enter their details and select tickets (1-3 tickets max)
3. **Booking Creation**: System creates a pending booking with 5-minute expiration
4. **Receipt Upload**: User must upload bank transfer receipt within 5 minutes
5. **Confirmation**: Once receipt is uploaded, booking is confirmed
6. **Auto-Cancellation**: Background task cancels expired bookings and releases tickets

## Database Schema

- **Lawyer**: Stores lawyer registration information
- **Booking**: Stores booking details with expiration timestamps

## File Structure

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── index.html         # Landing page
│   ├── register.html      # Registration form
│   ├── upload_receipt.html # Receipt upload page
│   └── booking_confirmed.html # Confirmation page
├── static/                # Static files
│   └── style.css          # Stylesheet
└── uploads/               # Uploaded receipt files (created automatically)
```

## Important Notes

- The background task checks for expired bookings every 10 seconds
- Uploaded receipts are stored in the `uploads/` directory
- The database file `conference_booking.db` is created automatically
- Only PNG, JPG, JPEG, and PDF files are accepted for receipt uploads

