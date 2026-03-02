import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

export function Shell({ children }: { children: ReactNode }) {
  const location = useLocation();

  return (
    <>
      <header className="shell-header">
        <div className="container">
          <h1>
            <Link to="/" style={{ color: "inherit", textDecoration: "none" }}>
              <span>databricks-agents</span> dashboard
            </Link>
          </h1>
          <nav className="nav-links">
            <Link
              to="/"
              style={
                location.pathname === "/"
                  ? { color: "var(--text)" }
                  : undefined
              }
            >
              Agents
            </Link>
            <Link
              to="/lineage"
              style={
                location.pathname === "/lineage"
                  ? { color: "var(--text)" }
                  : undefined
              }
            >
              Lineage
            </Link>
            <a href="/health" target="_blank" rel="noreferrer">
              Health
            </a>
          </nav>
        </div>
      </header>
      <div className="container">{children}</div>
    </>
  );
}
