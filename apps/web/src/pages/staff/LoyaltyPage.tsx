import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  apiFetch,
  formatMoney,
  type Coupon,
  type CouponRedemption,
  type LoyaltyAccount,
  type LoyaltyTransaction,
} from "../../lib/api";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../lib/auth";

const EMPTY_COUPON = {
  code: "",
  name: "",
  discount_type: "PERCENT",
  discount_value: "10",
  minimum_spend_minor: "0",
  valid_from: new Date().toISOString().slice(0, 10),
  maximum_redeem_count: "",
  usage_limit_per_customer: "",
};

export default function LoyaltyPage() {
  const { has } = useAuth();
  const canManage = has("loyalty.manage");
  const canRedeem = has("loyalty.redeem");
  const [account, setAccount] = useState<LoyaltyAccount | null>(null);
  const [transactions, setTransactions] = useState<LoyaltyTransaction[]>([]);
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [transactionDraft, setTransactionDraft] = useState({
    type: "EARN",
    points: "50",
    reason: "",
  });
  const [couponDraft, setCouponDraft] = useState(EMPTY_COUPON);
  const [redeemDraft, setRedeemDraft] = useState({
    coupon_id: "",
    order_id: "",
    discount_amount_minor: "0",
  });
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [accountData, transactionList, couponList] = await Promise.all([
      apiFetch<LoyaltyAccount>("/api/v1/loyalty/account"),
      apiFetch<LoyaltyTransaction[]>("/api/v1/loyalty/transactions"),
      apiFetch<Coupon[]>("/api/v1/loyalty/coupons"),
    ]);
    setAccount(accountData);
    setTransactions(transactionList);
    setCoupons(couponList);
  }, []);

  useEffect(() => {
    void load().catch((err) =>
      setError(err instanceof ApiError ? err.detail : "Could not load loyalty data.")
    );
  }, [load]);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setNotice(await action());
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "The loyalty action failed.");
    } finally {
      setBusy(false);
    }
  }

  function recordTransaction() {
    return run(async () => {
      await apiFetch<LoyaltyTransaction>("/api/v1/loyalty/transactions", {
        method: "POST",
        body: JSON.stringify({
          type: transactionDraft.type,
          points: Number(transactionDraft.points),
          reason: transactionDraft.reason.trim(),
        }),
      });
      setTransactionDraft({ ...transactionDraft, points: "50", reason: "" });
      return transactionDraft.type === "EARN" ? "Points earned." : "Points redeemed.";
    });
  }

  function createCoupon() {
    return run(async () => {
      await apiFetch<Coupon>("/api/v1/loyalty/coupons", {
        method: "POST",
        body: JSON.stringify({
          code: couponDraft.code.trim().toUpperCase(),
          name: couponDraft.name.trim(),
          discount_type: couponDraft.discount_type,
          discount_value: Number(couponDraft.discount_value) || 0,
          minimum_spend_minor: Number(couponDraft.minimum_spend_minor) || 0,
          maximum_redeem_count: couponDraft.maximum_redeem_count
            ? Number(couponDraft.maximum_redeem_count)
            : null,
          usage_limit_per_customer: couponDraft.usage_limit_per_customer
            ? Number(couponDraft.usage_limit_per_customer)
            : null,
          valid_from: new Date(`${couponDraft.valid_from}T00:00:00Z`).toISOString(),
        }),
      });
      setCouponDraft(EMPTY_COUPON);
      return "Coupon created.";
    });
  }

  function redeemCoupon() {
    return run(async () => {
      await apiFetch<CouponRedemption>("/api/v1/loyalty/coupons/redeem", {
        method: "POST",
        body: JSON.stringify({
          coupon_id: redeemDraft.coupon_id,
          order_id: redeemDraft.order_id.trim(),
          discount_amount_minor: Number(redeemDraft.discount_amount_minor) || 0,
        }),
      });
      setRedeemDraft({ ...redeemDraft, order_id: "", discount_amount_minor: "0" });
      return "Coupon redeemed.";
    });
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Loyalty"
        title="Points & coupons"
        sub="Points are earned and redeemed against this membership. Coupon redemption checks validity, global limits and per-customer limits server-side."
        actions={
          <button className="btn secondary" type="button" onClick={() => void load()}>
            Refresh
          </button>
        }
      />

      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}

      {account ? (
        <section className="report-grid" aria-label="Loyalty account">
          <article className="report-card">
            <p className="muted">Points balance</p>
            <p className="stat">{account.points_balance}</p>
            <p className="kpi-foot">{account.tier} tier</p>
          </article>
          <article className="report-card">
            <p className="muted">Total earned</p>
            <p className="stat">{account.total_earned}</p>
            <p className="kpi-foot">Lifetime points</p>
          </article>
          <article className="report-card">
            <p className="muted">Total redeemed</p>
            <p className="stat">{account.total_redeemed}</p>
            <p className="kpi-foot">Points spent</p>
          </article>
          <article className="report-card">
            <p className="muted">Lifetime spend</p>
            <p className="stat">{formatMoney(account.lifetime_spend_minor, "USD")}</p>
            <p className="kpi-foot">Recorded spend</p>
          </article>
        </section>
      ) : null}

      <div className="overview-grid">
        <section className="section-card" aria-labelledby="transactions-title">
          <div className="section-card-head">
            <h3 id="transactions-title">Points transactions</h3>
            <span className="muted text-sm">{transactions.length} recorded</span>
          </div>
          <div className="section-card-body">
            {transactions.length === 0 ? <p className="muted">No transactions yet.</p> : null}
            {transactions.map((transaction) => (
              <div className="audit-row" key={transaction.id}>
                <div>
                  <span className={`audit-action ${transaction.type === "REDEEM" ? "danger" : ""}`}>
                    {transaction.type}
                  </span>
                  <div>
                    {transaction.points} points · {transaction.reason}
                  </div>
                </div>
                <time className="muted text-sm" dateTime={transaction.created_at}>
                  {new Date(transaction.created_at).toLocaleString()}
                </time>
              </div>
            ))}

            {canManage ? (
              <form
                className="stack"
                style={{ marginTop: "var(--space-4)" }}
                onSubmit={(event) => {
                  event.preventDefault();
                  void recordTransaction();
                }}
              >
              <h4 style={{ margin: 0 }}>Record points</h4>
              <div className="grid two">
                <label className="field">
                  Type
                  <select
                    value={transactionDraft.type}
                    onChange={(event) =>
                      setTransactionDraft({ ...transactionDraft, type: event.target.value })
                    }
                  >
                    <option value="EARN">Earn</option>
                    <option value="REDEEM">Redeem</option>
                  </select>
                </label>
                <label className="field">
                  Points
                  <input
                    type="number"
                    min={1}
                    value={transactionDraft.points}
                    onChange={(event) =>
                      setTransactionDraft({ ...transactionDraft, points: event.target.value })
                    }
                    required
                  />
                </label>
              </div>
              <label className="field">
                Reason
                <input
                  value={transactionDraft.reason}
                  onChange={(event) =>
                    setTransactionDraft({ ...transactionDraft, reason: event.target.value })
                  }
                  placeholder="Welcome bonus, redemption at till…"
                  required
                />
              </label>
              <button
                className="btn"
                type="submit"
                disabled={busy || !transactionDraft.reason.trim()}
              >
                Record transaction
              </button>
              </form>
            ) : null}
          </div>
        </section>

        <div className="stack">
          <section className="section-card" aria-labelledby="coupons-title">
            <div className="section-card-head">
              <h3 id="coupons-title">Coupons</h3>
              <span className="muted text-sm">{coupons.length} active</span>
            </div>
            <div className="section-card-body">
              {coupons.length === 0 ? <p className="muted">No coupons yet.</p> : null}
              {coupons.map((coupon) => (
                <div className="list-row" key={coupon.id}>
                  <span>
                    <strong>{coupon.code}</strong> · {coupon.name}
                    <span className="muted text-sm">
                      {" "}
                      · {coupon.discount_type === "PERCENT"
                        ? `${coupon.discount_value}%`
                        : formatMoney(coupon.discount_value, "USD")}
                    </span>
                  </span>
                  <span className="muted text-sm">
                    {coupon.current_redeem_count}
                    {coupon.maximum_redeem_count ? ` / ${coupon.maximum_redeem_count}` : ""} used
                  </span>
                </div>
              ))}
            </div>
          </section>

          {canManage ? (
            <section className="section-card" aria-labelledby="create-coupon-title">
            <div className="section-card-head">
              <h3 id="create-coupon-title">Create coupon</h3>
            </div>
            <div className="section-card-body">
              <form
                className="stack"
                onSubmit={(event) => {
                  event.preventDefault();
                  void createCoupon();
                }}
              >
                <div className="grid two">
                  <label className="field">
                    Code
                    <input
                      value={couponDraft.code}
                      onChange={(event) =>
                        setCouponDraft({ ...couponDraft, code: event.target.value })
                      }
                      required
                    />
                  </label>
                  <label className="field">
                    Name
                    <input
                      value={couponDraft.name}
                      onChange={(event) =>
                        setCouponDraft({ ...couponDraft, name: event.target.value })
                      }
                      required
                    />
                  </label>
                  <label className="field">
                    Type
                    <select
                      value={couponDraft.discount_type}
                      onChange={(event) =>
                        setCouponDraft({ ...couponDraft, discount_type: event.target.value })
                      }
                    >
                      <option value="PERCENT">Percent</option>
                      <option value="FIXED">Fixed amount (minor)</option>
                    </select>
                  </label>
                  <label className="field">
                    Value
                    <input
                      type="number"
                      min={0}
                      value={couponDraft.discount_value}
                      onChange={(event) =>
                        setCouponDraft({ ...couponDraft, discount_value: event.target.value })
                      }
                      required
                    />
                  </label>
                  <label className="field">
                    Valid from
                    <input
                      type="date"
                      value={couponDraft.valid_from}
                      onChange={(event) =>
                        setCouponDraft({ ...couponDraft, valid_from: event.target.value })
                      }
                      required
                    />
                  </label>
                  <label className="field">
                    Minimum spend (minor)
                    <input
                      type="number"
                      min={0}
                      value={couponDraft.minimum_spend_minor}
                      onChange={(event) =>
                        setCouponDraft({
                          ...couponDraft,
                          minimum_spend_minor: event.target.value,
                        })
                      }
                    />
                  </label>
                  <label className="field">
                    Maximum redemptions
                    <input
                      type="number"
                      min={1}
                      value={couponDraft.maximum_redeem_count}
                      onChange={(event) =>
                        setCouponDraft({
                          ...couponDraft,
                          maximum_redeem_count: event.target.value,
                        })
                      }
                    />
                  </label>
                  <label className="field">
                    Per-customer limit
                    <input
                      type="number"
                      min={1}
                      value={couponDraft.usage_limit_per_customer}
                      onChange={(event) =>
                        setCouponDraft({
                          ...couponDraft,
                          usage_limit_per_customer: event.target.value,
                        })
                      }
                    />
                  </label>
                </div>
                <button
                  className="btn"
                  type="submit"
                  disabled={busy || !couponDraft.code.trim() || !couponDraft.name.trim()}
                >
                  Create coupon
                </button>
              </form>
            </div>
            </section>
          ) : null}

          {canRedeem ? (
            <section className="section-card" aria-labelledby="redeem-coupon-title">
            <div className="section-card-head">
              <h3 id="redeem-coupon-title">Redeem coupon</h3>
            </div>
            <div className="section-card-body">
              <form
                className="stack"
                onSubmit={(event) => {
                  event.preventDefault();
                  void redeemCoupon();
                }}
              >
                <label className="field">
                  Coupon
                  <select
                    value={redeemDraft.coupon_id}
                    onChange={(event) =>
                      setRedeemDraft({ ...redeemDraft, coupon_id: event.target.value })
                    }
                    required
                  >
                    <option value="">Select…</option>
                    {coupons.map((coupon) => (
                      <option key={coupon.id} value={coupon.id}>
                        {coupon.code} · {coupon.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  Order ID
                  <input
                    value={redeemDraft.order_id}
                    onChange={(event) =>
                      setRedeemDraft({ ...redeemDraft, order_id: event.target.value })
                    }
                    placeholder="Order UUID"
                    required
                  />
                </label>
                <label className="field">
                  Discount (minor)
                  <input
                    type="number"
                    min={0}
                    value={redeemDraft.discount_amount_minor}
                    onChange={(event) =>
                      setRedeemDraft({
                        ...redeemDraft,
                        discount_amount_minor: event.target.value,
                      })
                    }
                  />
                </label>
                <button
                  className="btn secondary"
                  type="submit"
                  disabled={busy || !redeemDraft.coupon_id || !redeemDraft.order_id.trim()}
                >
                  Redeem coupon
                </button>
              </form>
            </div>
            </section>
          ) : null}
        </div>
      </div>
    </div>
  );
}
