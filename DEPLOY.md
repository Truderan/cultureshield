# Deploying CultureShield AI (free tier)

GitHub hosts the **frontend** (GitHub Pages). GitHub cannot run the Python
backend or MongoDB, so those go on free services:

| Piece    | Where                | Config                           |
|----------|----------------------|----------------------------------|
| Frontend | GitHub Pages         | `.github/workflows/deploy-frontend.yml` |
| Backend  | Render (free web svc)| `render.yaml`                    |
| Database | MongoDB Atlas (M0)   | connection string -> `MONGO_URL` |

## Steps
1. Push this folder to a GitHub repo (branch `main`).
2. **Atlas:** create a free M0 cluster, add a DB user, allow access from anywhere (0.0.0.0/0), copy the connection string.
3. **Render:** New > Blueprint > pick the repo. Fill the prompted env vars
   (`MONGO_URL`, `MFA_ENCRYPTION_KEY`, `ANTHROPIC_API_KEY`, Paystack, Resend, `FRONTEND_URL`, `CORS_ORIGINS`).
   Generate the Fernet key with the command in `backend/.env.example`.
4. **GitHub:** Settings > Pages > Source = "GitHub Actions". Then Settings > Secrets and variables > Actions > Variables:
   - `REACT_APP_BACKEND_URL` = your Render URL (no trailing slash)
   - `PUBLIC_URL` = `/<repo-name>` for a project site, or empty with a custom domain
5. Push to `main` (or run the workflow manually). Set Render's `FRONTEND_URL` to the Pages URL and `CORS_ORIGINS` to its origin.

Notes: Render's free service sleeps after ~15 min idle (first request is slow).
Paystack webhooks need the Render URL. Resend still needs a verified domain for non-sandbox recipients.
