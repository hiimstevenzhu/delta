import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Coins, Dices, LayoutDashboard, Table2, Target, Trophy } from "lucide-react";
import "./styles.css";

const LEVEL_ODDS = {
  2: { 1: 1.0, 2: 0, 3: 0, 4: 0, 5: 0 },
  3: { 1: 0.75, 2: 0.25, 3: 0, 4: 0, 5: 0 },
  4: { 1: 0.55, 2: 0.3, 3: 0.15, 4: 0, 5: 0 },
  5: { 1: 0.45, 2: 0.33, 3: 0.2, 4: 0.02, 5: 0 },
  6: { 1: 0.3, 2: 0.4, 3: 0.25, 4: 0.05, 5: 0 },
  7: { 1: 0.19, 2: 0.3, 3: 0.4, 4: 0.1, 5: 0.01 },
  8: { 1: 0.15, 2: 0.2, 3: 0.32, 4: 0.3, 5: 0.03 },
  9: { 1: 0.1, 2: 0.17, 3: 0.25, 4: 0.33, 5: 0.15 },
  10: { 1: 0.05, 2: 0.1, 3: 0.2, 4: 0.4, 5: 0.25 },
  11: { 1: 0.01, 2: 0.02, 3: 0.12, 4: 0.5, 5: 0.35 },
};

const COPIES_PER_CHAMPION = { 1: 29, 2: 22, 3: 18, 4: 10, 5: 9 };
const CHAMPIONS_IN_TIER = { 1: 14, 2: 13, 3: 13, 4: 14, 5: 9 };
const ROLL_COST = 2;
const SHOP_SLOTS = 5;

function App() {
  const [activeView, setActiveView] = useState("dashboard");
  const [level, setLevel] = useState(8);
  const [tier, setTier] = useState(4);
  const [targetCopiesRemaining, setTargetCopiesRemaining] = useState("8");
  const [tierPoolRemaining, setTierPoolRemaining] = useState(String(totalTierPool(4)));
  const [copiesNeeded, setCopiesNeeded] = useState("3");
  const [gold, setGold] = useState("50");
  const [result, setResult] = useState(null);
  const [simulation, setSimulation] = useState(null);
  const [error, setError] = useState("");

  const tierOdds = LEVEL_ODDS[level][tier];
  const maxTargetCopies = COPIES_PER_CHAMPION[tier];

  const payload = useMemo(
    () => ({
      tier_odds: tierOdds,
      target_copies_remaining: toInputNumber(targetCopiesRemaining),
      tier_pool_remaining: toInputNumber(tierPoolRemaining),
      shop_slots: SHOP_SLOTS,
      copies_needed: toInputNumber(copiesNeeded),
      gold: toInputNumber(gold),
      roll_cost: ROLL_COST,
      unit_cost: tier,
    }),
    [tierOdds, targetCopiesRemaining, tierPoolRemaining, copiesNeeded, gold, tier],
  );

  useEffect(() => {
    setTierPoolRemaining(String(totalTierPool(tier)));
    setTargetCopiesRemaining(String(Math.min(COPIES_PER_CHAMPION[tier] - 1, COPIES_PER_CHAMPION[tier])));
  }, [tier]);

  useEffect(() => {
    calculate(payload, setResult, setError);
  }, [payload]);

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <div className="logo-mark">T</div>
          <div>
            <h1>TFT Odds Visualizer</h1>
            <p>Roll down, inspect the pool, and see the exact distribution before you spend.</p>
          </div>
        </div>
        <a className="swagger-link" href="http://127.0.0.1:8000/docs">
          Swagger
        </a>
      </section>

      <section className="workspace">
        <aside className="control-rail">
          <button
            className={`rail-icon ${activeView === "dashboard" ? "active" : ""}`}
            type="button"
            aria-label="Dashboard"
            onClick={() => setActiveView("dashboard")}
          >
            <LayoutDashboard size={22} />
          </button>
          <button
            className={`rail-icon ${activeView === "odds" ? "active" : ""}`}
            type="button"
            aria-label="Shop odds table"
            onClick={() => setActiveView("odds")}
          >
            <Table2 size={22} />
          </button>
          <button
            className={`rail-icon ${activeView === "simulator" ? "active" : ""}`}
            type="button"
            aria-label="Rolldown simulator"
            onClick={() => {
              setActiveView("simulator");
              setSimulation(simulateRolldown(payload));
            }}
          >
            <Dices size={22} />
          </button>
          <div className="rail-spacer" aria-hidden="true" />
        </aside>

        <section className="tool-surface">
          {activeView === "dashboard" ? (
            <>
              <section className="card control-card">
                <div className="card-heading">
                  <h2>Scenario</h2>
                </div>

                <div className="controls-grid">
                  <Field label="Level">
                    <select value={level} onChange={(event) => setLevel(Number(event.target.value))}>
                      {Object.keys(LEVEL_ODDS).map((value) => (
                        <option key={value} value={value}>Level {value}</option>
                      ))}
                    </select>
                  </Field>

                  <Field label="Unit cost">
                    <select value={tier} onChange={(event) => setTier(Number(event.target.value))}>
                      {[1, 2, 3, 4, 5].map((value) => (
                        <option key={value} value={value}>{value} Cost</option>
                      ))}
                    </select>
                  </Field>

                  <Readout label="Tier odds" value={formatPercent(tierOdds)} tone={`cost-${tier}`} />

                  <Field label="Target copies left">
                    <input
                      type="number"
                      min="0"
                      max={maxTargetCopies}
                      value={targetCopiesRemaining}
                      onChange={(event) => setTargetCopiesRemaining(event.target.value)}
                    />
                  </Field>

                  <Field label="Tier pool left">
                    <input
                      type="number"
                      min="0"
                      value={tierPoolRemaining}
                      onChange={(event) => setTierPoolRemaining(event.target.value)}
                    />
                  </Field>

                  <Field label="Copies needed">
                    <input
                      type="number"
                      min="0"
                      value={copiesNeeded}
                      onChange={(event) => setCopiesNeeded(event.target.value)}
                    />
                  </Field>

                  <Field label="Gold">
                    <input type="number" min="0" value={gold} onChange={(event) => setGold(event.target.value)} />
                  </Field>
                </div>

                {error && <div className="error">{error}</div>}
              </section>

              <section className="metric-grid">
                <Metric icon={<Trophy size={20} />} label="Chance to hit goal" value={result ? formatPercent(result.rolldown.chance_to_hit_goal) : "--"} />
                <Metric icon={<Target size={20} />} label="One-slot target odds" value={result ? formatPercent(result.slot.target) : "--"} />
                <Metric icon={<Coins size={20} />} label="Expected copies bought" value={result ? result.rolldown.expected_copies_bought.toFixed(2) : "--"} />
              </section>

              <section className="result-grid">
                <ChartCard title="One Slot" rows={result ? slotRows(result.slot) : []} />
                <ChartCard title="One Shop" subtitle={result ? `Expected ${result.shop.expected_hits.toFixed(3)}` : ""} rows={result ? distributionRows(result.shop.distribution, "copies") : []} />
                <ChartCard title="Rolldown" subtitle={result ? `Expected ${result.rolldown.expected_copies_bought.toFixed(3)}` : ""} rows={result ? distributionRows(result.rolldown.distribution, "bought") : []} wide />
              </section>
            </>
          ) : activeView === "odds" ? (
            <OddsTable />
          ) : (
            <Simulator payload={payload} simulation={simulation} onRun={() => setSimulation(simulateRolldown(payload))} />
          )}
        </section>
      </section>
    </main>
  );
}

