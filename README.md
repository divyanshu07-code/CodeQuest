# CodeQuest

A Flask-based web application designed to help students organize, track, and manage their coding practice in one place.

## Overview

As I started solving coding problems regularly, I realized it was difficult to keep track of what I had solved, what I needed to revisit, and how my progress was improving over time.

CodeQuest was built to solve that problem. It provides a simple and organized platform where users can manage their coding journey, maintain records of solved problems, and stay consistent with practice.

## Features

* User Registration and Login
* Secure Password Authentication
* Add Coding Problems
* Edit Existing Entries
* Delete Problems
* Track Problem-Solving Progress
* Session Management
* SQLite Database Integration
* Clean and Responsive User Interface

## Tech Stack

### Backend

* Python
* Flask
* SQLite

### Frontend

* HTML
* CSS
* JavaScript

### Deployment

* Render
* Gunicorn

## Project Structure

```text
CodeQuest/
├── static/             # CSS, JavaScript and assets
├── templates/          # HTML templates
├── .env.example        # Environment variables template
├── .gitignore          # Ignored files and folders
├── app.py              # Main Flask application
├── codequest.db        # SQLite database
├── config.py           # Configuration settings
├── database.py         # Database operations
├── requirements.txt    # Project dependencies
└── routes.py           # Application routes
```

## Installation

### Clone the Repository

```bash
git clone https://github.com/divyanshu07-code/codequest.git
cd codequest
```

### Create a Virtual Environment

```bash
python -m venv venv
```

### Activate the Virtual Environment

Windows:

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file and add:

```env
SECRET_KEY=your_secret_key
DATABASE_PATH=codequest.db
```

### Run the Application

```bash
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

## Live Demo

https://codequest-me7n.onrender.com/login

## What I Learned

Building CodeQuest helped me gain hands-on experience with:

* Flask application development
* User authentication and session handling
* Database management using SQLite
* Project structuring and organization
* Environment variable management
* Git and GitHub workflow
* Deploying Python web applications on Render

## Future Improvements

* Coding Streak Tracking
* Progress Analytics Dashboard
* Difficulty-wise Statistics
* Contest Tracking
* Dark Mode
* PostgreSQL Integration
* Public User Profiles
* Search and Filter Functionality

## Support

If you found this project useful or interesting, consider giving it a ⭐ on GitHub.

Your support motivates me to continue building and improving projects.

## Feedback

Suggestions, improvements, and feedback are always welcome. Feel free to open an issue or share your ideas.

## Author
**Divyanshu**

Web Development Enthusiast | Problem Solver

Thank you for visiting the repository.
