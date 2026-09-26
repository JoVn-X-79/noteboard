# Noteboard

A minimal shared notepad deployed as a microservice application on Kubernetes.

**Stack:** nginx (frontend) · Flask + Python (backend API) · PostgreSQL (database)

---

## What It Does

Open the app in a browser, type a note, press Save. Notes are listed on the same page and can be deleted. All data persists across pod restarts.

---

## Architecture

```
Browser → frontend-service (NodePort) → nginx pod
                                           ↓ proxy_pass /api/
                                     backend-service (ClusterIP) → Flask pod
                                                                       ↓ SQL
                                                               db-service (ClusterIP) → PostgreSQL pod
                                                                                              ↓ mounts
                                                                                         db-pvc (1Gi PVC)
```

Two independently scalable microservices + one database with persistent storage.

---

## Docker Hub Images

| Service | Image |
|---|---|
| Frontend | `jovnx79/noteboard-frontend:v2` |
| Backend | `jovnx79/noteboard-backend:v2` |

---

## Deploy

**Prerequisites:** minikube running, kubectl configured.

```bash
git clone https://github.com/JoVn-X-79/noteboard.git
cd noteboard
kubectl apply -f k8s/
```

Wait ~20 seconds for all pods to reach Running state:
```bash
kubectl get pods --watch
```

---

## Access the Application

```bash
minikube service frontend-service --url
```

Keep that terminal open (it maintains the tunnel), then open the printed URL in your browser.

---

## REST API

All endpoints are proxied through the frontend at `/api/`:

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check — returns `{"status": "ok"}` |
| GET | `/api/notes` | List all notes (newest first) |
| POST | `/api/notes` | Create a note — body: `{"text": "..."}` |
| DELETE | `/api/notes/<id>` | Delete a note by id |

---

## Scale Each Microservice Independently

```bash
# Scale backend to 3 replicas
kubectl scale deployment backend --replicas=3

# Scale frontend to 3 replicas
kubectl scale deployment frontend --replicas=3

# Check pods
kubectl get pods
```

The database does not need to scale — it uses a single replica with a PersistentVolumeClaim.

---

## Verify Persistence

```bash
# Delete the database pod
kubectl delete pod -l tier=database

# Wait for it to restart (~15s), then check your notes are still there
curl http://<your-minikube-url>/api/notes
```

---

## Project Structure

```
noteboard/
├── README.md
├── docs/
│   ├── description.md      # What the app does and who it's for
│   ├── architecture.md     # Mermaid diagram + component details
│   └── discussion.md       # Trade-offs, security, scaling
├── backend/
│   ├── Dockerfile
│   └── src/
│       ├── app.py          # Flask REST API
│       └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf          # Reverse proxy config
│   └── src/
│       └── index.html      # Single-page app (vanilla JS)
└── k8s/
    ├── configmap.yaml
    ├── secret.yaml
    ├── db-pvc.yaml
    ├── db-deployment.yaml  # PostgreSQL + ClusterIP service
    ├── backend-deployment.yaml  # Flask + ClusterIP service
    └── frontend-deployment.yaml # nginx + NodePort service
```

---

## Known Limitations

- No authentication — notes are public and shared
- Backend opens a new database connection per request (no connection pooling)
- NodePort exposure is for local/minikube use only — production would use an Ingress with TLS
- PostgreSQL is a single replica — no automatic failover

See `docs/discussion.md` for a full production readiness discussion.
