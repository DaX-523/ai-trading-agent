# ai-trading-bot

Python LLM trading agent with a React dashboard.

The app boots in **SANDBOX** (paper trading, fake $1000, no Lighter orders). Switch to **TESTNET** or **LIVE** from the navbar. Dashboard, invocations, and leaderboard only show data for the currently selected mode.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set these in `.env`:

- `OPENROUTER_API_KEY`
- `DATABASE_URL`
- `ADMIN_API_TOKEN` — required for changing trading mode and creating/editing/deleting models. Mutating endpoints fail closed if this is unset.

SQLAlchemy maps onto existing Postgres tables. Do not run `create_all` against a populated database.

Apply the trading-mode migration:

```bash
psql "$DATABASE_URL" -f migrations/0001_add_trading_modes.sql
```

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

## Models and credentials

Add bots from the **Models** page. Unlock writes with `ADMIN_API_TOKEN` (sent as `X-Admin-Token`). Lighter API keys are write-only: after save the UI only shows whether they are configured.

- **SANDBOX**: no Lighter keys required. The worker simulates fills against a $1000 paper ledger.
- **TESTNET**: each model needs a Lighter testnet API key and account index. Create a testnet wallet, fund it at `https://testnet.zklighter.elliot.ai/api/v1/faucet?l1_address=YOUR_ETH_ADDRESS`, then save those credentials on the model.
- **LIVE**: each model needs a mainnet Lighter API key and account index. Switching into LIVE requires a confirmation dialog plus the admin token.

## Tests

```bash
python -m unittest tests.test_indicators tests.test_paper_trading tests.test_trading_backend tests.test_leaderboard
```
