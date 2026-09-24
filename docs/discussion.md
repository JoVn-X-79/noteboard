# Noteboard — Architecture Discussion

## Benefits of the Chosen Architecture

The frontend-backend-database split satisfies the core goal of demonstrating independent horizontal scaling with the minimum possible code. Each tier has a single, clear responsibility: nginx delivers the UI and proxies API calls; Flask handles business logic; PostgreSQL stores state. No tier knows implementation details of the others beyond the agreed interface (HTTP/JSON for frontend↔backend, SQL/TCP for backend↔database).

Statelessness in both the frontend and backend tiers is the key property that makes scaling safe. Because neither tier holds in-memory session state or any data that must be tied to a specific pod, Kubernetes can route requests to any available replica and the behaviour is identical. Adding or removing replicas with `kubectl scale` takes effect immediately and requires no application changes.

The nginx reverse proxy pattern eliminates cross-origin complexity. The browser always talks to a single origin; nginx transparently routes static file requests and API calls to the appropriate backend. This is a standard pattern for single-page applications and means no CORS configuration is needed on the Flask side.

Using a ConfigMap for non-sensitive configuration and a Secret for credentials follows Kubernetes best practices. Configuration is decoupled from the image, which means the same Docker image can be deployed to different environments (dev, staging, production) with different database hosts and credentials, without rebuilding.

---

## Challenges and Trade-offs

**New connection per request.** The current Flask backend opens a new `psycopg2` connection on every request. This is simple and correct for a low-traffic prototype but does not scale. Under load, PostgreSQL's default connection limit (100) would be exhausted quickly. The fix is connection pooling, either inside the application (SQLAlchemy's pool or `psycopg2.pool`) or externally via PgBouncer as a sidecar or separate service.

**Single PostgreSQL replica.** The database is a single point of failure. If the pod is deleted, there is a brief outage until Kubernetes reschedules and PostgreSQL finishes its recovery cycle (observed: ~10–15 seconds in testing). A production deployment would use a managed database service or a PostgreSQL operator (e.g. CloudNativePG) to provide high availability with automatic failover.

**NodePort vs Ingress.** The frontend is exposed via a NodePort service, which is the simplest option for minikube but is not suitable for production. NodePorts expose a raw port on each cluster node and have no TLS termination or hostname-based routing. A production deployment would use an Ingress controller (e.g. nginx-ingress or Traefik) with a TLS certificate managed by cert-manager.

**No request validation beyond basics.** The backend checks that the `text` field is non-empty but performs no other sanitisation. A production API would enforce maximum lengths at the database level, add rate limiting, and validate content types strictly.

---

## Security

### Threat Model

The following trust boundaries and threats were identified for this application:

**1. Unauthenticated API access.** The backend REST API has no authentication. Any client that can reach `backend-service` — whether a browser via nginx, another pod inside the cluster, or an attacker who has breached the cluster network — can read, create, or delete all notes. In a production system, this would require at minimum an API key or JWT-based authentication. For a multi-user application, per-user authorisation would be needed.

**2. Secrets stored in Kubernetes Secrets (base64, not encrypted).** Kubernetes Secrets are base64-encoded, not encrypted at rest by default. Anyone with `kubectl get secret` access to the namespace can decode and read the database password. This means the Kubernetes RBAC configuration of the cluster itself is a critical security control. In production, secrets should be encrypted at rest (enabled via the Kubernetes `EncryptionConfiguration` feature) or managed by an external secrets manager such as HashiCorp Vault, AWS Secrets Manager, or the Kubernetes External Secrets Operator.

**3. Credentials in environment variables.** The database credentials are injected as environment variables into the backend pods. While this is the standard Kubernetes pattern, environment variables are visible to any process running inside the container and can appear in debug output or crash dumps. The risk is mitigated here because the backend does not log environment variables. A stricter approach would be to mount secrets as files and read them once at startup.

**4. Container privilege escalation.** The Flask and nginx containers run as root by default. A process that escapes the container could gain root on the host. This is mitigated in the current implementation by using minimal base images (`python:3.11-slim`, `nginx:alpine`) that reduce the installed attack surface. A production hardening step would be to add `securityContext` to each container (`runAsNonRoot: true`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`).

**5. Inter-service trust.** All pods inside the cluster can communicate freely by default. A compromised frontend pod could directly query `db-service:5432` if it had the credentials. Kubernetes NetworkPolicies would restrict this so that only backend pods can reach the database service, and only frontend pods can reach the backend service.

**6. Unvalidated input / SQL injection.** All database queries use psycopg2's parameterised query syntax (`%s` placeholders), which prevents SQL injection. The `text` field is stored and returned as-is; the frontend applies HTML entity escaping (`escHtml()`) before rendering note text in the DOM, preventing stored XSS.

**7. Image provenance.** The custom images (`jovnx79/noteboard-backend:v1`, `jovnx79/noteboard-frontend:v1`) are pushed to a public Docker Hub repository. In production, images should be stored in a private registry, signed (e.g. with Sigstore/cosign), and scanned for known vulnerabilities (e.g. with Trivy or Grype) as part of a CI/CD pipeline before deployment.

### What Has Been Mitigated

- SQL injection: parameterised queries throughout
- Stored XSS: HTML entity escaping in the frontend
- Credential separation: database credentials in Secrets, not hardcoded in images or ConfigMaps
- Reduced attack surface: minimal base images (alpine/slim variants)
- Health probes: liveness and readiness probes on all microservice containers prevent traffic being sent to unhealthy pods

### What Could Be Added for Production

- `securityContext` with `runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false` on all containers
- Kubernetes NetworkPolicies restricting which pods can talk to which services
- Encryption at rest for Kubernetes Secrets (`EncryptionConfiguration`)
- External secrets manager integration (Vault, AWS Secrets Manager)
- mTLS between services (e.g. via a service mesh like Istio or Linkerd)
- RBAC limiting which service accounts can access which namespaces and resources
- Image scanning in CI (Trivy, Grype) and admission webhook to block vulnerable images
- Rate limiting on the nginx layer to prevent API abuse
- TLS termination at the Ingress layer (cert-manager + Let's Encrypt)

---

## Scaling Discussion

### Frontend
nginx is completely stateless — it serves static files and proxies requests. Scaling from 2 to 100 replicas requires only `kubectl scale deployment frontend --replicas=100`. The only limit is cluster node capacity. No application changes are needed.

### Backend
The Flask backend is stateless with respect to the application domain — all state is in PostgreSQL. Horizontal scaling works correctly today for read-heavy workloads. The bottleneck for real production load is database connections: each pod opens one connection per request, so N replicas × concurrent requests = connection pressure on PostgreSQL. Before scaling beyond ~10 replicas, connection pooling (PgBouncer or SQLAlchemy pool) would be required.

### Database
PostgreSQL with a single replica does not scale horizontally in the current setup. For a read-heavy workload, streaming replication with read replicas would distribute `SELECT` queries. For write-heavy workloads, the options are vertical scaling (larger instance) or migrating to a distributed database. A Kubernetes-native approach would be to use the CloudNativePG operator, which manages PostgreSQL clusters, failover, and backup within Kubernetes using standard PVC storage.
