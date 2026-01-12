# Security Upgrade Summary

This document summarizes the significant security enhancements implemented in the CareerPilot application. The system has been upgraded from a fully public application to a secure, multi-user platform with Role-Based Access Control (RBAC).

## 1. Authentication System: JWT

- **Mechanism:** Implemented a robust authentication system based on **JSON Web Tokens (JWT)**.
- **Workflow:**
  - Users must now **register** and **log in** through dedicated API endpoints (`/auth/register` and `/auth/token`).
  - Upon successful login, the API generates a signed JWT access token.
  - This token is stored in the user's session in the Streamlit UI and must be included as a **Bearer Token** in the header of all subsequent API requests.

## 2. Authorization System: RBAC

- **Mechanism:** A Role-Based Access Control (RBAC) system has been integrated to manage user permissions.
- **Roles:**
  - Users are assigned roles upon registration (e.g., `user`, `admin`).
  - These roles are encoded into the JWT payload, allowing the API to perform stateless authorization checks.
  - **Endpoint Protection:**
    - All data-related endpoints are now **protected** and require a valid JWT.
    - Specific endpoints, such as `/rag/ingest`, are restricted to users with the `admin` role, preventing unauthorized data manipulation.

## 3. Secure Credential Storage

- **Database:** A new `users` collection has been added to MongoDB to store user information.
- **Password Hashing:**
  - User passwords are never stored in plaintext. They are securely hashed using **Argon2**, the current industry-recommended algorithm for password security.
  - The system was upgraded from `bcrypt` to `Argon2` to enhance security and resolve a library-specific issue. `passlib` is used to manage the hashing process.

## 4. Frontend Integration

- **Login/Registration UI:** The Streamlit application now features a dedicated login and registration page.
- **State Management:** The UI now manages the user's authentication state, storing the JWT in the session and providing login/logout functionality.
- **Protected Access:** The main analysis features of the application are now inaccessible until a user has successfully logged in.

## 5. New Dependencies

The following libraries were added to support this security architecture:

- `passlib[bcrypt]`: For password hashing and verification.
- `python-jose[cryptography]`: For creating and verifying JWTs.
- `argon2-cffi`: Provides the Argon2 hashing algorithm.
- `python-multipart`: Required by FastAPI to handle form data from the login endpoint.

## 6. Configuration

- A `JWT_SECRET_KEY` environment variable is now required to sign the JWTs, ensuring their integrity.
