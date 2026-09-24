# Noteboard — Application Description

## What It Does

Noteboard is a minimal shared notepad web application. Users open a browser, type a short note, and save it. All saved notes are listed on the same page. Any note can be deleted with a single click. Notes are stored persistently in a database and survive restarts.

## Who Would Use It and Why

The target user is anyone who needs a lightweight, browser-accessible scratchpad that persists across sessions — for example, a small team sharing quick reminders or a student keeping temporary study notes. No account, login, or installation is required on the client side.

## Feature Overview

- **Add a note** — type text (up to 500 characters) and press Save or Enter
- **List notes** — all notes displayed in reverse-chronological order on the same page
- **Delete a note** — click the ✕ button next to any note to remove it instantly
- **Persistent storage** — notes survive application restarts and pod rescheduling
- **REST API** — the backend exposes a documented JSON API usable by any HTTP client

## Technology Choices

| Layer | Technology |
|---|---|
| Frontend | nginx:alpine serving a single static HTML/JS page |
| Backend API | Python 3.11 + Flask + psycopg2 |
| Database | PostgreSQL 15 (alpine) |

## Acknowledgement: Scale Realism

Noteboard is intentionally trivial. A real-world notepad with multiple users would not warrant this architecture. The application has been built this way to satisfy the assignment requirements and to demonstrate the Kubernetes deployment patterns correctly.

In a real production scenario, the following would need to change:

- **Authentication and authorisation** — notes are currently public and shared. Real users would need accounts and private note spaces.
- **Database scaling** — the single PostgreSQL instance is a bottleneck. Read replicas (streaming replication) or a managed database service (e.g. AWS RDS, Cloud SQL) would be used for read-heavy load. Writes would still go to a single primary.
- **Backend connection pooling** — the current backend opens a new database connection per request. A production deployment would use PgBouncer or SQLAlchemy's connection pool to avoid exhausting PostgreSQL's connection limit under load.
- **Frontend caching** — static assets would be served via a CDN rather than directly from nginx pods.
- **Ingress with TLS** — a proper Ingress controller with a TLS certificate (e.g. cert-manager + Let's Encrypt) would replace the NodePort service.
