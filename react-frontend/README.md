# Blockchain Malware Reporting System - React Frontend

React frontend for the Blockchain-Based Malware Reporting System.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The app will run on http://localhost:3000

## Backend

Make sure your Flask backend is running on http://localhost:5000

## Project Structure

```
react-frontend/
├── src/
│   ├── components/
│   │   ├── Login.jsx
│   │   ├── EmployeeDashboard.jsx
│   │   └── AdminDashboard.jsx
│   ├── styles/
│   │   └── style.css
│   ├── App.jsx
│   └── main.jsx
├── index.html
├── package.json
└── vite.config.js
```

## Features

- Login page with role selection (Employee/Admin)
- Employee dashboard with file upload and history
- Admin dashboard with verification and download
- Loading states for all async operations
- Error handling and user feedback
- Clean, student-friendly UI
