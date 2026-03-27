# AI Video Editor SaaS

A comprehensive full-stack SaaS platform for AI-powered video editing. Users can upload raw videos, which are automatically processed into short-form content optimized for platforms like TikTok, Instagram Reels, and YouTube Shorts.

## 🗂️ Project Structure

The repository is divided into several main components:

*   **[`/backend`](./backend)**: The core REST API built with FastAPI. Handles authentication, job queuing, file management, and real-time progress streaming via Redis SSE.
*   **[`/frontend`](./frontend)**: The user interface (web application) for users to manage their videos, track processing status, and download outputs.
*   **[`/workers`](./workers)**: Asynchronous Celery workers that execute the heavy video processing tasks off the main thread.
*   **[`/ai-engine`](./ai-engine)**: The core intelligence and ML models responsible for analyzing and editing the video content.
*   **[`/docker`](./docker)**: Docker configuration and compose files for containerized deployment.

---

## 🎨 Frontend Architecture & Setup

The frontend is a modern web application designed for a smooth, reactive user experience.

### Key Technologies
*   **Framework:** Next.js 16 (React 19) with TypeScript
*   **Styling & UI:** Tailwind CSS v4, shadcn/ui, base-ui, Lucide Icons
*   **State Management:** Zustand (global state), TanStack React Query v5 (server state & caching)

### Running the Frontend Locally
1. **Install Dependencies:**
   ```bash
   cd frontend
   npm install
   ```
2. **Start the Development Server:**
   ```bash
   npm run dev
   ```
   The application will be available at `http://localhost:3000`.

---

## ⚙️ Backend Architecture & Setup

The backend is built for high performance, security, and scalability.

### Key Technologies
*   **Framework:** FastAPI (Python)
*   **Database:** PostgreSQL (Primary data storage)
*   **Broker/Cache:** Redis (Session management, Rate Limiting, Pub/Sub for SSE)

### Running the Backend Locally
1. **Environment Setup:** Create a `.env` file in the `backend/` directory based on `.env.example`.
2. **Install Dependencies:**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Start the API Server:**
   ```bash
   uvicorn app.main:app --reload
   ```
   *Interactive API docs available at `http://localhost:8000/docs`.*

---

## 👷 Workers Architecture (Celery)

Video processing is resource-intensive and is offloaded to asynchronous background workers to keep the API highly responsive.

### Key Technologies & Features
*   **Queueing:** Celery with Redis as the broker and result backend.
*   **Resource Management:** Implements FFmpeg concurrency limits to prevent CPU/RAM exhaustion, and worker recycling to prevent memory leaks.
*   **Crash Safety:** Uses `task_acks_late` to ensure tasks are re-queued if a worker crashes mid-processing.

### Main Tasks
*   `process_video`: The core task that receives an uploaded video and runs it through the AI editing pipeline via FFmpeg.
*   `recover_stale_jobs`: Scheduled maintenance task (every 10m) to clean up jobs that crashed silently.
*   `cleanup_orphan_files`: Scheduled maintenance task (every 1h) to remove temporary processing files.

### Running the Workers Locally
Make sure Redis is running, then from the **root directory** (or with `backend` in `PYTHONPATH`):
```bash
celery -A workers.celery_app worker --loglevel=info
```
*(To run scheduled maintenance tasks, you also need to start the Celery beat scheduler: `celery -A workers.celery_app beat --loglevel=info`)*

---

## 📚 Backend API Reference

Base URL: `/api`

### 1. Authentication (`/auth`)
Session-based authentication using `HTTPOnly` cookies, CSRF protection, and email verification.

| Method | Endpoint | Description | Auth Required | Rate Limit |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new user | No | 3/min |
| `POST` | `/auth/login` | Login with credentials | No | 5/min |
| `POST` | `/auth/logout` | Logout and destroy session | Yes | - |
| `GET` | `/auth/me` | Get current authenticated user | Yes | - |
| `POST` | `/auth/change-password` | Change user password | Yes | 5/min |
| `POST` | `/auth/verify-email` | Verify email with token | No | 10/min |
| `POST` | `/auth/forgot-password` | Request password reset | No | 5/min |
| `POST` | `/auth/reset-password` | Reset password with token | No | 5/min |

### 2. Jobs (`/jobs`)
Manage asynchronous video processing workflows.

| Method | Endpoint | Description | Auth Required | Rate Limit |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/jobs/start` | Start a new video processing job | Yes | 20/min, 100/hr |
| `GET` | `/jobs/{job_id}` | Get status of a specific job | Yes | 60/min |
| `POST` | `/jobs/{job_id}/cancel` | Cancel a processing job | Yes | 20/min |

### 3. Real-time Progress (`/jobs`)
Stream job updates directly to the client via Server-Sent Events (SSE).

| Method | Endpoint | Description | Auth Required | Rate Limit |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/jobs/{job_id}/progress` | Stream job progress via SSE | Yes | 30/min |

*Events Emitted:* `connected`, `progress` (containing status, %, and step name), `heartbeat`.

### 4. Outputs (`/outputs`)
Retrieve and securely download processed videos.

| Method | Endpoint | Description | Auth Required | Rate Limit |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/outputs` | List all processed outputs for a video | Yes | - |
| `GET` | `/outputs/{output_id}` | Retrieve details of a specific output | Yes | - |
| `GET` | `/outputs/{output_id}/download-url`| Generate a signed, time-limited (1h) download URL | Yes | 30/min |
| `GET` | `/outputs/download/{token}` | Download via signed token (Direct link) | Token | - |
