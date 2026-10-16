# Run and deploy the app

## Published dashboard

https://marketing-uplift-lab-171026.racinggrass8.chatgpt.site

Sites confirmed successful private deployment. Opening it requires ChatGPT sign-in. Local browser interaction checks passed; the private hosted page showed its sign-in gate in this browser. The API remains runnable locally/container-ready and is not publicly hosted.

## Browser dashboard

The static dashboard works independently of the API. It contains only aggregated benchmark outputs, not customer records. All scenario calculations run in the visitor's browser. It does not store or upload user inputs. Its static Sites deployment is private by default.

## App and API together

From this project folder, install the small app dependency set:

```sh
python -m pip install -r requirements-app.txt
uvicorn api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 for the app and http://127.0.0.1:8000/docs for interactive API documentation.

- `GET /api/health`: readiness and dataset version.
- `GET /api/results`: model comparisons, intervals and provenance.
- `GET /api/curves`: precomputed targeting capacity curves.
- `POST /api/scenario`: validated, hypothetical economics.

Example JSON request:

```json
{"strategy":"Boosted S-learner","capacity":0.2,"audience":100000,"margin":50,"cost":0.05}
```

Capacity must match the evaluated 5% grid. Only the three curve strategies are supported for scenarios. Responses scale benchmark estimates to the requested audience and return purchase and net-contribution intervals. They do not produce individual predictions or retrain models. Audience scaling assumes the same population distribution; it is not new evidence for a different company.

## Container deployment

```sh
docker build -t marketing-decision-lab .
docker run --rm -p 8000:8000 marketing-decision-lab
```

The container serves both app and API. It runs as a non-root user and excludes raw/sample data. Configure your host's port as 8000. Public API hosting is separate from the static Sites publication; the provided container has no built-in authentication and exposes only aggregate public-benchmark results. No credentials or customer uploads are needed.

The Docker image must be built and tested on a machine with Docker available; local source tests alone do not verify container execution.

## API tests

Install `pytest` and `httpx`, then run:

```sh
python -m pytest test_api.py -q
```
