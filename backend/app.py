from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_session import Session
from flask_mail import Mail, Message
import bcrypt
import jwt
import json
import os
from datetime import datetime, timedelta, timezone
import re
import logging
import logging.handlers
import threading
import time
from rate_limit import rate_limit
from scheduler import admit
from chatbox import get_chatbot_response
from dynamicDatabase import (
    setup_metadata_table, create_dynamic_database, insert_dynamic_data, 
    fetch_dynamic_data
)
from email_utils import (
    send_appointment_scheduled_email, send_appointment_confirmed_email,
    send_appointment_cancelled_email, send_appointment_completed_email,
    send_user_registration_email
)
from config import (
    SECRET_KEY, DEBUG, HOST, PORT, SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS, SESSION_TYPE, MAIL_SERVER, MAIL_PORT,
    MAIL_USE_TLS, MAIL_USE_SSL, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER
)
from models import db, User, UserSession, decode_token, get_user_by_token, get_session_by_refresh_token, Hospital, Farmer, Doctor, Appointment, Alert, Service, Page
from system_health_middleware import register_system_health_middleware
from system_health_routes import system_health_bp

# User Hierarchy and Permissions
USER_HIERARCHY = {
    'user': 1,           # Regular user - can register and request services
    'agriculture_admin': 2,  # Farmer admin - manage agriculture/farmer data
    'healthcare_admin': 3,   # Healthcare admin - manage healthcare data
    'healthcare_admin2': 6,  # Secondary healthcare admin role
    'admin': 4,          # General admin - manage users and system
    'super_admin': 5     # Overall admin - full access to everything
}

PERMISSIONS = {
    # User permissions
    'register': ['user', 'agriculture_admin', 'healthcare_admin', 'admin', 'super_admin'],
    'request_service': ['user', 'agriculture_admin', 'healthcare_admin', 'admin', 'super_admin'],

    # Healthcare permissions
    'view_healthcare': ['user', 'healthcare_admin', 'healthcare_admin2', 'admin', 'super_admin'],
    'manage_healthcare': ['healthcare_admin', 'healthcare_admin2', 'admin', 'super_admin'],

    # Agriculture permissions
    'view_agriculture': ['user', 'agriculture_admin', 'admin', 'super_admin'],
    'manage_agriculture': ['agriculture_admin', 'admin', 'super_admin'],

    # Admin permissions
    'manage_users': ['admin', 'super_admin'],
    'manage_system': ['super_admin'],

    # Super admin permissions (full CRUD access to all data)
    'full_access': ['super_admin'],
    'create_admins': ['super_admin'],  # Can create any type of admin
    'manage_all_data': ['super_admin']  # Can add, update, delete all hospitals, doctors, farmers, users
}

def check_permission(user, permission):
    """Check if user has the required permission"""
    if not user:
        return False
    
    user_role = user.role
    if user_role not in USER_HIERARCHY:
        return False
    
    # If user has full_access, allow everything
    if user_role in PERMISSIONS.get('full_access', []):
        return True
    
    if user_role not in PERMISSIONS.get(permission, []):
        return False
    
    return True

