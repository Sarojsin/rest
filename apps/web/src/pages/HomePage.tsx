import { Link } from "react-router-dom";
import { BRAND_NAME, monogram } from "../lib/brand";
import { DEMO_ACCOUNTS, DEMO_ENABLED, DEMO_HINT, demoLoginHref } from "../lib/demo";

export default function HomePage() {
  return (
    <div className="landing shell" data-theme="customer">
      <a className="skip-link" href="#demo">
        Skip to content
      </a>
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

      <section id="pricing" className="landing-section" aria-labelledby="pricing-title">
        <div className="section-head">
          <p className="kicker dark">Pricing</p>
          <h2 id="pricing-title">Simple, transparent pricing</h2>
          <p className="muted">
            Clear tiered pricing that grows with your restaurant.
          </p>
        </div>
        <div className="grid three" aria-label="Tier pricing cards">
          <article className="card pricing-card">
            <div className="pricing-header">
              <span className="popular-tag" style={{display: "none", backgroundColor: "var(--accent)", color: "var(--primary)"}}>Most Popular</span>
              <h3>Basic</h3>
              <p className="pricing-price">$29/month</p>
            </div>
            <ul className="pricing-features">
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Single branch/restaurant</li>
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Up to 5 tables</li>
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>QR code ordering</li>
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Table management</li>
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Basic dashboard</li>
            </ul>
          </article>
          <article className="card pricing-card">
            <div className="pricing-header">
              <span className="popular-tag" style={{display: "block", backgroundColor: "var(--accent)", color: "var(--primary)"}}>Most Popular</span>
              <h3>Professional</h3>
              <p className="pricing-price">$79/month</p>
            </div>
            <ul className="pricing-features">
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Unlimited branches</li>
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Branch-specific menus</li>
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Subdomain configuration</li>
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Audit viewer</li>
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Suspend/reactivate</li>
            </ul>
          </article>
          <article className="card pricing-card">
            <div className="pricing-header">
              <span className="popular-tag" style={{display: "none", backgroundColor: "var(--accent)", color: "var(--primary)"}}>Custom</span>
              <h3>Enterprise</h3>
              <p className="pricing-price">Custom</p>
            </div>
            <ul className="pricing-features">
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Unlimited branches</li>
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Custom branding</li>
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>API access</li>
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Priority support</li>
              <li className="feature-item"><span aria-hidden="true" className="check-icon">✓</span>Advanced analytics</li>
            </ul>
          </article>
        </div>
      </section>

      <section id="testimonials" className="landing-section" aria-labelledby="testimonials-title">
        <div className="section-head">
          <p className="kicker dark">Testimonials</p>
          <h2 id="testimonials-title">What restaurant owners say</h2>
        </div>
        <div className="grid three" aria-label="Customer testimonials">
          <article className="card testimonial-card">
            <div className="testimonial-text">
              <p>The QR ordering system has transformed our service. Guests love it and our kitchen runs smoother.</p>
              <div className="rating">
                {[1, 2, 3, 4, 5].map((value) => (
                  <span key={value} className={value <= 5 ? "star filled" : "star empty"} aria-hidden={true}>
                    ★
                  </span>
                ))}
              </div>
              <div className="author">
                <strong>Maria S.</strong>
                <span>Restaurant Owner</span>
              </div>
            </div>
          </article>
          <article className="card testimonial-card">
            <div className="testimonial-text">
              <p>Professional tier's branch management is exactly what we needed for our growing chain.</p>
              <div className="rating">
                {[1, 2, 3, 4, 5].map((value) => (
                  <span key={value} className={value <= 4 ? "star filled" : "star empty"} aria-hidden={true}>
                    ★
                  </span>
                ))}
              </div>
              <div className="author">
                <strong>James T.</strong>
                <span>Restaurant Manager</span>
              </div>
            </div>
          </article>
          <article className="card testimonial-card">
            <div className="testimonial-text">
              <p>Real-time order tracking has reduced kitchen stress significantly.</p>
              <div className="rating">
                {[1, 2, 3, 4, 5].map((value) => (
                  <span key={value} className={value <= 5 ? "star filled" : "star empty"} aria-hidden={true}>
                    ★
                  </span>
                ))}
              </div>
              <div className="author">
                <strong>Patricia K.</strong>
                <span>Head Chef</span>
              </div>
            </div>
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
