# TFT Odds Visualizer

Interactive TFT odds calculator for answering:

```text
What are the odds I hit X copies of a specific unit with my current level, gold, and pool state?
```

The project now has a FastAPI backend for exact probability calculations and a Vite/React frontend for visualizing the results.

## What It Includes

- Dashboard view for entering level, unit cost, current pool state, copies needed, and gold.
- Exact one-slot odds.
- Exact one-shop distribution with fixed 5-slot shops.
- Exact rolldown distribution using a buy-every-target policy.
- Shop odds reference table by level and unit cost.
- Pool size reference by unit cost.
- Random rolldown simulator using the current dashboard settings.
- Swagger docs for testing backend endpoints directly.

## Run Locally

Start the backend API from the repo root:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r backend/requirements.txt
./.venv/bin/python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload
```

Start the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the app:

```text
http://127.0.0.1:5173/
```

Swagger is available at:

```text
http://127.0.0.1:8000/docs
```

Run backend tests:

```bash
./.venv/bin/python -m pytest backend/tests
```

Build the frontend:

```bash
cd frontend
npm run build
```

## Current Assumptions

- Shops always have `5` slots.
- Roll cost is fixed at `2` gold.
- Unit cost is derived from selected unit tier.
- Tier odds are derived from selected level and unit cost.
- The rolldown policy buys every target copy that appears, up to copies needed and available gold.
- The current natural shop before rolling is not included; the model starts from paid refreshes.

## Calculation Model

The calculation code lives in `backend/tft_odds/calculator.py`. It is framework-free, so the same math can be used by the API, tests, and future tooling.

### One-Slot Odds

For one shop slot, the target unit probability is conditional probability:

```text
P(target unit)
= P(slot rolls target tier) * P(target unit | target tier)
```

In code:

```text
P(target unit)
= tier_odds * target_copies_remaining / tier_pool_remaining
```

The other two outcomes are:

```text
P(same tier, not target)
= tier_odds * (tier_pool_remaining - target_copies_remaining) / tier_pool_remaining
```

```text
P(other tier)
= 1 - tier_odds
```

These three outcomes always sum to `1`:

```text
target + same_tier_non_target + other_tier = 1
```

Example for a 4-cost at level 8:

```text
tier_odds = 0.30
target_copies_remaining = 8
tier_pool_remaining = 140

P(target) = 0.30 * 8 / 140 = 0.017142857 = 1.714%
```

### One-Shop Distribution

The shop is generated slot by slot instead of using a simple binomial approximation. This matters because if one slot hits the target tier, later slots should recalculate against the updated temporary pool.

For each of the 5 shop slots:

1. Roll a unit tier using the selected level odds.
2. If the slot rolls the target tier, draw from the remaining temporary tier pool.
3. If the target appears, reduce temporary target copies and temporary tier pool for later slots in that shop.
4. If a same-tier non-target appears, reduce only the temporary tier pool for later slots in that shop.

The shop calculation keeps a probability distribution over temporary states:

```text
(hits_so_far, target_left_in_temp_shop_pool, tier_pool_left_in_temp_shop_pool)
```

For each slot outcome:

```text
P(next_shop_state) += P(current_shop_state) * P(slot_outcome | current_shop_state)
```

After 5 slots, the temporary states are collapsed into:

```text
P(shop has 0 target copies)
P(shop has 1 target copy)
P(shop has 2 target copies)
...
P(shop has 5 target copies)
```

### Buy Policy

When a shop has target copies, the model buys as many as allowed by three caps:

```text
affordable_copies = floor(gold_remaining / unit_cost)
```

```text
copies_to_buy = min(shop_hits, copies_still_needed, affordable_copies)
```

This prevents the model from buying more copies than appeared, more than the target goal needs, or more than the current gold can afford.

### Rolldown Distribution

The main rolldown calculation uses dynamic programming over persistent states:

```text
(copies_bought, gold_left, target_copies_left, tier_pool_left)
```

The starting state has probability `1`:

```text
(0, starting_gold, target_copies_remaining, tier_pool_remaining)
```

For each active state:

1. Spend `2` gold to roll.
2. Compute the exact one-shop distribution from the current pool state.
3. For each possible `shop_hits` result, apply the buy policy.
4. Update copies bought, gold, target copies left, and tier pool left.
5. Move probability mass into the next state.

The transition formula is:

```text
P(next_state) += P(current_state) * P(shop_hits)
```

The process stops when a state cannot roll anymore or has already bought the requested number of copies.

At the end, detailed states are collapsed into the final distribution:

```text
P(buy exactly 0 target copies)
P(buy exactly 1 target copy)
P(buy exactly 2 target copies)
...
```

From that distribution, the API also calculates:

```text
chance_to_hit_goal = P(copies_bought >= copies_needed)
```

```text
expected_copies_bought = sum(copies_bought * P(copies_bought))
```

### Simulator

The simulator view is intentionally different from the exact backend calculation. It runs one random sample path using the same settings and the same finite-pool slot logic. It is useful for seeing what one possible rolldown could look like, while the dashboard shows the exact probability distribution across all possible rolldowns.

## API Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Confirms the API is running. |
| `GET /config/defaults` | Returns default level odds and pool sizes. |
| `POST /odds/slot` | Calculates one-slot target, same-tier non-target, and other-tier odds. |
| `POST /odds/shop` | Calculates exact target-hit distribution for one 5-slot shop. |
| `POST /policy/buy-targets` | Calculates how many target copies are bought from a shop. |
| `POST /odds/rolldown` | Calculates final bought-copy distribution after rolling down. |

## Frontend Views

The left rail controls the active view:

| Button | View |
| --- | --- |
| Dashboard | Main odds dashboard and charts. |
| Shop Odds | Shop odds table plus pool size reference. |
| Simulator | Random rolldown simulator using current dashboard settings. |

## Reference Odds

Chance of getting a certain cost of champion in one shop slot at each level:

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

Pool size, also called bag size, is the number of each champion available in the shop.

| Cost | Copies Per Champion |
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

For example, if you are rolling for a 4-cost and no 4-cost units have been removed from the pool yet:

```json
{
  "tier_pool_remaining": 140
}
```

## Project Structure

```text
backend/
  server.py              FastAPI app and API endpoint definitions
  requirements.txt       Backend Python dependencies
  tft_odds/              Framework-free odds calculation package
  tests/                 Backend calculation tests

frontend/
  index.html             Vite entry HTML
  package.json           Frontend scripts and dependencies
  src/main.jsx           React application
  src/styles.css         Frontend styling
  vite.config.js         Vite config and API proxy
```

Existing root files from the original repository, such as `requirements.txt` and `jupyter/`, are not used by the current web app.