function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function Readout({ label, value, tone = "" }) {
  return (
    <div className={`readout ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({ icon, label, value }) {
  return (
    <article className="metric-card">
      <div className="metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function ChartCard({ title, subtitle = "", rows, wide = false }) {
  return (
    <article className={`card chart-card ${wide ? "wide" : ""}`}>
      <div className="card-heading">
        <h2>{title}</h2>
        <span>{subtitle}</span>
      </div>
      <div className="bars">
        {rows.map(([label, value]) => (
          <div className="bar-row" key={label}>
            <span className="bar-label">{label}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${Math.max(value * 100, 0.3)}%` }} />
            </div>
            <span className="bar-value">{formatPercent(value)}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

function OddsTable() {
  return (
    <>
      <section className="card odds-card">
        <div className="card-heading">
          <h2>Shop Odds at Each Level</h2>
          <span>Chance each shop slot rolls a unit cost</span>
        </div>

        <div className="odds-table-wrap">
          <table className="odds-table">
            <thead>
              <tr>
                <th>Level</th>
                {[1, 2, 3, 4, 5].map((cost) => (
                  <th key={cost} className={`cost-${cost}-text`}>{cost} Cost</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(LEVEL_ODDS).map(([levelValue, odds]) => (
                <tr key={levelValue}>
                  <th>Lvl {levelValue}</th>
                  {[1, 2, 3, 4, 5].map((cost) => (
                    <td key={cost} className={odds[cost] === 0 ? "zero-odds" : `cost-${cost}-text`}>
                      {formatPercent(odds[cost])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card pool-card">
        <div className="card-heading">
          <h2>Pool Sizes</h2>
        </div>
        <p>
          The Pool Size, or Bag Size, is the number of each champion available in the shop.
          For each champion bought in the pool, the probability of hitting that champion
          decreases until it is empty.
        </p>
        <ul className="pool-list">
          {[1, 2, 3, 4, 5].map((cost) => (
            <li key={cost}>
              <span className={`cost-${cost}-text`}>{cost} Cost</span>
              <strong>{COPIES_PER_CHAMPION[cost]}</strong>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

function Simulator({ payload, simulation, onRun }) {
  const finalBought = simulation?.copiesBought ?? 0;
  const hitGoal = finalBought >= payload.copies_needed;

  return (
    <section className="card simulator-card">
      <div className="card-heading">
        <h2>Rolldown Simulator</h2>
        <button className="run-button" type="button" onClick={onRun}>Roll Down</button>
      </div>

      <section className="sim-summary">
        <Metric icon={<Dices size={20} />} label="Copies bought" value={simulation ? finalBought : "--"} />
        <Metric icon={<Coins size={20} />} label="Gold left" value={simulation ? simulation.goldLeft : "--"} />
        <Metric icon={<Trophy size={20} />} label="Result" value={simulation ? (hitGoal ? "Hit" : "Miss") : "--"} />
      </section>

      <div className="sim-log">
        {(simulation?.shops ?? []).map((shop) => (
          <article className="sim-row" key={shop.shopNumber}>
            <strong>Shop {shop.shopNumber}</strong>
            <span>{shop.hitsSeen} seen</span>
            <span>{shop.bought} bought</span>
            <span>{shop.goldLeft}g left</span>
            <span>{shop.totalBought} total</span>
          </article>
        ))}
      </div>
    </section>
  );
}

function slotRows(slot) {
  return [
    ["Target", slot.target],
    ["Same cost", slot.same_tier_non_target],
    ["Other cost", slot.other_tier],
  ];
}

function distributionRows(distribution, suffix) {
  return Object.entries(distribution).map(([key, value]) => [`${key} ${suffix}`, Number(value)]);
}

async function calculate(payload, setResult, setError) {
  try {
    setError("");
    const [slot, shop, rolldown] = await Promise.all([
      postJson("/odds/slot", {
        tier_odds: payload.tier_odds,
        target_copies_remaining: payload.target_copies_remaining,
        tier_pool_remaining: payload.tier_pool_remaining,
      }),
      postJson("/odds/shop", {
        tier_odds: payload.tier_odds,
        target_copies_remaining: payload.target_copies_remaining,
        tier_pool_remaining: payload.tier_pool_remaining,
        shop_slots: payload.shop_slots,
      }),
      postJson("/odds/rolldown", payload),
    ]);

    setResult({ slot, shop, rolldown });
  } catch (error) {
    setError(error.message);
  }
}

async function postJson(path, body) {
  const response = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json();

  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join(", ")
      : data.detail;
    throw new Error(detail || "Request failed");
  }

  return data;
}

function totalTierPool(tier) {
  return CHAMPIONS_IN_TIER[tier] * COPIES_PER_CHAMPION[tier];
}

function toInputNumber(value) {
  if (value === "") {
    return 0;
  }
  return Number(value);
}

function simulateRolldown(payload) {
  let goldLeft = payload.gold;
  let targetLeft = payload.target_copies_remaining;
  let tierPoolLeft = payload.tier_pool_remaining;
  let copiesBought = 0;
  let shopNumber = 0;
  const shops = [];

  while (goldLeft >= ROLL_COST && copiesBought < payload.copies_needed) {
    shopNumber += 1;
    goldLeft -= ROLL_COST;

    const shop = simulateShop({
      tierOdds: payload.tier_odds,
      targetLeft,
      tierPoolLeft,
    });
    const copiesStillNeeded = payload.copies_needed - copiesBought;
    const affordable = Math.floor(goldLeft / payload.unit_cost);
    const bought = Math.min(shop.hitsSeen, copiesStillNeeded, affordable);

    copiesBought += bought;
    goldLeft -= bought * payload.unit_cost;
    targetLeft -= bought;
    tierPoolLeft -= bought;

    shops.push({
      shopNumber,
      hitsSeen: shop.hitsSeen,
      bought,
      goldLeft,
      totalBought: copiesBought,
    });
  }

  return { shops, copiesBought, goldLeft, targetLeft, tierPoolLeft };
}

function simulateShop({ tierOdds, targetLeft, tierPoolLeft }) {
  let hitsSeen = 0;
  let tempTargetLeft = targetLeft;
  let tempTierPoolLeft = tierPoolLeft;

  for (let slot = 0; slot < SHOP_SLOTS; slot += 1) {
    if (Math.random() >= tierOdds || tempTierPoolLeft <= 0) {
      continue;
    }

    const targetChanceWithinTier = tempTargetLeft / tempTierPoolLeft;
    if (Math.random() < targetChanceWithinTier && tempTargetLeft > 0) {
      hitsSeen += 1;
      tempTargetLeft -= 1;
      tempTierPoolLeft -= 1;
    } else {
      tempTierPoolLeft -= 1;
    }
  }

  return { hitsSeen };
}

function formatPercent(value) {
  return `${(value * 100).toFixed(value < 0.001 && value > 0 ? 3 : 2)}%`;
}

createRoot(document.getElementById("root")).render(<App />);
