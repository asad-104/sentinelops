# Hosting the demo on Streamlit Community Cloud

The hosted demo is the local viewer with one extra step at startup:
- **Generated dev data:** `app/cloud_app.py` generates the synthetic dev split into a temporary directory and checks it against the frozen dev manifest.
- **What it shows:** dev scenarios, committed dev traces, and the M5 results as aggregate counts only.
- **What it never does:** list fresh-split runs, read held-out paths, call a model, or use a secret.

UI labels below are from the Community Cloud docs, as checked on 2026-11-09. They may change.

## Steps

1. **Account:** sign in at [share.streamlit.io](https://share.streamlit.io) and connect GitHub: **Workspaces** → **Connect GitHub account** → follow GitHub's prompts → **Authorize streamlit**.
2. **Private-repo access** (needed while `asad-104/sentinelops` is private):
   1. Click your GitHub username in the upper-left corner, then **Settings** → **Linked accounts**.
   2. Under *Source control*, click **Connect here** → **Authorize streamlit**.
   3. You need **admin** rights on the repository.
3. **Deploy:**
   1. Click **Create app** (upper right) → **Yup, I have an app**.
   2. Fill in the fields:
      - **Repository:** `asad-104/sentinelops`
      - **Branch:** `main`
      - **Main file path:** `app/cloud_app.py`
   3. Optionally choose an **App URL** subdomain.
4. **Advanced settings:**
   1. Click **Advanced settings**.
   2. **Python version:** `3.12`.
   3. Leave **Secrets** empty: the app reads none.
   4. Click **Save**. The app builds, using `app/requirements.txt`, which sits next to the entrypoint.
5. **First start:**
   - The first visit generates the dev split, which takes a few seconds.
   - If generation or the manifest check fails, the page says so instead of showing data. Reload to retry, or reboot the app from its settings.
6. **Visibility:**
   - While the repository is private, the app is private to the workspace's developers.
   - Community Cloud allows **one private app at a time**.
   - To make it public later: **App settings** → **Sharing** → *Who can view this app* → **This app is public and searchable**. Or open the app → **Share** → **Make this app public**.

## Things to check on the first deploy

- **The local config binds to `127.0.0.1`.** `.streamlit/config.toml` sets `server.address = "127.0.0.1"`, which keeps the local viewer off the network. The docs don't say whether Community Cloud overrides it.
  - If the deployed app doesn't come up (a health-check or connection error in the logs), that line is the first suspect.
  - The fix: move the binding out of the config file and into the local run command (`streamlit run app/viewer.py --server.address 127.0.0.1`).
- **Sleep.** Apps with no traffic for 12 hours go to sleep. A visit wakes them, and then dev data is generated again.
- **Resource limits** (dated February 2024 in the docs, and may change): about 0.078–2 CPU cores and 690 MB–2.7 GB of memory. The demo needs little: about 47 MB of generated dev data plus the committed outputs.

## Terms (Streamlit deployment terms, last updated November 2025)

- No sensitive personal data. The demo has none: all data is synthetic.
- Snowflake receives a broad, perpetual licence to the app's code and content in order to run the service, may monitor usage, and may suspend or remove apps.
- Users must be 18 or older.
- Don't imply that Snowflake endorses the app.