def require_permission(permission):
    """Decorator to require specific permission for endpoint"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            access_token = request.cookies.get('access_token')
            if not access_token:
                return jsonify({'error': 'Authentication required'}), 401
            
            user = get_user_by_token(access_token)
            if not check_permission(user, permission):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            # Apply rate limiting
            rate_limit(user.username if user else request.remote_addr)
            
            return f(user, *args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

def require_auth(f):
    """Decorator to require authentication"""
    def wrapper(*args, **kwargs):
        access_token = request.cookies.get('access_token')
        if not access_token:
            return jsonify({'error': 'Authentication required'}), 401
        
        user = get_user_by_token(access_token)
        if not user:
            return jsonify({'error': 'Invalid authentication'}), 401
        
        # Apply rate limiting
        rate_limit(user.username)
        
        return f(user, *args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

app = Flask(__name__)
CORS(app, supports_credentials=True)  # Enable CORS with credentials

# Configure logging with rotation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler(
            'app.log',
            maxBytes=10*1024*1024,  # 10MB per file
            backupCount=5  # Keep 5 backup files
        ),
        logging.StreamHandler()
    ]
)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_TYPE'] = SESSION_TYPE

# Email configuration
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER

# Background log cleanup function
def log_cleanup_worker():
    """Background worker to periodically clean up old log files"""
    while True:
        try:
            # Import here to avoid circular imports
            import subprocess
            import sys
            # Run log cleanup every 24 hours
            result = subprocess.run([sys.executable, 'log_cleanup.py'],
                                  cwd=os.path.dirname(__file__),
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                logging.info(f"Log cleanup: {result.stdout.strip()}")
        except Exception as e:
            logging.error(f"Log cleanup failed: {e}")
        finally:
            # Sleep for 24 hours
            time.sleep(24 * 60 * 60)

# Start background log cleanup thread
cleanup_thread = threading.Thread(target=log_cleanup_worker, daemon=True)
cleanup_thread.start()

# Initialize extensions
db.init_app(app)
Session(app)
mail = Mail(app)

# Create database tables
with app.app_context():
    db.create_all()
    # Create admin users if not exists
    admin_users = [
        {'username': 'superadmin', 'email': 'superadmin@govconnect.com', 'full_name': 'Super Administrator', 'password': 'super123', 'role': 'super_admin'},
        {'username': 'admin', 'email': 'admin@govconnect.com', 'full_name': 'System Administrator', 'password': 'admin123', 'role': 'admin'},
        {'username': 'healthadmin', 'email': 'healthadmin@govconnect.com', 'full_name': 'Healthcare Administrator', 'password': 'health123', 'role': 'healthcare_admin'},
        {'username': 'agriadmin', 'email': 'agriadmin@govconnect.com', 'full_name': 'Agriculture Administrator', 'password': 'agri123', 'role': 'agriculture_admin'},
        {'username': 'user', 'email': 'user@govconnect.com', 'full_name': 'Regular User', 'password': 'user123', 'role': 'user'},
        # Additional demo users
        {'username': 'healthadmin2', 'email': 'healthadmin2@govconnect.com', 'full_name': 'Healthcare Admin 2', 'password': 'health123', 'role': 'healthcare_admin'},
        {'username': 'agriadmin2', 'email': 'agriadmin2@govconnect.com', 'full_name': 'Agriculture Admin 2', 'password': 'agri123', 'role': 'agriculture_admin'},
        {'username': 'admin2', 'email': 'admin2@govconnect.com', 'full_name': 'System Admin 2', 'password': 'admin123', 'role': 'admin'},
        {'username': 'demo_user1', 'email': 'demo1@govconnect.com', 'full_name': 'Demo User One', 'password': 'demo123', 'role': 'user'},
        {'username': 'demo_user2', 'email': 'demo2@govconnect.com', 'full_name': 'Demo User Two', 'password': 'demo123', 'role': 'user'},
        {'username': 'demo_user3', 'email': 'demo3@govconnect.com', 'full_name': 'Demo User Three', 'password': 'demo123', 'role': 'user'},
        {'username': 'farmer1', 'email': 'farmer1@govconnect.com', 'full_name': 'John Farmer', 'password': 'farmer123', 'role': 'user'},
        {'username': 'farmer2', 'email': 'farmer2@govconnect.com', 'full_name': 'Jane Farmer', 'password': 'farmer123', 'role': 'user'},
        {'username': 'doctor1', 'email': 'doctor1@govconnect.com', 'full_name': 'Dr. Smith', 'password': 'doctor123', 'role': 'user'},
        {'username': 'doctor2', 'email': 'doctor2@govconnect.com', 'full_name': 'Dr. Johnson', 'password': 'doctor123', 'role': 'user'}
    ]

    for admin_data in admin_users:
        admin_user = User.query.filter_by(username=admin_data['username']).first()
        if not admin_user:
            admin_user = User(
                username=admin_data['username'],
                email=admin_data['email'],
                full_name=admin_data['full_name'],
                password=admin_data['password']
            )
            admin_user.role = admin_data['role']
            db.session.add(admin_user)
            print(f"{admin_data['role']} user created: username='{admin_data['username']}', password='{admin_data['password']}'")
        else:
            print(f"{admin_data['role']} user already exists")
    
    # Commit all the new users to the database
    db.session.commit()

# Register system health monitoring
register_system_health_middleware(app)
app.register_blueprint(system_health_bp)

@app.route('/auth/login', methods=['POST'])
def login():
    """Login endpoint"""
    try:
        # Apply rate limiting based on IP or user identifier
        user_id = request.remote_addr  # Use IP for rate limiting
        rate_limit(user_id)

        data = request.get_json()

        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Username and password are required'}), 400

        username = data['username']
        password = data['password']

        # Find user in database
        user = User.query.filter_by(username=username, is_active=True).first()
        if not user or not user.check_password(password):
            logging.warning(f"Failed login attempt for username: {username} from IP: {request.remote_addr}")
            return jsonify({'error': 'Invalid username or password'}), 401

        logging.info(f"Successful login for user: {username} from IP: {request.remote_addr}")

        # Generate tokens
        access_token = user.generate_access_token()
        refresh_token = user.generate_refresh_token()

        # Create session
        session = UserSession(
            user_id=user.id,
            session_token=access_token,
            refresh_token=refresh_token,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(session)
        db.session.commit()

        # Schedule a login tracking task
        admit({
            'type': 'user_login',
            'username': username,
            'user_id': user.id,
            'timestamp': datetime.utcnow().isoformat(),
            'ip': request.remote_addr
        }, priority=1)

        # Create response with cookies
        response = make_response(jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'fullName': user.full_name,
                'email': user.email,
                'role': user.role
            }
        }), 200)

        # Set secure cookies
        response.set_cookie(
            'access_token',
            access_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax',
            max_age=30 * 60  # 30 minutes
        )

        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax',
            max_age=7 * 24 * 60 * 60  # 7 days
        )

        return response

    except Exception as e:
        print(f"Login error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/auth/register', methods=['POST'])
def register():
    """Registration endpoint"""
    try:
        # Apply rate limiting
        user_id = request.remote_addr
        rate_limit(user_id)

        data = request.get_json()

        required_fields = ['username', 'password', 'fullName', 'email']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'All fields are required'}), 400

        username = data['username']
        password = data['password']
        full_name = data['fullName']
        email = data['email']

        # Basic validation
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400

        if '@' not in email or '.' not in email:
            return jsonify({'error': 'Please enter a valid email address'}), 400

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 409

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409

        # Create new user
        user = User(username=username, email=email, full_name=full_name, password=password)
        db.session.add(user)
        db.session.commit()

        # Schedule a registration tracking task
        admit({
            'type': 'user_registration',
            'username': username,
            'email': email,
            'user_id': user.id,
            'timestamp': datetime.utcnow().isoformat(),
            'ip': request.remote_addr
        }, priority=2)

        # Send welcome email
        try:
            send_user_registration_email(user)
        except Exception as email_error:
            logging.error(f"Failed to send user registration email: {email_error}")
            # Don't fail registration if email fails

        return jsonify({
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'fullName': user.full_name,
                'email': user.email
            }
        }), 201

    except Exception as e:
        print(f"Registration error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/auth/verify', methods=['GET'])
def verify():
    """Verify token endpoint"""
    try:
        # Try to get token from cookie first, then from Authorization header
        access_token = request.cookies.get('access_token')
        if not access_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

        if not access_token:
            return jsonify({'error': 'Token is required'}), 401

        user = get_user_by_token(access_token)
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Apply rate limiting
        rate_limit(user.username)

        return jsonify({
            'valid': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'fullName': user.full_name,
                'email': user.email,
                'role': user.role
            }
        }), 200

    except Exception as e:
        print(f"Verification error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/auth/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token"""
    try:
        refresh_token = request.cookies.get('refresh_token')
        if not refresh_token:
            return jsonify({'error': 'Refresh token required'}), 401

        # Get session by refresh token
        session = get_session_by_refresh_token(refresh_token)
        if not session or session.is_expired():
            return jsonify({'error': 'Invalid or expired refresh token'}), 401

        user = session.user
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401

        # Generate new access token
        new_access_token = user.generate_access_token()

        # Update session with new access token
        session.session_token = new_access_token
        session.extend_session()
        db.session.commit()

        # Create response with new access token cookie
        response = make_response(jsonify({
            'message': 'Token refreshed successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'fullName': user.full_name,
                'email': user.email
            }
        }), 200)

        response.set_cookie(
            'access_token',
            new_access_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax',
            max_age=30 * 60  # 30 minutes
        )

        return response

    except Exception as e:
        print(f"Token refresh error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    try:
        access_token = request.cookies.get('access_token')
        refresh_token = request.cookies.get('refresh_token')

        # Invalidate session if tokens are provided
        if refresh_token:
            session = get_session_by_refresh_token(refresh_token)
            if session:
                session.is_active = False
                db.session.commit()

        # Create response that clears cookies
        response = make_response(jsonify({'message': 'Logged out successfully'}), 200)

        response.set_cookie('access_token', '', expires=0, httponly=True)
        response.set_cookie('refresh_token', '', expires=0, httponly=True)

        return response

    except Exception as e:
        print(f"Logout error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/auth/me', methods=['GET'])
def get_current_user():
    """Get current user information"""
    try:
        # Get token from cookie or Authorization header
        access_token = request.cookies.get('access_token')
        if not access_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

        if not access_token:
            return jsonify({'error': 'Unauthorized'}), 401

        # Get user from token
        user = get_user_by_token(access_token)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        return jsonify({
            'id': user.id,
            'username': user.username,
            'fullName': user.full_name,
            'email': user.email,
            'role': user.role
        }), 200

    except Exception as e:
        print(f"Get user error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/auth/me', methods=['PUT'])
@require_auth
def update_current_user(user):
    """Update current user profile"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update allowed fields for self
        if 'full_name' in data:
            if len(data['full_name']) < 2 or len(data['full_name']) > 120:
                return jsonify({'error': 'Full name must be between 2 and 120 characters'}), 400
            user.full_name = data['full_name']
        
        if 'email' in data:
            # Basic email validation
            import re
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', data['email']):
                return jsonify({'error': 'Invalid email format'}), 400
            user.email = data['email']
        
        if 'password' in data:
            if len(data['password']) < 6:
                return jsonify({'error': 'Password must be at least 6 characters long'}), 400
            user.set_password(data['password'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'fullName': user.full_name,
                'email': user.email,
                'role': user.role
            }
        }), 200

    except Exception as e:
        print(f"Update user error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/tasks/submit', methods=['POST'])
def submit_task():
    """Submit a task to the worker pool"""
    try:
        # Verify authentication
        access_token = request.cookies.get('access_token')
        if not access_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

        if not access_token:
            return jsonify({'error': 'Authentication required'}), 401

        user = get_user_by_token(access_token)
        if not user:
            return jsonify({'error': 'Invalid token'}), 401

        # Apply rate limiting
        rate_limit(user.username)

        data = request.get_json()
        if not data or 'taskType' not in data:
            return jsonify({'error': 'Task type is required'}), 400

        task_data = {
            'type': data['taskType'],
            'username': user.username,
            'user_id': user.id,
            'data': data.get('data', {}),
            'timestamp': datetime.utcnow().isoformat(),
            'taskId': secrets.token_hex(8)
        }

        # Schedule the task with appropriate priority
        priority = data.get('priority', 1)
        admit(task_data, priority)

        return jsonify({
            'message': 'Task submitted successfully',
            'taskId': task_data['taskId'],
            'status': 'queued'
        }), 202

    except Exception as e:
        print(f"Task submission error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/dashboard/metrics', methods=['GET'])
def get_dashboard_metrics():
    """Get dashboard metrics (requires authentication)"""
    try:
        # Verify authentication
        access_token = request.cookies.get('access_token')
        if not access_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

        if not access_token:
            return jsonify({'error': 'Authentication required'}), 401

        user = get_user_by_token(access_token)
        if not user:
            return jsonify({'error': 'Invalid token'}), 401

        # Apply rate limiting
        rate_limit(user.username)

        # Schedule a metrics collection task
        admit({
            'type': 'collect_metrics',
            'username': user.username,
            'user_id': user.id,
            'timestamp': datetime.utcnow().isoformat(),
            'taskId': secrets.token_hex(8)
        }, priority=3)

        # Return mock dashboard data (in production, this would come from processed tasks)
        return jsonify({
            'healthcare': {
                'activePatients': 1247,
                'availableBeds': 89,
                'appointmentsToday': 156
            },
            'agriculture': {
                'activeFarms': 342,
                'cropYield': 89.5,
                'waterUsage': 72.3
            },
            'infrastructure': {
                'trafficFlow': 78.2,
                'powerConsumption': 94.1,
                'networkUptime': 99.8
            },
            'alerts': {
                'critical': 3,
                'warning': 12,
                'info': 28
            }
        }), 200

    except Exception as e:
        print(f"Dashboard metrics error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/healthcare/hospitals', methods=['GET'])
def get_hospitals():
    """Get all hospitals (public access for appointment booking)"""
    try:
        hospitals = Hospital.query.all()
        return jsonify({
            'hospitals': [hospital.to_dict() for hospital in hospitals]
        }), 200

    except Exception as e:
        print(f"Get hospitals error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/healthcare/hospitals', methods=['POST'])
@require_permission('manage_healthcare')
def create_hospital(user):
    """Create a new hospital (admin only)"""
    try:
        data = request.get_json()
        required_fields = ['hospitalId', 'name', 'city', 'state', 'type']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'Hospital ID, name, city, state, and type are required'}), 400

        # Input validation
        if not re.match(r'^[A-Z]{3}-[A-Z]{3}-\d{3}$', data['hospitalId']):
            return jsonify({'error': 'Hospital ID must be in format HOS-XXX-001'}), 400

        if len(data['name']) < 3 or len(data['name']) > 200:
            return jsonify({'error': 'Hospital name must be between 3 and 200 characters'}), 400

        if data['type'] not in ['government', 'private', 'semi-government']:
            return jsonify({'error': 'Hospital type must be either government, private, or semi-government'}), 400

        # Check if hospital ID already exists
        if Hospital.query.filter_by(hospital_id=data['hospitalId']).first():
            return jsonify({'error': 'Hospital ID already exists'}), 409

        # Validate optional fields
        if 'email' in data and data['email'] and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', data['email']):
            return jsonify({'error': 'Invalid email format'}), 400

        if 'phone' in data and data['phone'] and not re.match(r'^\+?[\d\s\-\(\)]{10,15}$', data['phone']):
            return jsonify({'error': 'Invalid phone number format'}), 400

        if 'directorEmail' in data and data['directorEmail'] and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', data['directorEmail']):
            return jsonify({'error': 'Invalid director email format'}), 400

        if 'directorPhone' in data and data['directorPhone'] and not re.match(r'^\+?[\d\s\-\(\)]{10,15}$', data['directorPhone']):
            return jsonify({'error': 'Invalid director phone number format'}), 400

        if 'establishedYear' in data and data['establishedYear'] is not None:
            try:
                established_year = int(data['establishedYear'])
                current_year = datetime.now().year
                if not (1800 <= established_year <= current_year):
                    return jsonify({'error': f'Established year must be between 1800 and {current_year}'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Established year must be a valid number'}), 400

        if 'totalBeds' in data and data['totalBeds'] is not None:
            try:
                total_beds = int(data['totalBeds'])
                if total_beds <= 0:
                    return jsonify({'error': 'Total beds must be a positive integer'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Total beds must be a valid positive integer'}), 400

        if 'icuBeds' in data and data['icuBeds'] is not None:
            try:
                icu_beds = int(data['icuBeds'])
                if icu_beds <= 0:
                    return jsonify({'error': 'ICU beds must be a positive integer'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'ICU beds must be a valid positive integer'}), 400

        if 'emergencyBeds' in data and data['emergencyBeds'] is not None:
            try:
                emergency_beds = int(data['emergencyBeds'])
                if emergency_beds <= 0:
                    return jsonify({'error': 'Emergency beds must be a positive integer'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Emergency beds must be a valid positive integer'}), 400

        hospital = Hospital(
            hospital_id=data['hospitalId'],
            name=data['name'],
            city=data['city'],
            state=data['state'],
            type=data['type'],
            address=data.get('address'),
            pincode=data.get('pincode'),
            phone=data.get('phone'),
            email=data.get('email'),
            website=data.get('website'),
            emergency_contact=data.get('emergencyContact'),
            total_beds=data.get('totalBeds'),
            icu_beds=data.get('icuBeds'),
            emergency_beds=data.get('emergencyBeds'),
            specialties=json.dumps(data.get('specialties', [])),
            facilities=json.dumps(data.get('facilities', [])),
            director_name=data.get('directorName'),
            director_phone=data.get('directorPhone'),
            director_email=data.get('directorEmail'),
            established_year=data.get('establishedYear'),
            accreditation=data.get('accreditation'),
            description=data.get('description')
        )

        db.session.add(hospital)
        db.session.commit()

        logging.info(f"Hospital created: {hospital.hospital_id} by user: {user.username}")
        return jsonify({
            'message': 'Hospital created successfully',
            'hospital': hospital.to_dict()
        }), 201

    except Exception as e:
        print(f"Create hospital error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/healthcare/hospitals/<int:hospital_id>', methods=['PUT'])
@require_permission('manage_healthcare')
def update_hospital(user, hospital_id):
    """Update a hospital (admin only)"""
    try:
        hospital = Hospital.query.get(hospital_id)
        if not hospital:
            return jsonify({'error': 'Hospital not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update fields
        if 'name' in data:
            if len(data['name']) < 2 or len(data['name']) > 200:
                return jsonify({'error': 'Hospital name must be between 2 and 200 characters'}), 400
            hospital.name = data['name']

        if 'type' in data:
            if data['type'] not in ['government', 'private', 'charitable']:
                return jsonify({'error': 'Type must be government, private, or charitable'}), 400
            hospital.type = data['type']

        if 'city' in data:
            if len(data['city']) < 2 or len(data['city']) > 100:
                return jsonify({'error': 'City must be between 2 and 100 characters'}), 400
            hospital.city = data['city']

        if 'state' in data:
            if len(data['state']) < 2 or len(data['state']) > 100:
                return jsonify({'error': 'State must be between 2 and 100 characters'}), 400
            hospital.state = data['state']

        if 'address' in data:
            hospital.address = data['address']

        if 'pincode' in data:
            hospital.pincode = data['pincode']

        if 'phone' in data:
            hospital.phone = data['phone']

        if 'email' in data:
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', data['email']):
                return jsonify({'error': 'Invalid email format'}), 400
            hospital.email = data['email']

        if 'totalBeds' in data:
            try:
                total_beds = int(data['totalBeds'])
                if total_beds < 1:
                    return jsonify({'error': 'Total beds must be at least 1'}), 400
                hospital.total_beds = total_beds
            except (ValueError, TypeError):
                return jsonify({'error': 'Total beds must be a valid number'}), 400

        if 'icuBeds' in data:
            try:
                icu_beds = int(data['icuBeds'])
                if icu_beds < 0:
                    return jsonify({'error': 'ICU beds cannot be negative'}), 400
                hospital.icu_beds = icu_beds
            except (ValueError, TypeError):
                return jsonify({'error': 'ICU beds must be a valid number'}), 400

        if 'emergencyBeds' in data:
            try:
                emergency_beds = int(data['emergencyBeds'])
                if emergency_beds < 0:
                    return jsonify({'error': 'Emergency beds cannot be negative'}), 400
                hospital.emergency_beds = emergency_beds
            except (ValueError, TypeError):
                return jsonify({'error': 'Emergency beds must be a valid number'}), 400

        hospital.updated_at = datetime.utcnow()
        db.session.commit()

        logging.info(f"Hospital {hospital_id} updated by user: {user.username}")
        return jsonify({
            'message': 'Hospital updated successfully',
            'hospital': hospital.to_dict()
        }), 200

    except Exception as e:
        print(f"Update hospital error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/healthcare/hospitals/<int:hospital_id>', methods=['DELETE'])
@require_permission('manage_healthcare')
def delete_hospital(user, hospital_id):
    """Delete a hospital (admin only)"""
    try:
        hospital = Hospital.query.get(hospital_id)
        if not hospital:
            return jsonify({'error': 'Hospital not found'}), 404

        # Check if hospital has associated doctors
        associated_doctors = Doctor.query.filter_by(hospital_id=hospital.hospital_id).count()
        if associated_doctors > 0:
            return jsonify({'error': f'Cannot delete hospital with {associated_doctors} associated doctor(s). Remove doctors first.'}), 400

        db.session.delete(hospital)
        db.session.commit()

        logging.info(f"Hospital {hospital_id} deleted by user: {user.username}")
        return jsonify({'message': 'Hospital deleted successfully'}), 200

    except Exception as e:
        print(f"Delete hospital error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/agriculture/farmers', methods=['GET'])
def get_farmers():
    """Get all farmers (requires authentication)"""
    try:
        # Verify authentication
        access_token = request.cookies.get('access_token')
        if not access_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

        if not access_token:
            return jsonify({'error': 'Authentication required'}), 401

        user = get_user_by_token(access_token)
        if not user:
            return jsonify({'error': 'Invalid token'}), 401

        # Apply rate limiting
        rate_limit(user.username)

        farmers = Farmer.query.all()
        return jsonify({
            'farmers': [farmer.to_dict() for farmer in farmers]
        }), 200

    except Exception as e:
        print(f"Get farmers error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/agriculture/farmers', methods=['POST'])
@require_permission('manage_agriculture')
def create_farmer(user):
    """Create a new farmer (admin only)"""
    try:
        data = request.get_json()
        required_fields = ['farmerName', 'mobileNumber', 'location', 'landArea']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'Farmer name, mobile number, location, and land area are required'}), 400

        # Input validation
        if len(data['farmerName']) < 2 or len(data['farmerName']) > 200:
            return jsonify({'error': 'Farmer name must be between 2 and 200 characters'}), 400

        if not re.match(r'^\d{10}$', str(data['mobileNumber'])):
            return jsonify({'error': 'Mobile number must be 10 digits'}), 400

        if len(data['location']) < 2 or len(data['location']) > 200:
            return jsonify({'error': 'Location must be between 2 and 200 characters'}), 400

        try:
            land_area = float(data['landArea'])
            if land_area <= 0 or land_area > 1000:
                return jsonify({'error': 'Land area must be a positive decimal number between 0.01 and 1000 hectares'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Land area must be a valid positive decimal number'}), 400

        farmer = Farmer(
            farmer_name=data['farmerName'],
            mobile_number=data['mobileNumber'],
            location=data['location'],
            land_area=data['landArea']
        )

        db.session.add(farmer)
        db.session.commit()

        logging.info(f"Farmer created: {farmer.farmer_name} by user: {user.username}")
        return jsonify({
            'message': 'Farmer created successfully',
            'farmer': farmer.to_dict()
        }), 201

    except Exception as e:
        print(f"Create farmer error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/agriculture/farmers/<int:farmer_id>', methods=['PUT'])
@require_permission('manage_agriculture')
def update_farmer(user, farmer_id):
    """Update a farmer (admin only)"""
    try:
        farmer = Farmer.query.get(farmer_id)
        if not farmer:
            return jsonify({'error': 'Farmer not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update fields
        if 'farmerName' in data:
            if len(data['farmerName']) < 2 or len(data['farmerName']) > 200:
                return jsonify({'error': 'Farmer name must be between 2 and 200 characters'}), 400
            farmer.farmer_name = data['farmerName']

        if 'mobileNumber' in data:
            if not re.match(r'^\d{10}$', str(data['mobileNumber'])):
                return jsonify({'error': 'Mobile number must be 10 digits'}), 400
            farmer.mobile_number = data['mobileNumber']

        if 'location' in data:
            if len(data['location']) < 2 or len(data['location']) > 200:
                return jsonify({'error': 'Location must be between 2 and 200 characters'}), 400
            farmer.location = data['location']

        if 'landArea' in data:
            try:
                land_area = float(data['landArea'])
                if land_area <= 0 or land_area > 1000:
                    return jsonify({'error': 'Land area must be a positive decimal number between 0.01 and 1000 hectares'}), 400
                farmer.land_area = land_area
            except (ValueError, TypeError):
                return jsonify({'error': 'Land area must be a valid positive decimal number'}), 400

        farmer.updated_at = datetime.utcnow()
        db.session.commit()

        logging.info(f"Farmer {farmer_id} updated by user: {user.username}")
        return jsonify({
            'message': 'Farmer updated successfully',
            'farmer': farmer.to_dict()
        }), 200

    except Exception as e:
        print(f"Update farmer error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/agriculture/farmers/<int:farmer_id>', methods=['DELETE'])
@require_permission('manage_agriculture')
def delete_farmer(user, farmer_id):
    """Delete a farmer (admin only)"""
    try:
        farmer = Farmer.query.get(farmer_id)
        if not farmer:
            return jsonify({'error': 'Farmer not found'}), 404

        db.session.delete(farmer)
        db.session.commit()

        logging.info(f"Farmer {farmer_id} deleted by user: {user.username}")
        return jsonify({'message': 'Farmer deleted successfully'}), 200

    except Exception as e:
        print(f"Delete farmer error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/healthcare/doctors', methods=['GET'])
def get_doctors():
    """Get all doctors (requires authentication)"""
    try:
        # Verify authentication
        access_token = request.cookies.get('access_token')
        if not access_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

        if not access_token:
            return jsonify({'error': 'Authentication required'}), 401

        user = get_user_by_token(access_token)
        if not user:
            return jsonify({'error': 'Invalid token'}), 401

        # Apply rate limiting
        rate_limit(user.username)

        doctors = Doctor.query.all()
        return jsonify({
            'doctors': [doctor.to_dict() for doctor in doctors]
        }), 200

    except Exception as e:
        print(f"Get doctors error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/healthcare/doctors', methods=['POST'])
def create_doctor():
    """Create a new doctor (admin only)"""
    try:
        # Verify authentication
        access_token = request.cookies.get('access_token')
        if not access_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

        if not access_token:
            return jsonify({'error': 'Authentication required'}), 401

        user = get_user_by_token(access_token)
        if not user or user.role not in ['admin', 'healthcare_admin', 'super_admin']:
            return jsonify({'error': 'Healthcare admin access required'}), 403

        # Apply rate limiting
        rate_limit(user.username)

        data = request.get_json()
        required_fields = ['drName', 'hospitalId', 'gender', 'time']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'Doctor name, hospital ID, gender, and time are required'}), 400

        # Input validation
        if len(data['drName']) < 3 or len(data['drName']) > 200:
            return jsonify({'error': 'Doctor name must be between 3 and 200 characters'}), 400

        if not re.match(r'^[A-Z]{3}-[A-Z]{3}-\d{3}$', data['hospitalId']):
            return jsonify({'error': 'Hospital ID must be in format HOS-XXX-001'}), 400

        if data['gender'] not in ['Male', 'Female']:
            return jsonify({'error': 'Gender must be either Male or Female'}), 400

        if not re.match(r'^\d{2}:\d{2}-\d{2}:\d{2}$', data['time']):
            return jsonify({'error': 'Time must be in format HH:MM-HH:MM'}), 400

        # Check if hospital exists
        hospital = Hospital.query.filter_by(hospital_id=data['hospitalId']).first()
        if not hospital:
            return jsonify({'error': 'Hospital not found'}), 404

        doctor = Doctor(
            dr_name=data['drName'],
            hospital_id=data['hospitalId'],
            gender=data['gender'],
            time=data['time']
        )

        db.session.add(doctor)
        db.session.commit()

        logging.info(f"Doctor created: {doctor.dr_name} for hospital {doctor.hospital_id} by user: {user.username}")
        return jsonify({
            'message': 'Doctor created successfully',
            'doctor': doctor.to_dict()
        }), 201

    except Exception as e:
        print(f"Create doctor error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/healthcare/doctors/<int:doctor_id>', methods=['PUT'])
@require_permission('manage_healthcare')
def update_doctor(user, doctor_id):
    """Update a doctor (admin only)"""
    try:
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update fields
        if 'drName' in data:
            if len(data['drName']) < 3 or len(data['drName']) > 200:
                return jsonify({'error': 'Doctor name must be between 3 and 200 characters'}), 400
            doctor.dr_name = data['drName']

        if 'hospitalId' in data:
            if not re.match(r'^[A-Z]{3}-[A-Z]{3}-\d{3}$', data['hospitalId']):
                return jsonify({'error': 'Hospital ID must be in format HOS-XXX-001'}), 400
            # Check if hospital exists
            hospital = Hospital.query.filter_by(hospital_id=data['hospitalId']).first()
            if not hospital:
                return jsonify({'error': 'Hospital not found'}), 404
            doctor.hospital_id = data['hospitalId']

        if 'gender' in data:
            if data['gender'] not in ['Male', 'Female']:
                return jsonify({'error': 'Gender must be either Male or Female'}), 400
            doctor.gender = data['gender']

        if 'time' in data:
            if not re.match(r'^\d{2}:\d{2}-\d{2}:\d{2}$', data['time']):
                return jsonify({'error': 'Time must be in format HH:MM-HH:MM'}), 400
            doctor.time = data['time']

        doctor.updated_at = datetime.utcnow()
        db.session.commit()

        logging.info(f"Doctor {doctor_id} updated by user: {user.username}")
        return jsonify({
            'message': 'Doctor updated successfully',
            'doctor': doctor.to_dict()
        }), 200

    except Exception as e:
        print(f"Update doctor error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/healthcare/doctors/<int:doctor_id>', methods=['DELETE'])
@require_permission('manage_healthcare')
def delete_doctor(user, doctor_id):
    """Delete a doctor (admin only)"""
    try:
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404

        db.session.delete(doctor)
        db.session.commit()

        logging.info(f"Doctor {doctor_id} deleted by user: {user.username}")
        return jsonify({'message': 'Doctor deleted successfully'}), 200

    except Exception as e:
        print(f"Delete doctor error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response

@app.route('/appointments', methods=['GET'])
def get_appointments():
    """Get all appointments (admin only)"""
    try:
        # Verify authentication
        access_token = request.cookies.get('access_token')
        if not access_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

        if not access_token:
            return jsonify({'error': 'Authentication required'}), 401

        user = get_user_by_token(access_token)
        if not user or user.role not in ['admin', 'healthcare_admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        # Apply rate limiting
        rate_limit(user.username)

        appointments = Appointment.query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
        return jsonify({
            'appointments': [appointment.to_dict() for appointment in appointments]
        }), 200

    except Exception as e:
        print(f"Get appointments error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/appointments', methods=['POST'])
def create_appointment():
    """Create a new appointment (anyone can book appointments, admins can create on behalf of users)"""
    try:
        # Check if user is authenticated (optional for public booking)
        user = None
        access_token = request.cookies.get('access_token')
        if not access_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

        if access_token:
            user = get_user_by_token(access_token)

        data = request.get_json()
        required_fields = ['patientName', 'patientEmail', 'patientPhone', 'hospitalId', 'department', 'appointmentDate', 'appointmentTime']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'All required fields must be provided'}), 400

        # Input validation
        if len(data['patientName']) < 2 or len(data['patientName']) > 200:
            return jsonify({'error': 'Patient name must be between 2 and 200 characters'}), 400

        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', data['patientEmail']):
            return jsonify({'error': 'Invalid email format'}), 400

        if not re.match(r'^\d{10}$', str(data['patientPhone'])):
            return jsonify({'error': 'Phone number must be 10 digits'}), 400

        # Check if hospital exists
        hospital = Hospital.query.filter_by(hospital_id=data['hospitalId']).first()
        if not hospital:
            return jsonify({'error': 'Hospital not found'}), 404

        # Validate date and time
        try:
            from datetime import datetime, date, time
            appointment_date = datetime.strptime(data['appointmentDate'], '%Y-%m-%d').date()
            appointment_time = datetime.strptime(data['appointmentTime'], '%H:%M').time()

            # Check if appointment date is not in the past
            if appointment_date < date.today():
                return jsonify({'error': 'Appointment date cannot be in the past'}), 400

        except ValueError:
            return jsonify({'error': 'Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time'}), 400

        # Check for conflicting appointments (same hospital, date, time)
        existing_appointment = Appointment.query.filter_by(
            hospital_id=data['hospitalId'],
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status='scheduled'
        ).first()

        if existing_appointment:
            return jsonify({'error': 'This time slot is already booked'}), 409

        appointment = Appointment(
            patient_name=data['patientName'],
            patient_email=data['patientEmail'],
            patient_phone=data['patientPhone'],
            hospital_id=data['hospitalId'],
            department=data['department'],
            doctor_name=data.get('doctorName'),  # Optional
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            symptoms=data.get('symptoms'),  # Optional
            created_by=user.id if user else None  # Track who created it
        )

        db.session.add(appointment)
        db.session.commit()

        logging.info(f"Appointment created for {appointment.patient_name} at {hospital.name} on {appointment_date}")

        # Send confirmation email
        try:
            send_appointment_scheduled_email(appointment)
        except Exception as email_error:
            logging.error(f"Failed to send appointment scheduled email: {email_error}")
            # Don't fail the appointment creation if email fails

        return jsonify({
            'message': 'Appointment scheduled successfully',
            'appointment': appointment.to_dict()
        }), 201

    except Exception as e:
        print(f"Create appointment error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/appointments/<int:appointment_id>', methods=['PUT'])
def update_appointment_status(appointment_id):
    """Update appointment status (admin only)"""
    try:
        # Verify authentication
        access_token = request.cookies.get('access_token')
        if not access_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

        if not access_token:
            return jsonify({'error': 'Authentication required'}), 401

        user = get_user_by_token(access_token)
        if not user or user.role not in ['admin', 'healthcare_admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        # Apply rate limiting
        rate_limit(user.username)

        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400

        if data['status'] not in ['scheduled', 'confirmed', 'completed', 'cancelled']:
            return jsonify({'error': 'Invalid status'}), 400

        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404

        old_status = appointment.status
        appointment.status = data['status']
        db.session.commit()

        # Send appropriate email based on status change
        try:
            if data['status'] == 'confirmed' and old_status != 'confirmed':
                send_appointment_confirmed_email(appointment)
            elif data['status'] == 'cancelled' and old_status != 'cancelled':
                send_appointment_cancelled_email(appointment)
            elif data['status'] == 'completed' and old_status != 'completed':
                send_appointment_completed_email(appointment)
        except Exception as email_error:
            logging.error(f"Failed to send appointment status update email: {email_error}")
            # Don't fail the status update if email fails

        # Create notification if appointment is confirmed
        if data['status'] == 'confirmed' and old_status != 'confirmed':
            # Create an alert notification for the user
            notification = Alert(
                type='Healthcare',
                message=f'Your appointment at {appointment.department} department has been confirmed for {appointment.appointment_date.strftime("%B %d, %Y")} at {appointment.appointment_time.strftime("%I:%M %p")}.',
                severity='MEDIUM',
                created_by=user.id
            )
            db.session.add(notification)
            db.session.commit()

            logging.info(f"Notification created for confirmed appointment {appointment_id}")

        logging.info(f"Appointment {appointment_id} status updated to {data['status']} by {user.username}")
        return jsonify({
            'message': 'Appointment status updated successfully',
            'appointment': appointment.to_dict()
        }), 200

    except Exception as e:
        print(f"Update appointment error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/appointments/my', methods=['GET'])
def get_my_appointments():
    """Get appointments for a specific email"""
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({'error': 'Email parameter required'}), 400

        appointments = Appointment.query.filter_by(patient_email=email).order_by(
            Appointment.appointment_date.desc(), 
            Appointment.appointment_time.desc()
        ).all()
        
        return jsonify({
            'appointments': [appointment.to_dict() for appointment in appointments]
        }), 200

    except Exception as e:
        print(f"Get my appointments error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }), 200

# User Management Endpoints (Super Admin Only)
@app.route('/admin/users', methods=['GET'])
@require_permission('manage_users')
def get_all_users(user):
    """Get all users (super admin only)"""
    try:
        users = User.query.all()
        users_data = []
        for u in users:
            users_data.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'full_name': u.full_name,
                'role': u.role,
                'is_active': u.is_active,
                'is_system_user': u.username in ['superadmin', 'admin', 'healthadmin', 'agriadmin', 'user'],
                'created_at': u.created_at.isoformat() if u.created_at else None,
                'updated_at': u.updated_at.isoformat() if u.updated_at else None
            })
        
        logging.info(f"Super admin {user.username} accessed user list")
        return jsonify({'users': users_data}), 200
    
    except Exception as e:
        logging.error(f"Error getting users: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/users', methods=['POST'])
@require_permission('manage_users')
def create_user(user):
    """Create a new user (admin and super admin only)"""
    try:
        data = request.get_json()
        required_fields = ['username', 'email', 'full_name', 'password', 'role']
        
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'All fields are required'}), 400
        
        # Validate role
        if data['role'] not in USER_HIERARCHY:
            return jsonify({'error': f'Invalid role. Must be one of: {", ".join(USER_HIERARCHY.keys())}'}), 400

        # Super admin can create any role including other super admins
        if user.role != 'super_admin':
            # Regular admins cannot create super_admin accounts
            if data['role'] == 'super_admin':
                return jsonify({'error': 'Super admin accounts can only be created by super admins'}), 403

            # Regular admins cannot create roles higher than their own
            if USER_HIERARCHY[user.role] < USER_HIERARCHY[data['role']]:
                return jsonify({'error': 'Cannot create user with higher role level'}), 403
        
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        
        if existing_user:
            return jsonify({'error': 'Username or email already exists'}), 409
        
        # Input validation
        if len(data['username']) < 3 or len(data['username']) > 80:
            return jsonify({'error': 'Username must be between 3 and 80 characters'}), 400
        
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        # Create user
        new_user = User(
            username=data['username'],
            email=data['email'],
            full_name=data['full_name'],
            password=data['password']
        )
        new_user.role = data['role']
        
        db.session.add(new_user)
        db.session.commit()
        
        logging.info(f"Super admin {user.username} created user {new_user.username} with role {new_user.role}")
        return jsonify({
            'message': 'User created successfully',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'full_name': new_user.full_name,
                'role': new_user.role,
                'is_active': new_user.is_active
            }
        }), 201
    
    except Exception as e:
        logging.error(f"Error creating user: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/users/<int:user_id>', methods=['PUT'])
@require_permission('manage_users')
def update_user(user, user_id):
    """Update a user (super admin only)"""
    try:
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Prevent super admin from modifying their own role or deactivating themselves
        if target_user.id == user.id:
            return jsonify({'error': 'Cannot modify your own account'}), 403
        
        # Check role hierarchy for updates
        if 'role' in data:
            if data['role'] not in USER_HIERARCHY:
                return jsonify({'error': f'Invalid role. Must be one of: {", ".join(USER_HIERARCHY.keys())}'}), 400

            # Super admin can assign any role
            if user.role != 'super_admin':
                # Cannot assign super_admin role
                if data['role'] == 'super_admin':
                    return jsonify({'error': 'Super admin role can only be assigned by super admins'}), 403

                # Cannot assign roles higher than your own
                if USER_HIERARCHY[user.role] < USER_HIERARCHY[data['role']]:
                    return jsonify({'error': 'Cannot assign higher role level'}), 403

            target_user.role = data['role']
        
        # Update other fields
        if 'full_name' in data:
            if len(data['full_name']) < 2 or len(data['full_name']) > 120:
                return jsonify({'error': 'Full name must be between 2 and 120 characters'}), 400
            target_user.full_name = data['full_name']
        
        if 'is_active' in data:
            target_user.is_active = bool(data['is_active'])
        
        if 'password' in data:
            if len(data['password']) < 6:
                return jsonify({'error': 'Password must be at least 6 characters long'}), 400
            target_user.set_password(data['password'])
        
        db.session.commit()
        
        logging.info(f"Super admin {user.username} updated user {target_user.username}")
        return jsonify({
            'message': 'User updated successfully',
            'user': {
                'id': target_user.id,
                'username': target_user.username,
                'email': target_user.email,
                'full_name': target_user.full_name,
                'role': target_user.role,
                'is_active': target_user.is_active
            }
        }), 200
    
    except Exception as e:
        logging.error(f"Error updating user: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/users/<int:user_id>', methods=['DELETE'])
@require_permission('manage_users')
def delete_user(user, user_id):
    """Delete a user (super admin only)"""
    try:
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Prevent super admin from deleting themselves
        if target_user.id == user.id:
            return jsonify({'error': 'Cannot delete your own account'}), 403
        
        # Super admin can delete any user including other super admins
        # Regular admins can only delete users with lower roles
        if user.role != 'super_admin':
            if target_user.role == 'super_admin':
                return jsonify({'error': 'Cannot delete super admin accounts'}), 403
            if USER_HIERARCHY[user.role] <= USER_HIERARCHY[target_user.role]:
                return jsonify({'error': 'Cannot delete users with equal or higher role level'}), 403
        
        # Hard delete the user
        db.session.delete(target_user)
        db.session.commit()
        
        logging.info(f"User {target_user.username} deleted by {user.username}")
        return jsonify({'message': 'User deleted successfully'}), 200
    
    except Exception as e:
        logging.error(f"Error deleting user: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

# Service Management Endpoints (Super Admin Only)
@app.route('/admin/services', methods=['GET'])
@require_permission('manage_system')
def get_services(user):
    """Get all services (super_admin only)"""
    try:
        services = Service.query.all()
        return jsonify([service.to_dict() for service in services]), 200
    except Exception as e:
        logging.error(f"Error fetching services: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/admin/services', methods=['POST'])
@require_permission('manage_system')
def create_service(user):
    """Create a new service (super_admin only)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate required fields
        required_fields = ['name', 'displayName', 'route', 'componentName']
        for field in required_fields:
            if field not in data or not data[field].strip():
                return jsonify({'error': f'{field} is required'}), 400

        # Validate route format (should start with /)
        if not data['route'].startswith('/'):
            return jsonify({'error': 'Route must start with /'}), 400

        # Check if route already exists
        existing_service = Service.query.filter_by(route=data['route']).first()
        if existing_service:
            return jsonify({'error': 'Service with this route already exists'}), 409

        # Create new service
        new_service = Service(
            name=data['name'].strip(),
            display_name=data['displayName'].strip(),
            description=data.get('description', '').strip(),
            icon=data.get('icon', 'Settings').strip(),
            route=data['route'].strip(),
            component_name=data['componentName'].strip(),
            is_active=data.get('isActive', True),
            is_builtin=False,  # User-created services are not built-in
            created_by=user.id
        )

        db.session.add(new_service)
        db.session.commit()

        logging.info(f"Service {new_service.name} created by {user.username}")
        return jsonify(new_service.to_dict()), 201
    except Exception as e:
        logging.error(f"Error creating service: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/services/<int:service_id>', methods=['PUT'])
def update_service(service_id):
    """Update an existing service"""
    try:
        # Verify user authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        user = get_user_by_token(token)
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Apply rate limiting
        rate_limit(user.username)
        
        # Only super_admin can manage services
        if user.role != 'super_admin':
            return jsonify({'error': 'Access denied. Super admin privileges required.'}), 403
        
        service = Service.query.get(service_id)
        if not service:
            return jsonify({'error': 'Service not found'}), 404
        
        # Cannot modify built-in services
        if service.is_builtin:
            return jsonify({'error': 'Cannot modify built-in services'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields if provided
        if 'name' in data and not data['name'].strip():
            return jsonify({'error': 'Name cannot be empty'}), 400
        if 'displayName' in data and not data['displayName'].strip():
            return jsonify({'error': 'Display name cannot be empty'}), 400
        if 'route' in data:
            if not data['route'].strip():
                return jsonify({'error': 'Route cannot be empty'}), 400
            if not data['route'].startswith('/'):
                return jsonify({'error': 'Route must start with /'}), 400
            # Check if route already exists (excluding current service)
            existing_service = Service.query.filter_by(route=data['route']).filter(Service.id != service_id).first()
            if existing_service:
                return jsonify({'error': 'Service with this route already exists'}), 409
        if 'componentName' in data and not data['componentName'].strip():
            return jsonify({'error': 'Component name cannot be empty'}), 400
        
        # Update service fields
        if 'name' in data:
            service.name = data['name'].strip()
        if 'displayName' in data:
            service.display_name = data['displayName'].strip()
        if 'description' in data:
            service.description = data.get('description', '').strip()
        if 'icon' in data:
            service.icon = data.get('icon', 'Settings').strip()
        if 'route' in data:
            service.route = data['route'].strip()
        if 'componentName' in data:
            service.component_name = data['componentName'].strip()
        if 'isActive' in data:
            service.is_active = data['isActive']
        
        db.session.commit()
        
        logging.info(f"Service {service.name} updated by {user.username}")
        return jsonify(service.to_dict()), 200
    
    except Exception as e:
        logging.error(f"Error updating service: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/services/<int:service_id>', methods=['DELETE'])
def delete_service(service_id):
    """Delete a service"""
    try:
        # Verify user authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        user = get_user_by_token(token)
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Apply rate limiting
        rate_limit(user.username)
        
        # Only super_admin can manage services
        if user.role != 'super_admin':
            return jsonify({'error': 'Access denied. Super admin privileges required.'}), 403
        
        service = Service.query.get(service_id)
        if not service:
            return jsonify({'error': 'Service not found'}), 404
        
        # Cannot delete built-in services
        if service.is_builtin:
            return jsonify({'error': 'Cannot delete built-in services'}), 403
        
        # Delete the service
        db.session.delete(service)
        db.session.commit()
        
        logging.info(f"Service {service.name} deleted by {user.username}")
        return jsonify({'message': 'Service deleted successfully'}), 200
    
    except Exception as e:
        logging.error(f"Error deleting service: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/restart', methods=['POST'])
def restart_backend():
    """Restart the backend server (for service updates)"""
    try:
        # Verify user authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        user = get_user_by_token(token)
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Apply rate limiting
        rate_limit(user.username)
        
        # Only super_admin can restart the backend
        if user.role != 'super_admin':
            return jsonify({'error': 'Access denied. Super admin privileges required.'}), 403
        
        # In a production environment, this would trigger a proper restart mechanism
        # For now, we'll just return a success message
        # The frontend will handle showing a restart notification
        
        logging.info(f"Backend restart requested by {user.username}")
        return jsonify({
            'message': 'Backend restart initiated',
            'note': 'The server will restart momentarily to apply service changes'
        }), 200
    
    except Exception as e:
        logging.error(f"Error initiating restart: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Dynamic Database Endpoints
@app.route('/admin/dynamic/setup', methods=['POST'])
@require_auth
def setup_dynamic_database(user):
    """Initialize dynamic database metadata table"""
    try:
        # Only super_admin can setup dynamic database
        if user.role != 'super_admin':
            return jsonify({'error': 'Access denied. Super admin privileges required.'}), 403
        
        setup_metadata_table()
        
        return jsonify({
            'message': 'Dynamic database setup completed successfully'
        }), 200
    
    except Exception as e:
        logging.error(f"Error setting up dynamic database: {e}")
        return jsonify({'error': 'Internal server error'}), 500
        
        # Apply rate limiting
        rate_limit(user.username)
        
        # Only super_admin can setup dynamic database
        if user.role != 'super_admin':
            return jsonify({'error': 'Access denied. Super admin privileges required.'}), 403
        
        setup_metadata_table()
        return jsonify({'message': 'Dynamic database metadata table initialized successfully'}), 200
    
    except Exception as e:
        logging.error(f"Error setting up dynamic database: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/dynamic/tables', methods=['POST'])
@require_auth
def create_dynamic_table(user):
    """Create a new dynamic table"""
    try:
        # Only super_admin can create dynamic tables
        if user.role != 'super_admin':
            return jsonify({'error': 'Access denied. Super admin privileges required.'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        table_name = data.get('table_name')
        fields = data.get('fields', [])
        data_types = data.get('data_types', [])
        show_ui = data.get('show_ui', [])
        
        if not table_name or not fields or not data_types or not show_ui:
            return jsonify({'error': 'table_name, fields, data_types, and show_ui are required'}), 400
        
        create_dynamic_database(table_name, fields, data_types, show_ui)
        
        return jsonify({
            'message': f'Dynamic table "{table_name}" created successfully',
            'table_name': table_name
        }), 201
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error creating dynamic table: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/dynamic/tables', methods=['GET'])
@require_auth
def get_dynamic_tables(user):
    """Get list of all dynamic tables"""
    try:
        # Only admin and super_admin can view dynamic tables
        if user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
        
        # Import here to avoid circular imports
        import mysql.connector as con
        connector = con.connect(
            host='localhost',
            user='root',
            password='Soul#13211993',
            database='govconnect'
        )
        cursor = connector.cursor(dictionary=True)
        
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        # Filter for dynamic tables (those with metadata)
        cursor.execute("SELECT DISTINCT table_name FROM dynamic_table_meta")
        dynamic_tables = [row['table_name'] for row in cursor.fetchall()]
        
        connector.close()
        
        return jsonify({'tables': dynamic_tables}), 200
    
    except Exception as e:
        logging.error(f"Error getting dynamic tables: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/dynamic/tables/<table_name>/metadata', methods=['GET'])
@require_auth
def get_table_metadata(user, table_name):
    """Get metadata for a specific dynamic table"""
    try:
        # Only admin and super_admin can view table metadata
        if user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
        
        import mysql.connector as con
        connector = con.connect(
            host='localhost',
            user='root',
            password='Soul#13211993',
            database='govconnect'
        )
        cursor = connector.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT field_name, data_type, show_ui 
            FROM dynamic_table_meta 
            WHERE table_name = %s
        """, (table_name,))
        
        metadata = cursor.fetchall()
        connector.close()
        
        if not metadata:
            return jsonify({'error': 'Table not found or no metadata available'}), 404
        
        return jsonify({
            'table_name': table_name,
            'fields': metadata
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting table metadata: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/dynamic/tables/<table_name>/data', methods=['POST'])
@require_auth
def insert_dynamic_table_data(user, table_name):
    """Insert data into a dynamic table"""
    try:
        # Only admin and super_admin can insert data
        if user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        insert_dynamic_data(table_name, data)
        
        return jsonify({
            'message': f'Data inserted into "{table_name}" successfully'
        }), 201
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error inserting data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/dynamic/tables/<table_name>/data', methods=['GET'])
@require_auth
def get_dynamic_table_data(user, table_name):
    """Get data from a dynamic table"""
    try:
        # Only admin and super_admin can view data
        if user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
        
        ui_only = request.args.get('ui_only', 'true').lower() == 'true'
        data = fetch_dynamic_data(table_name, ui_only)
        
        return jsonify({
            'table_name': table_name,
            'data': data,
            'ui_only': ui_only
        }), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/dynamic/tables/<table_name>/data/<int:record_id>', methods=['PUT'])
@require_auth
def update_dynamic_table_data(user, table_name, record_id):
    """Update a record in a dynamic table"""
    try:
        # Only admin and super_admin can update data
        if user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Import the update function (we need to add this to dynamicDatabase.py)
        from dynamicDatabase import update_dynamic_data
        update_dynamic_data(table_name, record_id, data)
        
        return jsonify({
            'message': f'Record {record_id} in "{table_name}" updated successfully'
        }), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error updating data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/dynamic/tables/<table_name>/data/<int:record_id>', methods=['DELETE'])
@require_auth
def delete_dynamic_table_data(user, table_name, record_id):
    """Delete a record from a dynamic table"""
    try:
        # Only admin and super_admin can delete data
        if user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
        
        # Import the delete function (we need to add this to dynamicDatabase.py)
        from dynamicDatabase import delete_dynamic_data
        delete_dynamic_data(table_name, record_id)
        
        return jsonify({
            'message': f'Record {record_id} in "{table_name}" deleted successfully'
        }), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error deleting data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/dynamic/tables/<table_name>', methods=['DELETE'])
@require_auth
def delete_dynamic_table(user, table_name):
    """Delete an entire dynamic table"""
    try:
        # Only super_admin can delete tables
        if user.role != 'super_admin':
            return jsonify({'error': 'Access denied. Super admin privileges required.'}), 403
        
        from dynamicDatabase import delete_dynamic_table
        delete_dynamic_table(table_name)
        
        return jsonify({
            'message': f'Dynamic table "{table_name}" deleted successfully'
        }), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error deleting table: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/dynamic/tables/<table_name>/fields/<field_name>', methods=['DELETE'])
@require_auth
def delete_dynamic_field(user, table_name, field_name):
    """Delete a field from a dynamic table"""
    try:
        # Only super_admin can delete fields
        if user.role != 'super_admin':
            return jsonify({'error': 'Access denied. Super admin privileges required.'}), 403
        
        from dynamicDatabase import delete_dynamic_field
        delete_dynamic_field(table_name, field_name)
        
        return jsonify({
            'message': f'Field "{field_name}" deleted from table "{table_name}" successfully'
        }), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error deleting field: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Dashboard Field Management (using makeSections.py functionality)
dashboard_configs = []

@app.route('/api/fields', methods=['POST'])
@require_auth
def add_dashboard_field(user):
    """Add a new dashboard field configuration"""
    try:
        # Only admin and super_admin can add dashboard fields
        if user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Create dynamic table for the field
        table_name = f"dashboard_{data.get('fieldName', 'field').lower().replace(' ', '_')}_{int(time.time())}"
        
        # Convert inputs to fields format
        fields = []
        data_types = []
        show_ui = []
        
        for input_item in data.get('inputs', []):
            fields.append(input_item.get('label', 'field'))
            # Map input types to database types
            input_type = input_item.get('type', 'text')
            if input_type == 'number':
                data_types.append('int')
            elif input_type == 'boolean':
                data_types.append('bool')
            else:
                data_types.append('string')
            show_ui.append(True)
        
        if fields:
            # Create the dynamic table
            create_dynamic_database(table_name, fields, data_types, show_ui)
        
        # Store configuration
        new_field = {
            "id": len(dashboard_configs) + 1,
            "name": data.get('fieldName'),
            "category": data.get('fieldType'),
            "db_strategy": data.get('dbType'),
            "schema": data.get('inputs'),
            "table_name": table_name,
            "created_at": datetime.utcnow().isoformat()
        }
        
        dashboard_configs.append(new_field)
        
        return jsonify({
            "message": "Dashboard field added successfully!",
            "data": new_field
        }), 201
    
    except Exception as e:
        logging.error(f"Error adding dashboard field: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/fields', methods=['GET'])
@require_auth
def get_dashboard_fields(user):
    """Get all dashboard field configurations"""
    try:
        return jsonify({"fields": dashboard_configs}), 200
    except Exception as e:
        logging.error(f"Error getting dashboard fields: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Full Page Management Endpoints (Super Admin Only)
@app.route('/admin/pages', methods=['POST'])
@require_auth
def create_page(user):
    """Create a new full page (super_admin only)"""
    try:
        # Only super_admin can create pages
        if user.role != 'super_admin':
            return jsonify({'error': 'Access denied. Super admin privileges required.'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        required_fields = ['title', 'route']
        if not all(field in data for field in required_fields):
            return jsonify({'error': f'Required fields: {", ".join(required_fields)}'}), 400

        # Validate route format (should start with /)
        if not data['route'].startswith('/'):
            return jsonify({'error': 'Route must start with /'}), 400

        # Check if route already exists
        existing_page = Page.query.filter_by(route=data['route']).first()
        if existing_page:
            return jsonify({'error': 'Page with this route already exists'}), 409

        # Create new page
        new_page = Page(
            title=data['title'].strip(),
            description=data.get('description', '').strip(),
            route=data['route'].strip(),
            icon=data.get('icon', 'FileText').strip(),
            is_active=data.get('isActive', True),
            is_main_tab=data.get('isMainTab', False),  # Add main tab field
            is_builtin=False,  # User-created pages are not built-in
            created_by=user.id
        )

        db.session.add(new_page)
        db.session.commit()

        logging.info(f"Page '{new_page.title}' created by {user.username}")
        return jsonify(new_page.to_dict()), 201

    except Exception as e:
        logging.error(f"Error creating page: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/pages', methods=['GET'])
@require_auth
def get_pages(user):
    """Get all pages (admin and super_admin only)"""
    try:
        # Only admin and super_admin can view pages
        if user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403

        pages = Page.query.filter_by(is_active=True).order_by(Page.created_at.desc()).all()
        return jsonify([page.to_dict() for page in pages]), 200

    except Exception as e:
        logging.error(f"Error getting pages: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/pages/<int:page_id>', methods=['GET'])
@require_auth
def get_page(user, page_id):
    """Get a specific page (admin and super_admin only)"""
    try:
        # Only admin and super_admin can view pages
        if user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403

        page = Page.query.get(page_id)
        if not page:
            return jsonify({'error': 'Page not found'}), 404

        return jsonify(page.to_dict()), 200

    except Exception as e:
        logging.error(f"Error getting page: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/pages/<int:page_id>', methods=['PUT'])
@require_auth
def update_page(user, page_id):
    """Update a page (super_admin only)"""
    try:
        # Only super_admin can update pages
        if user.role != 'super_admin':
            return jsonify({'error': 'Access denied. Super admin privileges required.'}), 403

        page = Page.query.get(page_id)
        if not page:
            return jsonify({'error': 'Page not found'}), 404

        # Cannot modify built-in pages
        if page.is_builtin:
            return jsonify({'error': 'Cannot modify built-in pages'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Validate required fields if provided
        if 'title' in data and not data['title'].strip():
            return jsonify({'error': 'Title cannot be empty'}), 400
        if 'route' in data:
            if not data['route'].strip():
                return jsonify({'error': 'Route cannot be empty'}), 400
            if not data['route'].startswith('/'):
                return jsonify({'error': 'Route must start with /'}), 400
            # Check if route already exists (excluding current page)
            existing_page = Page.query.filter_by(route=data['route']).filter(Page.id != page_id).first()
            if existing_page:
                return jsonify({'error': 'Page with this route already exists'}), 409

        # Update page fields
        if 'title' in data:
            page.title = data['title'].strip()
        if 'description' in data:
            page.description = data.get('description', '').strip()
        if 'route' in data:
            page.route = data['route'].strip()
        if 'icon' in data:
            page.icon = data.get('icon', 'FileText').strip()
        if 'isActive' in data:
            page.is_active = data['isActive']
        if 'isMainTab' in data:
            page.is_main_tab = data['isMainTab']

        db.session.commit()

        logging.info(f"Page '{page.title}' updated by {user.username}")
        return jsonify(page.to_dict()), 200

    except Exception as e:
        logging.error(f"Error updating page: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/pages/<int:page_id>', methods=['DELETE'])
@require_auth
def delete_page(user, page_id):
    """Delete a page (super_admin only)"""
    try:
        # Only super_admin can delete pages
        if user.role != 'super_admin':
            return jsonify({'error': 'Access denied. Super admin privileges required.'}), 403

        page = Page.query.get(page_id)
        if not page:
            return jsonify({'error': 'Page not found'}), 404

        # Cannot delete built-in pages
        if page.is_builtin:
            return jsonify({'error': 'Cannot delete built-in pages'}), 403

        # Delete the page
        db.session.delete(page)
        db.session.commit()

        logging.info(f"Page '{page.title}' deleted by {user.username}")
        return jsonify({'message': 'Page deleted successfully'}), 200

    except Exception as e:
        logging.error(f"Error deleting page: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

# Alert Management Endpoints
@app.route('/alerts', methods=['GET'])
def get_alerts():
    """Get all active alerts (public access for dashboard display)"""
    try:
        # Allow public access to alerts for dashboard display
        # But still apply rate limiting based on IP
        user_id = request.remote_addr
        rate_limit(user_id)

        alerts = Alert.query.filter_by(is_active=True).order_by(Alert.created_at.desc()).all()

        return jsonify({
            'alerts': [alert.to_dict() for alert in alerts]
        }), 200

    except Exception as e:
        logging.error(f"Error getting alerts: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/alerts', methods=['POST'])
@require_auth
def create_alert(user):
    """Create a new alert (admin and super_admin only)"""
    try:
        # Only admin and super_admin can create alerts
        if user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        required_fields = ['type', 'message', 'severity']
        if not all(field in data for field in required_fields):
            return jsonify({'error': f'Required fields: {", ".join(required_fields)}'}), 400
        
        # Validate severity
        if data['severity'] not in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            return jsonify({'error': 'Severity must be one of: CRITICAL, HIGH, MEDIUM, LOW'}), 400
        
        # Validate type
        valid_types = ['Healthcare', 'Agriculture', 'System', 'General']
        if data['type'] not in valid_types:
            return jsonify({'error': f'Type must be one of: {", ".join(valid_types)}'}), 400
        
        alert = Alert(
            type=data['type'],
            message=data['message'],
            severity=data['severity'],
            created_by=user.id
        )
        
        db.session.add(alert)
        db.session.commit()
        
        logging.info(f"Alert created by {user.username}: {alert.type} - {alert.severity}")
        return jsonify({
            'message': 'Alert created successfully',
            'alert': alert.to_dict()
        }), 201
    
    except Exception as e:
        logging.error(f"Error creating alert: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/alerts/<int:alert_id>', methods=['DELETE'])
@require_auth
def delete_alert(user, alert_id):
    """Delete an alert (admin and super_admin only)"""
    try:
        # Only admin and super_admin can delete alerts
        if user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
        
        alert = Alert.query.get(alert_id)
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404
        
        alert.is_active = False
        db.session.commit()
        
        logging.info(f"Alert {alert_id} deleted by {user.username}")
        return jsonify({'message': 'Alert deleted successfully'}), 200
    
    except Exception as e:
        logging.error(f"Error deleting alert: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

# Dashboard Statistics Endpoints
@app.route('/dashboard/stats/users', methods=['GET'])
@require_auth
def get_user_count(user):
    """Get total number of active users"""
    try:
        user_count = User.query.filter_by(is_active=True).count()
        
        return jsonify({
            'total_users': user_count
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting user count: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/dashboard/stats/services', methods=['GET'])
@require_auth
def get_services_count(user):
    """Get total number of active services"""
    try:
        # Count built-in services (home, healthcare, agriculture, alerts, system-health, admin)
        builtin_services = 6  # home, healthcare, agriculture, alerts, system-health, admin
        
        # Add dynamic full sections
        dynamic_sections = Service.query.filter_by(is_active=True).count()
        
        total_services = builtin_services + dynamic_sections
        
        return jsonify({
            'active_services': total_services
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting services count: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/dashboard/stats/regions', methods=['GET'])
@require_auth
def get_regions_count(user):
    """Get number of regions (configurable by super admin)"""
    try:
        # Check if there's a dynamic table for regions configuration
        try:
            # Look for tables with "region" in the name
            regions_data = fetch_dynamic_data('user_section_regions', ui_only=True)
            if regions_data and len(regions_data) > 0:
                # Use the first record's regions_count
                regions_count = regions_data[0].get('regions_count') or regions_data[0].get('count') or regions_data[0].get('number')
                if regions_count:
                    return jsonify({
                        'regions': int(regions_count)
                    }), 200
        except:
            pass
        
        # Default fallback
        return jsonify({
            'regions': 36
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting regions count: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/dashboard/stats/alerts-today', methods=['GET'])
@require_auth
def get_alerts_today_count(user):
    """Get number of alerts created today"""
    try:
        from datetime import date
        today = date.today()
        
        alerts_today = Alert.query.filter(
            Alert.created_at >= today,
            Alert.is_active == True
        ).count()
        
        return jsonify({
            'alerts_today': alerts_today
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting alerts today count: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/dashboard/stats/requests-per-minute', methods=['GET'])
@require_auth
def get_requests_per_minute_stats(user):
    """Get current requests per minute from system health AI"""
    try:
        from system_health_ai import compute_health_score
        
        health_data = compute_health_score()
        requests_per_minute = health_data.get('metrics', {}).get('requests_per_min', 0)
        
        return jsonify({
            'requests_per_minute': requests_per_minute
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting requests per minute: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Settings Endpoints
@app.route('/settings/regions', methods=['GET'])
@require_auth
def get_regions_setting(user):
    """Get regions count setting"""
    try:
        # For now, return a default value. In a real app, this would be stored in a settings table
        return jsonify({
            'regions_count': 36
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting regions setting: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/settings/regions', methods=['PUT'])
@require_permission('manage_system')
def update_regions_setting(user):
    """Update regions count setting (super admin only)"""
    try:
        data = request.get_json()
        if not data or 'regions_count' not in data:
            return jsonify({'error': 'regions_count is required'}), 400
        
        regions_count = int(data['regions_count'])
        if regions_count <= 0:
            return jsonify({'error': 'Regions count must be a positive integer'}), 400
        
        # In a real app, save to database
        # For now, just return success
        return jsonify({
            'message': 'Regions count updated successfully',
            'regions_count': regions_count
        }), 200
    
    except ValueError:
        return jsonify({'error': 'Regions count must be a valid integer'}), 400
    except Exception as e:
        logging.error(f"Error updating regions setting: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Healthcare Statistics Endpoints
@app.route('/healthcare/stats/users', methods=['GET'])
@require_auth
def get_healthcare_user_count(user):
    """Get total number of users registered in healthcare system"""
    try:
        # For healthcare, we might want to count users who have made appointments or are registered patients
        # For now, return total active users (same as dashboard)
        user_count = User.query.filter_by(is_active=True).count()
        
        return jsonify({
            'total_users': user_count
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting healthcare user count: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/healthcare/stats/doctors', methods=['GET'])
@require_auth
def get_doctor_count(user):
    """Get total number of registered doctors"""
    try:
        from models import Doctor
        doctor_count = Doctor.query.count()
        
        return jsonify({
            'total_doctors': doctor_count
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting doctor count: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/dashboard/stats/requests-per-minute', methods=['GET'])
@require_auth
def get_requests_per_minute(user):
    """Get requests per minute from system health AI"""
    try:
        from system_health_ai import compute_health_score
        
        health_data = compute_health_score()
        requests_per_min = health_data.get('metrics', {}).get('requests_per_min', 0)
        
        return jsonify({
            'requests_per_minute': requests_per_min
        }), 200
    
    except Exception as e:
        logging.error(f"Error getting requests per minute: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Chat Endpoint (authenticated users only)
@app.route('/chat', methods=['POST'])
@require_auth
def chat(user):
    """Get AI-powered chatbot response (requires authentication for all users)"""
    try:
        # Apply rate limiting based on username
        user_id = user.username if user else request.remote_addr
        rate_limit(user_id)

        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400

        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        # Get chatbot response (conversation scoped to username)
        bot_response = get_chatbot_response(user_message, user_id)

        return jsonify({
            'response': bot_response,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200

    except Exception as e:
        logging.error(f"Error in chat endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting GovConnect Backend...")
    print("Available endpoints:")
    print("POST /auth/login")
    print("POST /auth/register")
    print("GET /auth/verify")
    print("POST /auth/refresh")
    print("POST /auth/logout")
    print("POST /tasks/submit")
    print("GET /healthcare/hospitals")
    print("POST /healthcare/hospitals")
    print("PUT /healthcare/hospitals/<hospital_id>")
    print("DELETE /healthcare/hospitals/<hospital_id>")
    print("GET /healthcare/doctors")
    print("POST /healthcare/doctors")
    print("PUT /healthcare/doctors/<doctor_id>")
    print("DELETE /healthcare/doctors/<doctor_id>")
    print("GET /agriculture/farmers")
    print("POST /agriculture/farmers")
    print("PUT /agriculture/farmers/<farmer_id>")
    print("DELETE /agriculture/farmers/<farmer_id>")
    print("GET /appointments")
    print("POST /appointments")
    print("PUT /appointments/<appointment_id>")
    print("GET /appointments/my")
    print("GET /dashboard/metrics")
    print("GET /health")
    
    # User Management Endpoints (Super Admin Only)
    print("GET /admin/users")
    print("POST /admin/users")
    print("PUT /admin/users/<user_id>")
    print("DELETE /admin/users/<user_id>")
    
    # Service Management Endpoints (Super Admin Only)
    print("GET /admin/services")
    print("POST /admin/services")
    print("PUT /admin/services/<service_id>")
    print("DELETE /admin/services/<service_id>")
    print("POST /admin/restart")
    
    # Dynamic Database Endpoints (Admin/Super Admin Only)
    print("POST /admin/dynamic/setup")
    print("POST /admin/dynamic/tables")
    print("GET /admin/dynamic/tables")
    print("GET /admin/dynamic/tables/<table_name>/metadata")
    print("POST /admin/dynamic/tables/<table_name>/data")
    print("GET /admin/dynamic/tables/<table_name>/data")
    print("PUT /admin/dynamic/tables/<table_name>/data/<record_id>")
    print("DELETE /admin/dynamic/tables/<table_name>/data/<record_id>")
    print("DELETE /admin/dynamic/tables/<table_name>")
    print("DELETE /admin/dynamic/tables/<table_name>/fields/<field_name>")
    
    # Dashboard Field Management Endpoints (Admin/Super Admin Only)
    print("POST /api/fields")
    print("GET /api/fields")
    
    # Full Page Management Endpoints (Super Admin Only)
    print("POST /admin/pages")
    print("GET /admin/pages")
    print("GET /admin/pages/<page_id>")
    print("PUT /admin/pages/<page_id>")
    print("DELETE /admin/pages/<page_id>")
    
    # Alert Endpoints
    print("GET /alerts")
    print("POST /alerts")
    print("DELETE /alerts/<alert_id>")
    
    # Chat Endpoint
    print("POST /chat")
    
    print(f"Running on {HOST}:{PORT}")
    app.run(debug=DEBUG, host=HOST, port=PORT)