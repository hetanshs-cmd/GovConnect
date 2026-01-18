# GovConnect - Government Infrastructure Dashboard

> A comprehensive government infrastructure dashboard built with React and TypeScript, featuring real-time monitoring, user authentication, and multi-sector analytics.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [AI Assistant Features](#ai-assistant-features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Environment Variables](#environment-variables)
- [Running Locally](#running-locally)
- [Test Credentials](#test-credentials)
- [Error Handling](#error-handling)
- [Security & Secrets](#security--secrets)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)
- [Collaborators](#collaborators)

---

## Project Overview

GovConnect is a comprehensive government infrastructure monitoring and management platform that provides real-time insights across multiple sectors including healthcare, agriculture, and urban infrastructure. The platform features role-based access control, secure authentication, an intuitive dashboard for government officials to monitor and manage critical infrastructure services, and an AI-powered assistant for enhanced decision-making and system queries.

---

## Features

- 🔐 **User Authentication**: Secure login/registration with JWT tokens and role-based access control
- 📧 **Email Notifications**: Automated email notifications for user registration, appointment scheduling, and status updates
- 🎨 **Theme Support**: Light/dark mode toggle for better user experience
- 📊 **Real-time Dashboard**: Infrastructure monitoring across multiple sectors with live metrics
- 🏥 **Healthcare Sector**: Hospital management, appointment booking, and health metrics monitoring
- 🌾 **Agriculture Sector**: Farmer registration, crop monitoring, and yield analytics
- 🏙️ **Urban Infrastructure**: Traffic monitoring and utility service management
- 🚨 **Alert System**: Real-time notifications and critical status updates for administrators with live top-nav alerts
- 🤖 **AI Assistant**: GPT-5 mini powered chat assistant for system queries and support (authenticated users only)
- 📱 **Responsive Design**: Fully responsive interface that works on desktop and mobile devices
- ⚡ **Performance**: Optimized with background workers and Redis-based caching
- 🔒 **Role-based Permissions**: Super admin controls for system configuration and section management

---

## AI Assistant Features

GovConnect includes a powerful AI assistant powered by GPT-5 mini for enhanced user experience:

### 🤖 AI Chat Assistant
- **Smart Query Handling**: Ask questions about system status, infrastructure metrics, and operational data
- **Contextual Responses**: AI understands government infrastructure context and provides relevant insights
- **Authentication Required**: Chat functionality is available only to authenticated users
- **Real-time Responses**: Instant answers to system queries and support requests
- **Multi-sector Knowledge**: Trained to understand healthcare, agriculture, and infrastructure domains

### 🔧 System Health AI
- **Automated Monitoring**: AI-powered analysis of system metrics and performance indicators
- **Predictive Alerts**: Intelligent detection of potential issues before they become critical
- **Health Scoring**: Automated calculation of system health scores based on multiple metrics
- **Performance Analytics**: AI-driven insights into system performance and optimization opportunities

---

## 📧 Email Integration Features

GovConnect includes comprehensive email notification system for enhanced user communication:

### 🎯 Automated Email Triggers
- **User Registration**: Welcome emails sent to new users with platform overview and getting started guide
- **Appointment Scheduling**: Confirmation emails sent when appointments are booked with full details
- **Appointment Status Updates**: Automatic emails for confirmed, cancelled, and completed appointments
- **Professional Templates**: HTML/CSS email templates with GovConnect branding and responsive design

### 📨 Email Configuration
- **Gmail SMTP Integration**: Secure email delivery through Gmail SMTP servers
- **TLS Encryption**: Encrypted email transmission for security
- **Error Handling**: Email failures don't break core functionality
- **Template System**: Professional HTML templates with plain text fallbacks

### 🔧 Technical Implementation
- **Flask-Mail Extension**: Robust email sending with Flask integration
- **Template Engine**: Dynamic email content generation
- **Queue System**: Asynchronous email processing to prevent delays
- **Logging**: Comprehensive email delivery tracking and error logging

---

### Frontend
- **React 19** with TypeScript for type-safe development
- **React Router DOM** for client-side routing
- **Tailwind CSS** for responsive styling and theming
- **Lucide React** for consistent iconography
- **Recharts** for data visualization
- **Vite** for fast development and optimized builds

### Backend
- **Flask** (Python web framework) with RESTful API design
- **JWT Authentication** for secure token-based authentication
- **Redis** for rate limiting, caching, and session management
- **MySQL** database with SQLAlchemy ORM
- **Flask-Mail** for email notifications and communications
- **bcrypt** for secure password hashing
- **Background Workers** for task scheduling and processing
- **Rate Limiting** with Redis-based protection against abuse

---

## Prerequisites

- **Node.js** (v16 or higher)
- **Python 3** (v3.8 or higher)
- **pip** (Python package manager)
- **MySQL Server** (for database)
- **Redis** (for caching and rate limiting)

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd GovConnect
```

### 2. Setup Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Setup Frontend Dependencies
```bash
cd ..
npm install
```

### 4. Setup Database
```bash
# Ensure MySQL is running and create the database
mysql -u root -p
CREATE DATABASE govconnect;
# Run the setup script (located in both root and backend directories)
mysql -u root -p govconnect < setup_mysql.sql
```

---

## Environment Variables

### Backend (.env in `/backend`)
```env
# Flask Configuration
SECRET_KEY=your-secret-key-change-in-production
DEBUG=False
SESSION_TYPE=filesystem
HOST=0.0.0.0
PORT=5001

# Database Configuration
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_DB=govconnect
MYSQL_PORT=3306

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Rate Limiting
RATE_LIMIT=100
RATE_WINDOW=60

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# AI/LLM Configuration
LLM_PROVIDER=openai
LLM_DEFAULT_MODEL=gpt-5-mini
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=your-openai-api-key

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Logging
LOG_LEVEL=INFO
```

### Frontend (.env in root)
```env
VITE_API_URL=http://localhost:5000
VITE_APP_NAME=GovConnect
```

---

## Running Locally

### Start Backend Server (Terminal 1)
```bash
cd backend
python app.py
```
Backend will start on `http://localhost:5000`

### Start Frontend Development Server (Terminal 2)
```bash
npm run dev
```
Frontend will start on `http://localhost:3000`

### Optional: Start Redis (if not running)
```bash
redis-server
```

---

## Test Credentials

Use these demo credentials to test different user roles (automatically created on backend startup):

### Super Administrator (Full System Access)
- **Username**: `superadmin`
- **Password**: `super123`
- **Role**: Complete access to all features and user management

### System Administrators
- **Username**: `admin`
- **Password**: `admin123`
- **Role**: User management and system administration
- **Username**: `admin2`
- **Password**: `admin123`
- **Role**: User management and system administration

### Healthcare Administrators
- **Username**: `healthadmin`
- **Password**: `health123`
- **Role**: Hospital and healthcare management
- **Username**: `healthadmin2`
- **Password**: `health123`
- **Role**: Hospital and healthcare management

### Agriculture Administrators
- **Username**: `agriadmin`
- **Password**: `agri123`
- **Role**: Farmer registration and agriculture data management
- **Username**: `agriadmin2`
- **Password**: `agri123`
- **Role**: Farmer registration and agriculture data management

### Regular Users
- **Username**: `user`
- **Password**: `user123`
- **Role**: Basic access to view services and make appointments

*Note: You can also register new accounts through the application's registration page.*

---

## Error Handling

The application implements comprehensive error handling across all layers:

### Frontend Error Handling
- **Network Errors**: Automatic retry logic with exponential backoff
- **Authentication Errors**: Auto-redirect to login with user notification
- **Validation Errors**: Real-time form validation with helpful error messages
- **Loading States**: Skeleton loaders and progress indicators

### Backend Error Handling
- **Authentication Errors**: 401 Unauthorized with descriptive messages
- **Validation Errors**: 400 Bad Request with field-specific error details
- **Rate Limiting**: 429 Too Many Requests (Redis-based protection)
- **Server Errors**: 500 Internal Server Error with proper logging
- **Database Errors**: Graceful handling with user-friendly messages

### Security Error Handling
- **Token Expiration**: Automatic token refresh or redirect to login
- **Invalid Tokens**: Secure logout and session cleanup
- **CORS Issues**: Proper cross-origin request handling

---

## Security & Secrets

✅ **CONFIRMED: No secrets committed to repository**

### Security Measures Implemented:
- **Environment Variables**: All sensitive data stored in `.env` files (excluded from version control)
- **JWT Tokens**: Secure token-based authentication with HTTP-only cookies
- **Password Security**: bcrypt hashing for all passwords (never stored in plain text)
- **Rate Limiting**: Redis-based protection against brute force attacks
- **CORS Protection**: Configured allowed origins for cross-origin requests
- **Input Validation**: Server-side validation for all user inputs
- **SQL Injection Protection**: Parameterized queries with SQLAlchemy ORM

### Production Security Recommendations:
- Use AWS Secrets Manager or HashiCorp Vault for secret management
- Enable HTTPS/TLS encryption
- Implement proper logging and monitoring
- Regular security audits and dependency updates

---

## Project Structure

```
GovConnect/
├── backend/
│   ├── app.py                 # Main Flask application with AI chat integration
│   ├── config.py             # Configuration settings including LLM and email defaults
│   ├── models.py             # Database models (SQLAlchemy)
│   ├── database.py           # Database connection utilities
│   ├── chatbox.py            # AI chatbot with GPT-5 mini integration
│   ├── email_utils.py        # Email notification utilities and templates
│   ├── system_health_ai.py   # AI-powered system health monitoring
│   ├── requirements.txt      # Python dependencies
│   ├── setup_mysql.sql       # Database schema setup
│   ├── rate_limit.py         # Rate limiting utilities
│   ├── redis_client.py       # Redis connection utilities
│   ├── scheduler.py          # Background task scheduler
│   ├── worker.py             # Background worker processes
│   └── README.md            # Backend documentation
├── components/               # React components
│   ├── Login.tsx            # Authentication component
│   ├── Dashboard.tsx        # Main dashboard with super-admin section management
│   ├── HealthcareSector.tsx # Healthcare management
│   ├── AgricultureSector.tsx # Agriculture management
│   ├── AppointmentForm.tsx  # Appointment booking
│   ├── AlertFeed.tsx        # System alerts display
│   ├── ChatBox.tsx          # AI assistant chat interface
│   ├── TopNav.tsx           # Navigation with live alerts
│   ├── Sidebar.tsx          # Navigation sidebar
│   ├── UserManagement.tsx   # User administration
│   └── ...
├── pages/                   # Page components
│   ├── HomePage.tsx
│   ├── HealthcarePage.tsx
│   ├── AgriculturePage.tsx
│   ├── AdminPage.tsx
│   ├── AlertsPage.tsx
│   └── ...
├── App.tsx                  # Main application component
├── index.tsx               # Application entry point
├── package.json            # Frontend dependencies
├── vite.config.ts          # Vite configuration
├── tsconfig.json           # TypeScript configuration
├── setup_mysql.sql         # Database setup script
└── README.md              # This file
```

---

## API Endpoints

### Authentication Endpoints
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/verify` - Token verification
- `POST /api/auth/refresh` - Token refresh
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user info

### Healthcare Endpoints
- `GET /api/healthcare/hospitals` - List all hospitals
- `POST /api/healthcare/hospitals` - Register new hospital
- `PUT /api/healthcare/hospitals/{id}` - Update hospital
- `DELETE /api/healthcare/hospitals/{id}` - Delete hospital

### Appointment Endpoints
- `GET /api/appointments` - List all appointments (admin only)
- `POST /api/appointments` - Create new appointment
- `PUT /api/appointments/{id}` - Update appointment status
- `GET /api/appointments/my` - Get user's appointments

### Agriculture Endpoints
- `GET /api/agriculture/farmers` - List all farmers
- `POST /api/agriculture/farmers` - Register new farmer
- `PUT /api/agriculture/farmers/{id}` - Update farmer
- `DELETE /api/agriculture/farmers/{id}` - Delete farmer

### System Endpoints
- `GET /api/dashboard/metrics` - Dashboard metrics
- `GET /api/alerts` - System alerts
- `POST /api/alerts` - Create alert (admin only)
- `DELETE /api/alerts/{id}` - Delete alert (admin only)
- `POST /api/chat` - AI assistant chat (authenticated users only)
- `GET /api/admin/users` - List all users (admin only)
- `POST /api/admin/users` - Create new user (admin only)
- `PUT /api/admin/users/{id}` - Update user (admin only)
- `DELETE /api/admin/users/{id}` - Delete user (admin only)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Module not found` | Run `npm install` (frontend) or `pip install -r requirements.txt` (backend) |
| `Port already in use` | Change `PORT` in backend config or Vite config |
| `CORS errors` | Verify `CORS_ORIGINS` in backend `.env` matches frontend URL |
| `Database connection failed` | Check MySQL credentials and ensure database exists |
| `Redis connection failed` | Ensure Redis server is running on localhost:6379 |
| `JWT token invalid` | Clear browser cookies and re-login |
| `Build fails` | Clear node_modules (`rm -rf node_modules && npm install`) |
| `bcrypt import error` | Install additional packages: `pip install bcrypt` (Linux) or `pip install bcrypt[py36]` |
| `MySQL connection error` | Ensure MySQL service is running: `sudo systemctl start mysql` |
| `Permission denied` | Check file permissions and run with appropriate user privileges |
| `AI chat not working` | Check `LLM_API_KEY` in backend `.env` and ensure OpenAI API access |
| `Email notifications not sending` | Check `MAIL_USERNAME` and `MAIL_PASSWORD` in backend `.env`, verify Gmail app password |
| `Section creation restricted` | Only super_admin users can add new dashboard sections |
| `Live alerts not showing` | Check browser network tab for `/api/alerts` endpoint connectivity |

---

## Collaborators

- [Hetansh Sutaria](https://github.com/hetanshs-cmd) (Team Leader)
- [Kunal Pundhir](https://github.com/augustbeyondinfinity)
- [Krish Pundhir](https://github.com/Charlie199KO)
- [Kush Kelaiya](https://github.com/Kush-Kelaiya22)
- [Tanish Shah](https://github.com/tanishshahhh)

---

## License

This project is licensed under the MIT License.
