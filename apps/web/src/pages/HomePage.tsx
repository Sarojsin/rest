import { Link } from "react-router-dom";

const DEMO_TABLES = [
  { code: "T1", token: "table-harbor-1-alpha", name: "Table 1", seats: 2 },
  { code: "T2", token: "table-harbor-2-bravo", name: "Table 2", seats: 4 },
  { code: "T3", token: "table-harbor-3-charlie", name: "Table 3", seats: 2 },
  { code: "T4", token: "table-harbor-4-delta", name: "Table 4", seats: 6 },
  { code: "T5", token: "table-harbor-5-echo", name: "Table 5", seats: 4 },
  { code: "T6", token: "table-harbor-6-foxtrot", name: "Table 6", seats: 8 },
];

const PATHS = [
  {
    step: "01",
    title: "Order as the evening flows",
    copy: (
      <>
        No waving, no waiting for a pen and pad. Guests scan their table once, order
        another round while the conversation keeps going, and staff confirm every
        request before it reaches the kitchen.
      </>
    ),
  },
  {
    step: "02",
    title: "Watch every course, live",
    copy: (
      <>
        Each order gets a private status link — from <em>submitted</em> to
        <em> confirmed</em> and <em>served</em>. Guests follow their plates in real
        time instead of looking around for an update.
      </>
    ),
  },
  {
    step: "03",
    title: "Settle the bill on your schedule",
    copy: (
      <>
        One shared bill per table, kept accurate by the same records the kitchen and
        cashier see. When the evening winds down, payment is a single unhurried step.
      </>
    ),
  },
];

export default function HomePage() {
  return (
    <div className="landing shell" data-theme="customer">
      <header className="topbar">
        <Link className="brand" to="/">
          <div className="mark">HT</div>
          <div>
            <h1>Harbor Table</h1>
            <p>Dine-in, without the wait</p>
          </div>
        </Link>
        <nav className="nav" aria-label="Main">
          <a href="#tables">Tables</a>
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
          <a className="btn btn-amber btn-lg" href="#tables">Choose your table</a>
          <a className="btn btn-hero-ghost btn-lg" href="#how">See how it works</a>
        </div>
        <ul className="hero-meta">
          <li>Guests order from their own phone</li>
          <li>Staff confirm every QR order</li>
          <li>Live course tracking</li>
        </ul>
      </section>

      <section id="tables" className="landing-section" aria-labelledby="tables-title">
        <div className="section-head">
          <p className="kicker dark">Tonight&apos;s dining room</p>
          <h2 id="tables-title">Find your table</h2>
          <p className="muted">
            Sitting down with us? Open your table below — the menu opens exactly as
            it does after scanning the QR badge on the table.
          </p>
        </div>
        <div className="grid tables table-grid">
          {DEMO_TABLES.map((table) => (
            <article key={table.code} className="table-card">
              <div className="table-card-top">
                <span className="badge open">Open</span>
                <span className="muted table-seats">{table.seats} seats</span>
              </div>
              <h3>{table.name}</h3>
              <p className="muted table-code">{table.code}</p>
              <Link className="table-order-link" to={`/t/${table.token}`}>
                Order here <span aria-hidden="true">→</span>
                <span className="visually-hidden">— open menu for {table.name}</span>
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section id="how" className="landing-section" aria-labelledby="how-title">
        <div className="section-head">
          <p className="kicker dark">The guest experience</p>
          <h2 id="how-title">Keep the evening moving</h2>
        </div>
        <div className="grid three path-grid">
          {PATHS.map((path) => (
            <article key={path.step} className="card path-card">
              <p className="path-step" aria-hidden="true">{path.step}</p>
              <h3>{path.title}</h3>
              <p className="muted">{path.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section">
        <div className="card closing">
          <div>
            <h2>Your table is ready.</h2>
            <p className="muted">
              Pick a table above to browse the menu as a guest — or sign in as staff
              to run the dining room from the other side.
            </p>
          </div>
          <a className="btn btn-amber btn-lg" href="#tables">Back to tables</a>
        </div>
      </section>

      <footer className="landing-footer">
        <p className="muted">
          Harbor Table — waiter, kitchen, cashier and manager share one source of
          truth. Guests never need to install anything.
        </p>
      </footer>
    </div>
  );
}
