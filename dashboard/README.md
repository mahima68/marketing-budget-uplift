# Dashboard

A static, browser-local decision explorer using verified held-out results. No user data is uploaded or saved. Controls recalculate hypothetical economics; they do not retrain models or establish new causal effects. Open via an HTTP server, not file://.

Run from this folder: `python -m http.server 8080 --directory dist`.

The independent FastAPI service in the parent folder exposes the same results and scenario arithmetic; the deployed static dashboard works without that service.
