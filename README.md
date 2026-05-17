# TFT Odds API

Small, modular FastAPI service for calculating TFT shop odds with finite-pool, slot-by-slot shop generation.

## Run

Start the backend API:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r backend/requirements.txt
./.venv/bin/python -m uvicorn backend.server:app --reload
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Then open the frontend:

```text
http://127.0.0.1:5173/
```

Swagger is available at:

```text
http://127.0.0.1:8000/docs
```

Run tests with:

```bash
./.venv/bin/python -m pytest backend/tests
```

## Model

The shop model generates one slot at a time:

1. Roll a unit tier using the configured level odds.
2. If the rolled tier is the target tier, draw from the remaining temporary tier pool.
3. If the target appears, reduce both temporary target copies and temporary tier pool for later shop slots.
4. If another unit from the same tier appears, reduce only the temporary tier pool for later shop slots.
5. After the shop, bought target copies are permanently removed from the pool.

## Reference Odds

The chance of getting a certain cost of champion in your shop at each level:

| Level | 1 Cost | 2 Cost | 3 Cost | 4 Cost | 5 Cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lvl 2 | 100% | 0% | 0% | 0% | 0% |
| Lvl 3 | 75% | 25% | 0% | 0% | 0% |
| Lvl 4 | 55% | 30% | 15% | 0% | 0% |
| Lvl 5 | 45% | 33% | 20% | 2% | 0% |
| Lvl 6 | 30% | 40% | 25% | 5% | 0% |
| Lvl 7 | 19% | 30% | 40% | 10% | 1% |
| Lvl 8 | 15% | 20% | 32% | 30% | 3% |
| Lvl 9 | 10% | 17% | 25% | 33% | 15% |
| Lvl 10 | 5% | 10% | 20% | 40% | 25% |
| Lvl 11 | 1% | 2% | 12% | 50% | 35% |

## Pool Sizes

Pool size, also called bag size, is the number of each champion available in the shop. For each champion bought from the pool, the probability of hitting that champion decreases until it is empty.

| Cost | Pool Size |
| --- | ---: |
| 1 Cost | 29 |
| 2 Cost | 22 |
| 3 Cost | 18 |
| 4 Cost | 10 |
| 5 Cost | 9 |

## Total Tier Pool Copies

The `tier_pool_remaining` input should use the total number of remaining copies across all champions of the same cost.

| Cost | Champions In Tier | Copies Per Champion | Total Tier Pool Copies |
| --- | ---: | ---: | ---: |
| 1 Cost | 14 | 29 | 406 |
| 2 Cost | 13 | 22 | 286 |
| 3 Cost | 13 | 18 | 234 |
| 4 Cost | 14 | 10 | 140 |
| 5 Cost | 9 | 9 | 81 |

For example, if you are rolling for a 4-cost and no 4-cost units have been removed from the pool yet, use:

```json
{
  "tier_pool_remaining": 140
}
```

## Project Structure

```text
backend/
  server.py              FastAPI server and API endpoint definitions
  requirements.txt       Python dependencies
  tft_odds/              Odds calculation package
  tests/                 Backend tests

frontend/
  static/                HTML, CSS, and JavaScript visualizer
```
