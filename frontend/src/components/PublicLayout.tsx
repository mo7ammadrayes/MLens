import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Brand } from "./Brand";

export function scrollToHowItWorks() {
  const target = document.getElementById("how-it-works");
  if (!target) return;
  const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  target.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
  history.replaceState(null, "", "/#how-it-works");
}

// Shell for signed-out visitors: landing page, Discover and public detail pages.
export function PublicLayout() {
  const { pathname } = useLocation();
  const isLanding = pathname === "/";

  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-wrap lp-nav-inner">
          <Brand />
          <nav className="lp-nav-links">
            <NavLink
              to="/discover"
              end
              onClick={(e) => pathname === "/discover" && e.preventDefault()}
              aria-disabled={pathname === "/discover" || undefined}
            >
              Discover
            </NavLink>
            <Link
              to="/#how-it-works"
              className="lp-hide-sm"
              onClick={(e) => {
                // Already on the landing page: scroll instead of re-navigating.
                if (pathname === "/") {
                  e.preventDefault();
                  scrollToHowItWorks();
                }
              }}
            >
              How it works
            </Link>
            <Link to="/login" state={{ from: pathname }}>Sign in</Link>
            <Link to="/signup" className="lp-btn lp-btn-dark lp-btn-sm">Get started</Link>
          </nav>
        </div>
      </header>
      {isLanding ? (
        <Outlet />
      ) : (
        <main className="lp-wrap lp-page" key={pathname}>
          <Outlet />
        </main>
      )}
      <footer className="lp-footer">
        <div className="lp-wrap lp-footer-inner">
          <Brand />
          <span>Discover, train, compare, and understand.</span>
        </div>
      </footer>
    </div>
  );
}
