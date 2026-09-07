# Sprintalis API

Sprintalis is an AI-powered project management application designed to help users organize projects, manage tasks, and build more efficient workflows.

This repository contains the backend API for Sprintalis.

The backend is currently focused on building a strong foundation for authentication, security, database architecture, and future AI-powered project management features.

---

## Project Vision

Sprintalis aims to combine traditional project management with AI-powered capabilities.

The goal is to build a platform that can help users:

- Manage projects
- Organize tasks
- Track workflows
- Improve productivity
- Use AI-powered features to assist with project management

The project is currently under active development.

---

# Tech Stack

The backend is built using:

- **Python**
- **FastAPI**
- **PostgreSQL**
- **SQLAlchemy Async**
- **Alembic**
- **Pydantic**
- **Argon2**
- **JWT Authentication**
- **Google Authentication**
- **UV**

---

# Authentication

Sprintalis currently supports multiple authentication methods.

## Email and Password Authentication

The authentication system includes:

- Email registration
- Email OTP verification
- OTP expiration handling
- OTP attempt limits
- Registration tickets
- Secure password hashing using Argon2
- Password strength validation
- Email and password login
- Failed login attempt tracking
- Temporary account locking
- JWT access tokens
- Refresh tokens
- Refresh token revocation

---

## Google Authentication

Google authentication includes:

- Google Sign-In
- Google ID token verification
- New user creation
- Existing Google user login
- Invalid Google token handling
- Duplicate user prevention
- Separate authentication identities for providers

After Google authentication is verified, Sprintalis issues its own authentication tokens.

```text
Google ID Token
        ↓
Verify Google Identity
        ↓
Find / Create Sprintalis User
        ↓
Issue Sprintalis Access Token
        +
Issue Sprintalis Refresh Token
```

Sprintalis does not use Google's token as the application's access token.

Google authentication is used to verify the user's identity, after which Sprintalis manages its own authentication system.

---

# Authentication Architecture

Sprintalis separates the core user account from authentication providers.

```text
User
 │
 ├── Password Identity
 │
 ├── Google Identity
 │
 └── Future Authentication Providers
```

This architecture allows the application to support multiple authentication providers without tightly coupling authentication logic to the core user model.

---

# Authentication Flow

## Registration

```text
User
 │
 ▼
Enter Email
 │
 ▼
Request OTP
 │
 ▼
Email Verification
 │
 ▼
Verify OTP
 │
 ▼
Registration Ticket
 │
 ▼
Create User
 │
 ├───────────────┐
 ▼               ▼
User        Password Identity
 │
 ▼
Issue Access Token
+
Refresh Token
```

---

## Password Login

```text
Email + Password
        │
        ▼
Find User
        │
        ▼
Check Account Lock
        │
        ▼
Find Password Identity
        │
        ▼
Verify Password
        │
        ├── Incorrect Password
        │
        │      ▼
        │  Increase Failed Attempts
        │
        │      ▼
        │  Lock Account if Threshold Reached
        │
        └── Correct Password
               │
               ▼
        Reset Failed Attempts
               │
               ▼
        Issue Access + Refresh Tokens
```

---

## Google Login

```text
Client
  │
  ▼
Google Sign-In
  │
  ▼
Google ID Token
  │
  ▼
Sprintalis API
  │
  ▼
Verify Google Token
  │
  ▼
Find Google Identity using Google `sub`
  │
  ├── Existing Identity
  │        │
  │        ▼
  │   Find Existing User
  │        │
  │        ▼
  │   Issue Sprintalis Tokens
  │
  └── New Google Identity
           │
           ▼
      Check Existing Email
           │
           ├── Existing Password Account
           │        │
           │        ▼
           │    Reject Login
           │    Require Password Login
           │
           └── No Existing Account
                    │
                    ▼
                Create User
                    │
                    ▼
              Create Google Identity
                    │
                    ▼
              Issue Sprintalis Tokens
```

---

# Token System

Sprintalis uses two types of tokens.

## Access Token

