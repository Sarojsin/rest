import { Link } from "react-router-dom";

const DEMO_TABLES = [
  { code: "T1", token: "table-harbor-1-alpha", name: "Table 1" },
  { code: "T2", token: "table-harbor-2-bravo", name: "Table 2" },
  { code: "T3", token: "table-harbor-3-charlie", name: "Table 3" },
  { code: "T4", token: "table-harbor-4-delta", name: "Table 4" },
  { code: "T5", token: "table-harbor-5-echo", name: "Table 5" },
  { code: "T6", token: "table-harbor-6-foxtrot", name: "Table 6" },
];

export default function HomePage() {
  return (
    <div className="shell">
      <header className="topbar">
        <Link className="brand" to="/">
          <div className="mark">HT</div>
          <div>
            <h1>Harbor Table</h1>
            <p>Dine-in restaurant operations</p>
          </div>
        </Link>
        <nav className="nav">
          <Link to="/login">Staff sign in</Link>
        </nav>
      </header>

      <section className="hero">
        <div className="kicker">Pilot restaurant</div>
        <h2>One kitchen, one bill, one source of truth.</h2>
        <p>
          Guests scan a table QR and order from the browser. Staff confirm every QR request
          before it reaches the kitchen. Waiter, kitchen, cashier, and manager share the same records.
        </p>
      </section>

      <div className="grid two">
        <article className="card">
          <h3>Guest QR ordering</h3>
          <p className="muted">
            Open a table menu as a guest would after scanning a printed QR code. Submitted orders
            stay pending until a waiter accepts them.
          </p>
          <div className="grid tables" style={{ marginTop: 16 }}>
            {DEMO_TABLES.map((table) => (
              <Link key={table.code} className="card table-tile AVAILABLE" to={`/t/${table.token}`}>
                <strong>{table.name}</strong>
                <span className="muted">{table.code}</span>
              </Link>
            ))}
          </div>
        </article>
        <article className="card">
          <h3>Staff demo accounts</h3>
          <p className="muted">Use these seeded logins. Password pattern is HarborRole!1</p>
          <ul>
            <li>owner@harbor.example / HarborOwner!1</li>
            <li>manager@harbor.example / HarborManager!1</li>
            <li>waiter@harbor.example / HarborWaiter!1</li>
            <li>kitchen@harbor.example / HarborKitchen!1</li>
            <li>cashier@harbor.example / HarborCashier!1</li>
          </ul>
          <Link className="btn" to="/login">Open staff app</Link>
        </article>
      </div>
    </div>
  );
}
