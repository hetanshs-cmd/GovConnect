from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import bcrypt
import jwt
from config import JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_DAYS

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default='user')  # 'user', 'admin', 'healthcare_admin', 'agriculture_admin', 'super_admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    sessions = db.relationship('UserSession', backref='user', lazy=True, cascade='all, delete-orphan')

    def __init__(self, username, email, full_name, password):
        self.username = username
        self.email = email
        self.full_name = full_name
        self.set_password(password)

    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        """Check if password matches the hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def generate_access_token(self):
        """Generate JWT access token"""
        payload = {
            'user_id': self.id,
            'username': self.username,
            'exp': datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')

    def generate_refresh_token(self):
        """Generate JWT refresh token"""
        payload = {
            'user_id': self.id,
            'username': self.username,
            'exp': datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')

    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'fullName': self.full_name,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'isActive': self.is_active
        }

class UserSession(db.Model):
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(500), unique=True, nullable=False)
    refresh_token = db.Column(db.String(500), unique=True, nullable=False)
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def __init__(self, user_id, session_token, refresh_token, ip_address=None, user_agent=None):
        self.user_id = user_id
        self.session_token = session_token
        self.refresh_token = refresh_token
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.expires_at = datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    def is_expired(self):
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at

    def extend_session(self):
        """Extend session expiration"""
        self.expires_at = datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    def to_dict(self):
        """Convert session object to dictionary"""
        return {
            'id': self.id,
            'userId': self.user_id,
            'ipAddress': self.ip_address,
            'userAgent': self.user_agent,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'expiresAt': self.expires_at.isoformat() if self.expires_at else None,
            'isActive': self.is_active
        }

# Utility functions for token validation
def decode_token(token):
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_user_by_token(token):
    """Get user by access token"""
    payload = decode_token(token)
    if not payload or payload.get('type') != 'access':
        return None

    user_id = payload.get('user_id')
    if not user_id:
        return None

    return User.query.get(user_id)

def get_session_by_refresh_token(refresh_token):
    """Get session by refresh token"""
    payload = decode_token(refresh_token)
    if not payload or payload.get('type') != 'refresh':
        return None

    return UserSession.query.filter_by(
        refresh_token=refresh_token,
        is_active=True
    ).first()

class Hospital(db.Model):
    __tablename__ = 'hospital'

    hospital_id = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'government' or 'private'
    
    # Additional fields for comprehensive hospital registration
    address = db.Column(db.Text, nullable=True)
    pincode = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    emergency_contact = db.Column(db.String(20), nullable=True)
    
    # Capacity information
    total_beds = db.Column(db.Integer, nullable=True)
    icu_beds = db.Column(db.Integer, nullable=True)
    emergency_beds = db.Column(db.Integer, nullable=True)
    
    # Medical specialties (stored as JSON)
    specialties = db.Column(db.Text, nullable=True)  # JSON array of specialties
    facilities = db.Column(db.Text, nullable=True)   # JSON array of facilities
    
    # Director information
    director_name = db.Column(db.String(200), nullable=True)
    director_phone = db.Column(db.String(20), nullable=True)
    director_email = db.Column(db.String(120), nullable=True)
    
    # Additional information
    established_year = db.Column(db.Integer, nullable=True)
    accreditation = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            'id': self.hospital_id,  # Use hospital_id as id for frontend compatibility
            'hospitalId': self.hospital_id,
            'name': self.name,
            'city': self.city,
            'state': self.state,
            'type': self.type,
            'address': self.address,
            'pincode': self.pincode,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'emergencyContact': self.emergency_contact,
            'totalBeds': self.total_beds,
            'icuBeds': self.icu_beds,
            'emergencyBeds': self.emergency_beds,
            'specialties': json.loads(self.specialties) if self.specialties else [],
            'facilities': json.loads(self.facilities) if self.facilities else [],
            'directorName': self.director_name,
            'directorPhone': self.director_phone,
            'directorEmail': self.director_email,
            'establishedYear': self.established_year,
            'accreditation': self.accreditation,
            'description': self.description,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }

class Farmer(db.Model):
    __tablename__ = 'farmers'

    farmer_name = db.Column(db.String(200), primary_key=True)  # Using farmer_name as primary key since no id column
    mobile_number = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    land_area = db.Column(db.Float, nullable=False)  # in acres/hectares
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.farmer_name,  # Use farmer_name as id for frontend compatibility
            'farmerName': self.farmer_name,
            'mobileNumber': self.mobile_number,
            'location': self.location,
            'landArea': self.land_area,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }

class Doctor(db.Model):
    __tablename__ = 'doctors'

    dr_name = db.Column(db.String(200), primary_key=True)  # Using dr_name as primary key since no id column
    hospital_id = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.dr_name,  # Use dr_name as id for frontend compatibility
            'drName': self.dr_name,
            'hospitalId': self.hospital_id,
            'gender': self.gender,
            'time': self.time,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }

class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(200), nullable=False)
    patient_email = db.Column(db.String(120), nullable=False)
    patient_phone = db.Column(db.String(20), nullable=False)
    hospital_id = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    doctor_name = db.Column(db.String(200), nullable=True)  # Optional doctor preference
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    symptoms = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, confirmed, completed, cancelled
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Admin who created it, null for user-created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    creator = db.relationship('User', backref='created_appointments')

    def to_dict(self):
        return {
            'id': self.id,
            'patientName': self.patient_name,
            'patientEmail': self.patient_email,
            'patientPhone': self.patient_phone,
            'hospitalId': self.hospital_id,
            'department': self.department,
            'doctorName': self.doctor_name,
            'appointmentDate': self.appointment_date.isoformat() if self.appointment_date else None,
            'appointmentTime': self.appointment_time.isoformat() if self.appointment_time else None,
            'symptoms': self.symptoms,
            'status': self.status,
            'createdBy': self.created_by,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }

class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # 'Healthcare', 'Agriculture', 'System', etc.
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationship
    creator = db.relationship('User', backref='alerts')

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'message': self.message,
            'severity': self.severity,
            'createdBy': self.created_by,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'isActive': self.is_active
        }

class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='Settings')  # Lucide icon name
    route = db.Column(db.String(100), nullable=False, unique=True)  # URL route for the service
    component_name = db.Column(db.String(100), nullable=False)  # React component name
    is_active = db.Column(db.Boolean, default=True)
    is_builtin = db.Column(db.Boolean, default=False)  # Built-in services cannot be deleted
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    creator = db.relationship('User', backref='services')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'displayName': self.display_name,
            'description': self.description,
            'icon': self.icon,
            'route': self.route,
            'componentName': self.component_name,
            'isActive': self.is_active,
            'isBuiltin': self.is_builtin,
            'createdBy': self.created_by,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }

class Page(db.Model):
    __tablename__ = 'pages'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    route = db.Column(db.String(200), unique=True, nullable=False)
    icon = db.Column(db.String(50), default='FileText')
    is_active = db.Column(db.Boolean, default=True)
    is_builtin = db.Column(db.Boolean, default=False)  # Built-in pages cannot be deleted
    is_main_tab = db.Column(db.Boolean, default=False)  # Whether this appears as a main navigation tab
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with user
    creator = db.relationship('User', backref='created_pages')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'route': self.route,
            'icon': self.icon,
            'isActive': self.is_active,
            'isBuiltin': self.is_builtin,
            'isMainTab': self.is_main_tab,
            'createdBy': self.created_by,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }