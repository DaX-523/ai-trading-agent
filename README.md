# ai-trading-bot

Python LLM trading agent with a React dashboard.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `OPENROUTER_API_KEY` and `DATABASE_URL` in `.env`. SQLAlchemy maps onto existing Postgres tables (`"Models"`, `"Invocations"`, `"ToolCalls"`, `"PortfolioSize"`). Do not run `create_all` against a populated database.

## Run

API server (port 3000):

```bash
python server.py
```

Background worker (agent every 5 minutes, price tracker every 2 minutes):

```bash
python worker.py
```

Frontend:

```bash
cd frontend
bun install
bun run dev
```

## Tests

```bash
python -m unittest tests.test_indicators
```
