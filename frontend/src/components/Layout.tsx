import { useState } from "react";
import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { PublicLayout } from "./PublicLayout";
import { BrandMark } from "./Brand";
import { useAuth } from "../context/AuthContext";
import { AccountDialog } from "./AccountDialog";
import { Button, ErrorBanner, Loading } from "./ui";

const NAV = [
  { to: "/", label: "Dashboard", icon: "M3 12l9-8 9 8M5 10v10h14V10", end: true },
  { to: "/discover", label: "Discover", icon: "M11 19a8 8 0 100-16 8 8 0 000 16zm10 2l-4.35-4.35" },
  { to: "/datasets", label: "My datasets", icon: "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zm0 0v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3", divider: true },
  { to: "/experiments", label: "Experiments", icon: "M9 3h6M10 3v6l-5 9a2 2 0 002 3h10a2 2 0 002-3l-5-9V3" },
  { to: "/models", label: "Models", icon: "M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3zm0 0v18M4 7.5l8 4.5 8-4.5" },
  { to: "/predictions", label: "Predictions", icon: "M4 19h16M7 15l4-5 3 3 5-7" },
];

// Pages signed-out visitors can open (the API decides what is public).
const PUBLIC_PATHS = [/^\/$/, /^\/discover$/, /^\/datasets\/\d+$/, /^\/experiments\/\d+$/, /^\/experiments\/compare$/];

export function isPublicPath(pathname: string) {
  return PUBLIC_PATHS.some((pattern) => pattern.test(pathname));
}

// Authenticated app shell: redirects to sign-in without a session and waits
// for the API user profile before rendering pages.
export function Layout() {
  const { session, user, initializing, profileError, passwordRecovery, reloadProfile, signOut } = useAuth();
  const [accountOpen, setAccountOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const location = useLocation();

  if (initializing) return <Loading />;
  if (!session) {
    // Signed-out visitors can browse public pages; everything else needs sign-in.
    if (isPublicPath(location.pathname)) return <PublicLayout />;
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  if (passwordRecovery) return <Navigate to="/reset-password" replace />;

  if (!user) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          {profileError ? (
            <>
              <ErrorBanner error={profileError} title="Could not load your account" onRetry={reloadProfile} />
              <Button variant="ghost" onClick={() => void signOut()}>Sign out</Button>
            </>
          ) : (
            <Loading label="Loading your workspace…" />
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <aside className={`sidebar ${navOpen ? "open" : ""}`}>
        <div className="brand">
          <BrandMark />
          <span>MLens</span>
        </div>
        <nav onClick={() => setNavOpen(false)}>
          {NAV.map((item) => (
            <NavLink key={item.to} style={item.divider ? { marginTop: 14 } : undefined} to={item.to} end={item.end} className="nav-link">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d={item.icon} />
              </svg>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="user-switch" onClick={() => setAccountOpen(true)} title="Account settings">
            <span className="avatar">{user.name[0]?.toUpperCase() ?? "?"}</span>
            <span className="user-meta">
              <span className="user-name">{user.name}</span>
              <span className="user-email">{user.email}</span>
            </span>
          </button>
          <button className="signout-btn" onClick={() => void signOut()}>
            Sign out
          </button>
        </div>
      </aside>

      <div className="main">
        <div className="topbar">
          <button className="icon-btn" onClick={() => setNavOpen((v) => !v)} aria-label="Menu">
            ☰
          </button>
          <span className="topbar-title">MLens</span>
        </div>
        <main className="content" key={location.pathname}>
          <Outlet />
        </main>
      </div>

      {accountOpen && <AccountDialog onClose={() => setAccountOpen(false)} />}
    </div>
  );
}
