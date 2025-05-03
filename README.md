# F1 Driver Database Management System

A modern Formula 1 driver database management system built with FastAPI and Firebase, featuring real-time driver statistics and team management.

## Technologies Used

### Backend
- **FastAPI**: Modern, fast web framework for building APIs with Python
- **Python**: Primary programming language
- **Firebase**: 
  - **Firebase Authentication**: User authentication and management
  - **Firestore**: NoSQL database for storing driver data, teams, and race statistics
  - **Google Cloud Platform**: Hosting and infrastructure

### Authentication
- **Google Firebase Authentication**: Secure user authentication system
- **JWT (JSON Web Tokens)**: Token-based authentication
- **OAuth 2.0**: Secure authorization framework

### Database
- **Firestore**: 
  - Real-time NoSQL database
  - Document-based data structure
  - Automatic scaling and high availability

### API Features
- RESTful API endpoints
- Real-time data synchronization
- CRUD operations for:
  - Drivers
  - Teams
  - Race Results
  - Team Members

### Security
- Token-based authentication
- Role-based access control
- Secure API endpoints
- Data validation and sanitization

## Project Structure
- `main.py`: Core application logic and API endpoints
- `templates/`: HTML templates for the web interface
- `static/`: Static assets (CSS, JavaScript, images)

## Key Features
- Driver profile management
- Team information tracking
- Race result analysis
- Real-time statistics
- Role-based permissions
- Performance metrics tracking
- Historical data management
- Team member management

## Getting Started
1. Clone the repository
2. Set up Firebase project and configure credentials
3. Install dependencies
4. Run the application

## Dependencies
- fastapi==0.97.0
- google-auth==2.20.0
- google-cloud-firestore==2.11.1
- google-cloud-storage==2.10.0
- Jinja2==3.1
- python-multipart==0.0.6
- requests==2.31.0
- uvicorn==0.22.0

## Prerequisites

Before running this project, you'll need:

1. Python 3.8 or higher installed on your system
2. A Google Cloud Platform account
3. A Firebase project
4. Git installed on your system

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Rpmali/F1-databse-management.git
cd F1-databse-management
```

### 2. Firebase Setup

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select an existing one
3. Enable Authentication with Email/Password provider
4. Download your service account key:
   - Go to Project Settings > Service Accounts
   - Click "Generate New Private Key"
   - Save the downloaded JSON file as `service-account.json` in your project root

### 3. Configure Firebase
1. Open `static/firebase-config.js`
2. Replace the Firebase configuration with your own:

```javascript
const firebaseConfig = {
  apiKey: "your-api-key",
  authDomain: "your-auth-domain",
  projectId: "your-project-id",
  storageBucket: "your-storage-bucket",
  messagingSenderId: "your-messaging-sender-id",
  appId: "your-app-id"
};
```

You can find these values in your Firebase project settings under "General" > "Your apps" > "Web app".

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Application

```bash
uvicorn main:app --reload
```

The application will be available at `http://localhost:8000`

## Project Structure

- `main.py` - Core application logic and API endpoints
- `templates/` - HTML templates for the web interface
- `static/` - Static assets (CSS, JavaScript, images)
- `service-account.json` - Google Cloud service account credentials
- `requirements.txt` - Project dependencies

## Features

- Driver Profile Management (Add, Edit, View)
- Team Information Management
- Race Result Tracking
- Real-time statistics updates
- Secure data storage
- Role-based access control

## Security Notes

- Never commit your `service-account.json` file to version control
- Keep your Firebase configuration secure
- Use environment variables for sensitive information
- Implement proper input validation
- Use HTTPS in production

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 