The access token is a JWT used to authenticate requests to protected API endpoints.

Example flow:

```text
Client
  │
  ▼
Access JWT
  │
  ▼
Protected API Endpoint
  │
  ▼
Validate JWT
  │
  ▼
Authenticated User
```

---

## Refresh Token

Refresh tokens allow clients to obtain new access tokens without requiring the user to log in again.

```text
Refresh Token
      │
      ▼
Find Token Session
      │
      ├── Invalid
      ├── Revoked
      └── Expired
             │
             ▼
        Authentication Failed
             
      Valid
        │
        ▼
Issue New Access Token
```

---

# Project Structure

```text
src/
└── sprintalis_api/
    │
    ├── api/
    │   └── v1/
    │
    ├── authentication/
    │
    ├── database/
    │
    └── main.py
```

The project follows a modular architecture to keep API routing, authentication logic, database logic, and application configuration separated.

---

# Getting Started

## Prerequisites

Make sure you have installed:

- Python
- PostgreSQL
- UV

---

## Clone the Repository

```bash
git clone <repository-url>
cd sprintalis-api
```

---

## Install Dependencies

```bash
uv sync
```

---

## Configure Environment Variables

Create a `.env` file and configure the environment variables required by the application.

Sensitive configuration may include:

- Database credentials
- JWT secret keys
- Google OAuth credentials
- API keys

> ⚠️ Never commit `.env` files, passwords, API keys, OAuth secrets, or JWT secrets to version control.

---

## Run Database Migrations

```bash
uv run alembic upgrade head
```

---

## Run the Development Server

```bash
uv run fastapi dev src/sprintalis_api/main.py
```

The API will be available at:

```text
http://127.0.0.1:8000
```

---

## API Documentation

FastAPI automatically provides interactive API documentation.

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

---

# Testing

The API is currently being tested manually using Bruno.

Authentication flows tested include:

- User registration
- Existing email registration protection
- OTP generation
- OTP verification
- Invalid OTP handling
- OTP expiration
- Password login
- Incorrect password handling
- Failed login attempt tracking
- Temporary account locking
- JWT authentication
- Refresh token handling
- Google authentication
- Invalid Google token handling
- New Google user creation
- Existing Google user login
- Duplicate user prevention

---

# Security

Sprintalis currently implements several security-focused mechanisms.

### Password Security

- Argon2 password hashing
- Password strength validation

### Authentication Security

- JWT access tokens
- Refresh tokens
- Refresh token revocation
- Failed login tracking
- Temporary account locking

### Registration Security

- Email OTP verification
- OTP expiration
- OTP attempt limits
- Registration tickets

### Google Authentication Security

- Google ID token verification
- Google user identification using the Google `sub` identifier
- Invalid token rejection

---

# Project Status

Sprintalis is currently under active development.

## Current Progress

### Foundation

- [x] Project setup
- [x] PostgreSQL database setup
- [x] SQLAlchemy Async setup
- [x] Alembic database migrations

### Authentication

- [x] Email registration
- [x] Email OTP verification
- [x] Registration tickets
- [x] Password authentication
- [x] Argon2 password hashing
- [x] Failed login tracking
- [x] Temporary account locking
- [x] JWT access tokens
- [x] Refresh tokens
- [x] Google authentication
- [x] Resend OTP
- [x] Password Reset
- [ ] Rate Limiting (Active)

### Upcoming Features

- [ ] Project management
- [ ] Task management
- [ ] Workspace management
- [ ] Team collaboration
- [ ] AI-powered project assistance
- [ ] AI-powered task management
- [ ] Additional project analytics

---

# Development Goals

The main goals of Sprintalis include:

- Building a clean backend architecture
- Learning production-oriented backend development
- Implementing secure authentication
- Designing scalable database relationships
- Supporting multiple authentication providers
- Integrating AI capabilities into project management workflows

---

# Author

**Arun Sabu**

---

## Note

Sprintalis is a personal learning and portfolio project currently under active development.

The project focuses on backend architecture, authentication, security, database design, and future AI-powered project management capabilities.