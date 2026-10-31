# Self-host Repo Séance with Coolify

This deployment runs the web app, API, Postgres/pgvector, and Ollama on one
Linux server. Coolify manages the Compose project and public HTTPS domains;
Ollama and Postgres are not exposed publicly.

## 1. Install Coolify on a VPS

Provision a fresh supported Linux VPS with a public IPv4 address. Coolify's
installation command must be run on that VPS over SSH, not in Windows
PowerShell. Use the current command and prerequisites from the
[official Coolify installation guide](https://coolify.io/docs/installation).
The command you provided is:

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash
```

It downloads and runs an installer with root privileges, so verify the URL
against Coolify's official instructions and run it only on a server you control.

The full stack also needs enough resources for Docker image builds, Postgres,
and CPU inference. Choose a server with more than Coolify's own minimum; 8 GB
RAM and 50 GB disk is a practical starting point for this project. A CPU-only
Ollama service will be slower than the local GPU setup.

## 2. Add the Compose project

1. In Coolify, create a project and add a resource from the public GitHub
   repository `SomSatwik/repo-seance`.
2. Select the **Docker Compose** build pack.
3. Set the base directory to the repository root and the Compose file to
   `infra/docker-compose.coolify.yml`.
4. Configure these variables before deploying:

   | Variable | Value |
   | --- | --- |
   | `POSTGRES_PASSWORD` | A strong, URL-safe alphanumeric password (at least 32 characters). It is used in the PostgreSQL connection URL. |
   | `API_PUBLIC_URL` | The public HTTPS URL that will be assigned to the API service, e.g. `https://api.example.com`. |
   | `WEB_ORIGIN` | The public HTTPS origin assigned to the web service, e.g. `https://app.example.com`. |
   | `SENTRY_DSN` | Optional; leave empty to disable Sentry. |

5. Add a Coolify domain for the `web` service on port `3000` and one for the
   `api` service on port `8000`. The `API_PUBLIC_URL` and `WEB_ORIGIN` values
   must match those domains exactly.
6. Deploy the Compose project. The first run downloads Gemma 2B and
   `nomic-embed-text`; wait for both model downloads and for all services to
   become healthy before trying AI endpoints.

`NEXT_PUBLIC_API_URL` is passed as a web-image build argument, so changing
`API_PUBLIC_URL` requires rebuilding the web service. The API's `CORS_ORIGINS`
uses `WEB_ORIGIN` at runtime.

## 3. Verify

- Open `https://<api-domain>/health`; verify the JSON reports `"db":"connected"`.
- Open the web domain and confirm its health indicator reaches the API.
- Import a repository, then test `/ask`, `/roadmap`, and GhostTrace.
- Check that Postgres, Ollama models, and cloned repositories use their named
  volumes; do not remove those volumes when recreating the Compose project.
- Keep Postgres and Ollama internal; only route the web and API services through
  Coolify. Back up the database and test restoring it.

The API currently has no authentication or rate limiting. Do not expose it to
untrusted traffic without adding those protections.
