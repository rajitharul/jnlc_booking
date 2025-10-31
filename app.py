from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime, timedelta
from functools import wraps
import os
import json
from werkzeug.utils import secure_filename
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
# Use PostgreSQL in production if DATABASE_URL is set, otherwise SQLite
database_url = os.environ.get('DATABASE_URL', 'sqlite:///conference_booking.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database connection options for PostgreSQL (if using PostgreSQL)
if database_url.startswith('postgresql://'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,  # Verify connections before using them
        'pool_recycle': 300,    # Recycle connections after 5 minutes
        'connect_args': {'connect_timeout': 10}  # 10 second connection timeout
    }
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

# Email configuration - using Gmail SMTP (free)
# To use Gmail, you need to create an App Password: https://support.google.com/accounts/answer/185833
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'coderemdev@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'xybsrcahxjwsgxnk')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'coderemdev@gmail.com')

db = SQLAlchemy(app)
mail = Mail(app)

# Admin credentials - can be set via environment variables
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')  # Change this in production!

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Authentication decorator for admin routes
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            flash('Please login to access admin panel.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Database Models
class Lawyer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    basl_id = db.Column(db.String(50), unique=True, nullable=False)
    nic = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lawyer_id = db.Column(db.Integer, db.ForeignKey('lawyer.id'), nullable=False)
    ticket_type = db.Column(db.String(20), nullable=False)  # Single, Double, Triple
    additional_basl_ids = db.Column(db.Text, nullable=True)  # JSON string of additional persons details (name, basl_id, nic, phone)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    receipt_filename = db.Column(db.String(255), nullable=True)
    
    lawyer = db.relationship('Lawyer', backref='bookings')

# Initialize database - lazy initialization to avoid blocking startup
def init_db():
    """Initialize database - call this after app context is available"""
    try:
        with app.app_context():
            db.create_all()
            # Start background thread only once
            if not hasattr(app, 'background_thread_started'):
                threading.Thread(target=background_task, daemon=True).start()
                app.background_thread_started = True
    except Exception as e:
        print(f"Database initialization error: {str(e)}")

# Try to initialize database, but don't block if it fails
try:
    with app.app_context():
        db.create_all()
except Exception as e:
    print(f"Warning: Could not initialize database at startup: {str(e)}")
    print("Database will be initialized on first request")

# Add template functions
@app.template_filter('fromjson')
def fromjson_filter(data):
    """Convert JSON string to Python object"""
    if data:
        return json.loads(data)
    return []

@app.context_processor
def utility_processor():
    """Make utility functions available in templates"""
    return dict(get_accommodation_usage=get_accommodation_usage)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_accommodation_usage(ticket_type):
    """Calculate accommodation usage based on ticket type"""
    usage_map = {
        'Single': 1,
        'Double': 2,
        'Triple': 3
    }
    return usage_map.get(ticket_type, 0)

def get_available_accommodations():
    """Calculate available accommodations (universal count)"""
    total_accommodations = 100  # Total available accommodations
    
    # Count only confirmed bookings
    active_bookings = Booking.query.filter_by(status='confirmed').all()
    booked_accommodations = sum(get_accommodation_usage(b.ticket_type) for b in active_bookings)
    
    # Also count pending bookings that haven't expired
    pending_bookings = Booking.query.filter(
        Booking.status == 'pending',
        Booking.expires_at > datetime.utcnow()
    ).all()
    pending_accommodations = sum(get_accommodation_usage(b.ticket_type) for b in pending_bookings)
    
    used_accommodations = booked_accommodations + pending_accommodations
    available = total_accommodations - used_accommodations
    
    return max(0, available), total_accommodations

def send_booking_confirmation_email(booking):
    """Send confirmation email to lawyer after successful booking"""
    try:
        lawyer = booking.lawyer
        
        # Create email message
        msg = Message(
            subject='Booking Confirmed - Junior National Law Conference',
            recipients=[lawyer.email],
            html=render_template('email_confirmation.html', booking=booking, lawyer=lawyer)
        )
        
        # Send email
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def cancel_expired_bookings():
    """Cancel bookings that expired without receipt upload"""
    expired_bookings = Booking.query.filter(
        Booking.status == 'pending',
        Booking.expires_at <= datetime.utcnow()
    ).all()
    
    for booking in expired_bookings:
        booking.status = 'cancelled'
        db.session.commit()

# Background thread to check and cancel expired bookings
def background_task():
    while True:
        try:
            with app.app_context():
                cancel_expired_bookings()
        except Exception as e:
            print(f"Error in background task: {str(e)}")
        time.sleep(10)  # Check every 10 seconds

# Background thread will be started in before_first_request

# Ensure database is initialized on first request
@app.before_request
def ensure_db_initialized():
    """Ensure database is initialized before handling requests"""
    if not hasattr(app, 'db_initialized'):
        try:
            db.create_all()
            app.db_initialized = True
            # Start background thread if not already started
            if not hasattr(app, 'background_thread_started'):
                threading.Thread(target=background_task, daemon=True).start()
                app.background_thread_started = True
        except Exception as e:
            print(f"Database initialization error: {str(e)}")

@app.route('/health')
def health_check():
    """Health check endpoint for deployment platforms"""
    return jsonify({'status': 'ok'}), 200

@app.route('/')
def index():
    available, total = get_available_accommodations()
    return render_template('index.html', 
                         available_accommodations=available,
                         total_accommodations=total)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        basl_id = request.form.get('basl_id', '').strip()
        nic = request.form.get('nic', '').strip()
        ticket_type = request.form.get('ticket_type', '').strip()
        
        # Validate ticket type
        if ticket_type not in ['Single', 'Double', 'Triple']:
            flash('Please select a valid ticket type.', 'error')
            return redirect(url_for('register'))
        
        # Get additional persons details for Double/Triple
        additional_persons = []
        if ticket_type == 'Double':
            add_name_1 = request.form.get('additional_name_1', '').strip()
            add_basl_1 = request.form.get('additional_basl_1', '').strip()
            add_nic_1 = request.form.get('additional_nic_1', '').strip()
            add_phone_1 = request.form.get('additional_phone_1', '').strip()
            
            if not all([add_name_1, add_basl_1, add_nic_1, add_phone_1]):
                flash('Please provide complete details (Name, BASL ID, NIC, Phone) for the second person in Double booking.', 'error')
                return redirect(url_for('register'))
            
            additional_persons = [{
                'name': add_name_1,
                'basl_id': add_basl_1,
                'nic': add_nic_1,
                'phone': add_phone_1
            }]
        elif ticket_type == 'Triple':
            add_name_1 = request.form.get('additional_name_1', '').strip()
            add_basl_1 = request.form.get('additional_basl_1', '').strip()
            add_nic_1 = request.form.get('additional_nic_1', '').strip()
            add_phone_1 = request.form.get('additional_phone_1', '').strip()
            
            add_name_2 = request.form.get('additional_name_2', '').strip()
            add_basl_2 = request.form.get('additional_basl_2', '').strip()
            add_nic_2 = request.form.get('additional_nic_2', '').strip()
            add_phone_2 = request.form.get('additional_phone_2', '').strip()
            
            if not all([add_name_1, add_basl_1, add_nic_1, add_phone_1, add_name_2, add_basl_2, add_nic_2, add_phone_2]):
                flash('Please provide complete details (Name, BASL ID, NIC, Phone) for both additional persons in Triple booking.', 'error')
                return redirect(url_for('register'))
            
            additional_persons = [
                {
                    'name': add_name_1,
                    'basl_id': add_basl_1,
                    'nic': add_nic_1,
                    'phone': add_phone_1
                },
                {
                    'name': add_name_2,
                    'basl_id': add_basl_2,
                    'nic': add_nic_2,
                    'phone': add_phone_2
                }
            ]
        
        # Check if main BASL ID already exists
        existing_basl = Lawyer.query.filter_by(basl_id=basl_id).first()
        if existing_basl:
            flash(f'This BASL ID ({basl_id}) has already been registered. Please use a different BASL ID.', 'error')
            return redirect(url_for('register'))
        
        # Check if main NIC already exists
        existing_nic = Lawyer.query.filter_by(nic=nic).first()
        if existing_nic:
            flash(f'This NIC ({nic}) has already been registered. Please use a different NIC.', 'error')
            return redirect(url_for('register'))
        
        # Check if additional persons' BASL IDs and NICs already exist
        all_basl_ids_to_check = [basl_id] + [p['basl_id'] for p in additional_persons]
        all_nics_to_check = [nic] + [p['nic'] for p in additional_persons]
        
        for check_basl_id in all_basl_ids_to_check:
            existing = Lawyer.query.filter_by(basl_id=check_basl_id).first()
            if existing:
                flash(f'The BASL ID ({check_basl_id}) has already been registered.', 'error')
                return redirect(url_for('register'))
        
        for check_nic in all_nics_to_check:
            existing = Lawyer.query.filter_by(nic=check_nic).first()
            if existing:
                flash(f'The NIC ({check_nic}) has already been registered.', 'error')
                return redirect(url_for('register'))
        
        # Check if email already exists
        existing_email = Lawyer.query.filter_by(email=email).first()
        if existing_email:
            flash('This email has already been registered.', 'error')
            return redirect(url_for('register'))
        
        # Check accommodation availability
        available, total = get_available_accommodations()
        required_accommodations = get_accommodation_usage(ticket_type)
        
        if required_accommodations > available:
            flash(f'Insufficient accommodations available. Only {available} accommodations left.', 'error')
            return redirect(url_for('register'))
        
        # Create new lawyer
        lawyer = Lawyer(name=name, email=email, phone=phone, basl_id=basl_id, nic=nic)
        db.session.add(lawyer)
        db.session.commit()
        
        # Create booking
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        booking = Booking(
            lawyer_id=lawyer.id,
            ticket_type=ticket_type,
            additional_basl_ids=json.dumps(additional_persons) if additional_persons else None,
            status='pending',
            expires_at=expires_at
        )
        db.session.add(booking)
        db.session.commit()
        
        return redirect(url_for('upload_receipt', booking_id=booking.id))
    
    available, total = get_available_accommodations()
    return render_template('register.html',
                         available_accommodations=available,
                         total_accommodations=total)

@app.route('/upload_receipt/<int:booking_id>', methods=['GET', 'POST'])
def upload_receipt(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if booking has expired
    if booking.expires_at <= datetime.utcnow() and booking.status == 'pending':
        booking.status = 'cancelled'
        db.session.commit()
        flash('Booking expired. Please create a new booking.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        if 'receipt' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('upload_receipt', booking_id=booking_id))
        
        file = request.files['receipt']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('upload_receipt', booking_id=booking_id))
        
        if file and allowed_file(file.filename):
            try:
                # Create booking-specific folder
                booking_folder = os.path.join(app.config['UPLOAD_FOLDER'], f'booking_{booking_id}')
                os.makedirs(booking_folder, exist_ok=True)
                
                # Generate filename with timestamp
                original_filename = secure_filename(file.filename)
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{original_filename}"
                
                # Save file in booking folder
                filepath = os.path.join(booking_folder, filename)
                file.save(filepath)
                
                # Store relative path in database
                relative_path = os.path.join(f'booking_{booking_id}', filename)
                booking.receipt_filename = relative_path
                booking.status = 'confirmed'
                db.session.commit()
                
                # Send confirmation email
                email_sent = send_booking_confirmation_email(booking)
                if not email_sent:
                    flash('Receipt uploaded successfully! Your booking is confirmed. (Note: Email notification could not be sent)', 'success')
                else:
                    flash('Receipt uploaded successfully! Your booking is confirmed. A confirmation email has been sent.', 'success')
                
                return redirect(url_for('booking_confirmed', booking_id=booking.id))
            except Exception as e:
                flash(f'Error uploading file: {str(e)}', 'error')
                return redirect(url_for('upload_receipt', booking_id=booking_id))
        else:
            flash('Invalid file type. Please upload PNG, JPG, JPEG, or PDF.', 'error')
    
    # Calculate time remaining
    time_remaining = (booking.expires_at - datetime.utcnow()).total_seconds()
    if time_remaining < 0:
        time_remaining = 0
    
    return render_template('upload_receipt.html', 
                         booking=booking,
                         time_remaining=int(time_remaining))

@app.route('/booking_confirmed/<int:booking_id>')
def booking_confirmed(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    return render_template('booking_confirmed.html', booking=booking)

@app.route('/check_status/<int:booking_id>')
def check_status(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    time_remaining = (booking.expires_at - datetime.utcnow()).total_seconds()
    if time_remaining < 0:
        time_remaining = 0
    
    return jsonify({
        'status': booking.status,
        'time_remaining': int(time_remaining),
        'expired': booking.expires_at <= datetime.utcnow()
    })

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password.', 'error')
    
    # If already logged in, redirect to admin
    if session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin():
    """Admin panel to view all bookings"""
    # Get all bookings ordered by creation date (newest first)
    all_bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    
    # Calculate statistics
    total_bookings = len(all_bookings)
    confirmed_bookings = len([b for b in all_bookings if b.status == 'confirmed'])
    pending_bookings = len([b for b in all_bookings if b.status == 'pending'])
    cancelled_bookings = len([b for b in all_bookings if b.status == 'cancelled'])
    
    # Calculate total accommodations used
    total_accommodations_used = sum(get_accommodation_usage(b.ticket_type) for b in all_bookings if b.status == 'confirmed')
    available, total = get_available_accommodations()
    
    return render_template('admin.html',
                         bookings=all_bookings,
                         total_bookings=total_bookings,
                         confirmed_bookings=confirmed_bookings,
                         pending_bookings=pending_bookings,
                         cancelled_bookings=cancelled_bookings,
                         total_accommodations_used=total_accommodations_used,
                         available_accommodations=available,
                         total_accommodations=total)

@app.route('/admin/booking/<int:booking_id>')
@admin_required
def admin_view_booking(booking_id):
    """View detailed information about a specific booking"""
    booking = Booking.query.get_or_404(booking_id)
    return render_template('admin_booking_view.html', booking=booking)

@app.route('/admin/booking/<int:booking_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_booking(booking_id):
    """Edit a booking"""
    booking = Booking.query.get_or_404(booking_id)
    
    if request.method == 'POST':
        # Update booking status
        new_status = request.form.get('status')
        if new_status in ['pending', 'confirmed', 'cancelled']:
            booking.status = new_status
        
        # Update ticket type
        new_ticket_type = request.form.get('ticket_type')
        if new_ticket_type in ['Single', 'Double', 'Triple']:
            booking.ticket_type = new_ticket_type
        
        # Update additional persons details
        additional_persons = []
        if new_ticket_type == 'Double':
            add_name_1 = request.form.get('additional_name_1', '').strip()
            add_basl_1 = request.form.get('additional_basl_1', '').strip()
            add_nic_1 = request.form.get('additional_nic_1', '').strip()
            add_phone_1 = request.form.get('additional_phone_1', '').strip()
            
            if all([add_name_1, add_basl_1, add_nic_1, add_phone_1]):
                additional_persons = [{
                    'name': add_name_1,
                    'basl_id': add_basl_1,
                    'nic': add_nic_1,
                    'phone': add_phone_1
                }]
        elif new_ticket_type == 'Triple':
            add_name_1 = request.form.get('additional_name_1', '').strip()
            add_basl_1 = request.form.get('additional_basl_1', '').strip()
            add_nic_1 = request.form.get('additional_nic_1', '').strip()
            add_phone_1 = request.form.get('additional_phone_1', '').strip()
            
            add_name_2 = request.form.get('additional_name_2', '').strip()
            add_basl_2 = request.form.get('additional_basl_2', '').strip()
            add_nic_2 = request.form.get('additional_nic_2', '').strip()
            add_phone_2 = request.form.get('additional_phone_2', '').strip()
            
            if all([add_name_1, add_basl_1, add_nic_1, add_phone_1, add_name_2, add_basl_2, add_nic_2, add_phone_2]):
                additional_persons = [
                    {
                        'name': add_name_1,
                        'basl_id': add_basl_1,
                        'nic': add_nic_1,
                        'phone': add_phone_1
                    },
                    {
                        'name': add_name_2,
                        'basl_id': add_basl_2,
                        'nic': add_nic_2,
                        'phone': add_phone_2
                    }
                ]
        
        booking.additional_basl_ids = json.dumps(additional_persons) if additional_persons else None
        
        db.session.commit()
        flash('Booking updated successfully!', 'success')
        return redirect(url_for('admin_view_booking', booking_id=booking.id))
    
    additional_basl_list = []
    if booking.additional_basl_ids:
        additional_basl_list = json.loads(booking.additional_basl_ids)
    
    return render_template('admin_booking_edit.html', booking=booking, additional_basl_list=additional_basl_list)

@app.route('/admin/booking/<int:booking_id>/delete', methods=['POST'])
@admin_required
def admin_delete_booking(booking_id):
    """Delete a booking"""
    booking = Booking.query.get_or_404(booking_id)
    lawyer = booking.lawyer
    
    # Delete receipt file if exists
    if booking.receipt_filename:
        receipt_path = os.path.join(app.config['UPLOAD_FOLDER'], booking.receipt_filename)
        if os.path.exists(receipt_path):
            try:
                os.remove(receipt_path)
            except:
                pass
    
    # Delete booking
    db.session.delete(booking)
    
    # Check if lawyer has other bookings, if not, delete lawyer too
    if not lawyer.bookings:
        db.session.delete(lawyer)
    
    db.session.commit()
    flash('Booking deleted successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/receipt/<path:filename>')
@admin_required
def admin_view_receipt(filename):
    """Serve receipt images for viewing"""
    # Filename includes the booking folder path (e.g., booking_1/filename.jpg)
    # Split to get directory and filename
    path_parts = filename.split('/')
    if len(path_parts) > 1:
        directory = '/'.join(path_parts[:-1])
        file = path_parts[-1]
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], directory)
        return send_from_directory(full_path, file)
    else:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # Get port from environment variable (for deployment) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)

