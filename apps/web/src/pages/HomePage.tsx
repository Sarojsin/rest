import { Link } from "react-router-dom";
import { BRAND_NAME, monogram } from "../lib/brand";
import { DEMO_ACCOUNTS, DEMO_ENABLED, DEMO_HINT, demoLoginHref } from "../lib/demo";

export default function HomePage() {
  return (
    <div className="landing shell" data-theme="customer">
      <header className="topbar">
        <Link className="brand" to="/">
          <div className="mark">{monogram(BRAND_NAME)}</div>
          <div>
            <h1>{BRAND_NAME}</h1>
            <p>Dine-in, without the wait</p>
          </div>
        </Link>
        <nav className="nav" aria-label="Main">
          <a href="#how">How it works</a>
          <Link to="/login" className="nav-cta">Staff sign in</Link>
        </nav>
      </header>

      <section className="hero landing-hero">
        <p className="kicker">Table-side ordering · No app needed</p>
        <h2>
          A full evening at your table,
          <br />
          without waving anyone down.
        </h2>
        <p className="hero-copy">
          Scan the badge on your table, order at your own pace, and follow every
          course from the kitchen to your seat. One shared bill, settled whenever
          you are ready.
        </p>
        <div className="hero-actions">
          {DEMO_ENABLED ? <a className="btn btn-amber btn-lg" href="#demo">Try the live demo</a> : null}
          <a className="btn btn-hero-ghost btn-lg" href="#how">See how it works</a>
        </div>
        <ul className="hero-meta">
          <li>Guests order from their own phone</li>
          <li>Staff confirm every QR order</li>
          <li>Live course tracking</li>
        </ul>
      </section>

      <section id="how" className="landing-section" aria-labelledby="scan-title">
        <div className="section-head">
          <p className="kicker dark">Getting started</p>
          <h2 id="scan-title">No app, no sign-up, no queueing</h2>
          <p className="muted">
            Every table carries a QR badge. Scan it and the menu for your exact table opens
            instantly — guests never create an account, and orders are tagged to the right
            table automatically.
          </p>
        </div>
        <div className="grid three path-grid">
          <article className="card path-card">
            <p className="path-step" aria-hidden="true">01</p>
            <h3>Scan the badge on your table</h3>
            <p className="muted">
              Each table has its own code, printed by the restaurant. There is nothing to
              download — any phone camera opens the menu.
            </p>
          </article>
          <article className="card path-card">
            <p className="path-step" aria-hidden="true">02</p>
            <h3>Order at your own pace</h3>
            <p className="muted">
              Add courses whenever you like. Your order is confirmed by staff before the
              kitchen sees it, so nothing gets lost.
            </p>
          </article>
          <article className="card path-card">
            <p className="path-step" aria-hidden="true">03</p>
            <h3>Follow and settle the bill</h3>
            <p className="muted">
              A private status link tracks every course. When you are ready, the shared
              table bill is settled with staff.
            </p>
          </article>
        </div>
      </section>

      {DEMO_ENABLED ? (
        <section id="demo" className="landing-section" aria-labelledby="demo-title">
          <div className="section-head">
            <p className="kicker dark">Live demo</p>
            <h2 id="demo-title">Try it right now</h2>
            <p className="muted">
              One tap signs you in as any staff role, with a working dining room behind it —
              tables, QR orders, kitchen tickets, and bills.
            </p>
          </div>
          <div className="grid three path-grid">
            {DEMO_ACCOUNTS.map((account) => (
              <article key={account.role} className="card path-card">
                <p className="path-step" aria-hidden="true">{account.role}</p>
                <h3>Sign in as {account.role.toLowerCase()}</h3>
                <p className="muted">{DEMO_HINT[account.role]}</p>
                <Link className="btn btn-amber demo-cta" to={demoLoginHref(account)}>
                  Open the demo <span aria-hidden="true">→</span>
                </Link>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="landing-section">
        <div className="card closing">
          <div>
            <h2>Bring the evening to your tables.</h2>
            <p className="muted">
              Print the QR badges, stick them on the tables, and guests are ordering in
              seconds. Staff manage menus, tables, and payments from the workspace.
            </p>
          </div>
          <Link className="btn btn-amber btn-lg" to="/login">Staff sign in</Link>
        </div>
      </section>

      <footer className="landing-footer">
        <p className="muted">
          {BRAND_NAME} — waiter, kitchen, cashier and manager share one source of
          truth. Guests never need to install anything.
        </p>
      </footer>
    </div>
  );
}
