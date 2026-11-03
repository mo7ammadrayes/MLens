import { useState, type FormEvent, type ReactNode } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { BrandMark } from "../components/Brand";
import { Alert, Button, ErrorBanner, Field, Loading } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { supabase, supabaseConfigured } from "../lib/supabase";

function AuthShell({ title, subtitle, children, footer }: { title: string; subtitle?: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="auth-page">
      <div className="auth-card">
        <Link to="/" className="brand auth-brand">
          <BrandMark size={28} />
          <span>MLens</span>
        </Link>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
        {!supabaseConfigured && (
          <Alert tone="warning">
            Supabase is not configured. Set <span className="mono">VITE_SUPABASE_URL</span> and{" "}
            <span className="mono">VITE_SUPABASE_PUBLISHABLE_KEY</span> in <span className="mono">frontend/.env</span> and
            restart <span className="mono">npm run dev</span>.
          </Alert>
        )}
        {children}
        {footer && <div className="auth-footer">{footer}</div>}
      </div>
    </div>
  );
}

function friendly(message: string): string {
  if (/invalid login credentials/i.test(message)) return "Incorrect email or password.";
  if (/email not confirmed/i.test(message)) return "Confirm your email first — check your inbox for the link.";
  return message;
}

export function SignIn() {
  const { session, initializing } = useAuth();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  if (initializing) return <Loading />;
  if (session) return <Navigate to={from} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    const { error } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
    setBusy(false);
    if (error) setError(friendly(error.message));
  }

  return (
    <AuthShell
      title="Sign in"
      subtitle="Welcome back. Sign in to your workspace."
      footer={<>No account? <Link to="/signup" state={{ from }}>Create one</Link></>}
    >
      <form onSubmit={submit} className="stack-sm">
        <Field label="Email" htmlFor="email">
          <input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </Field>
        <Field label={<span className="label-row">Password <Link to="/forgot-password" className="small">Forgot?</Link></span>} htmlFor="password">
          <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </Field>
        <ErrorBanner error={error} />
        <Button type="submit" variant="primary" loading={busy} className="btn-block">
          Sign in
        </Button>
      </form>
    </AuthShell>
  );
}

export function SignUp() {
  const { session } = useAuth();
  const location = useLocation();
  // Return visitors to the page that asked them to sign up.
  const from = (location.state as { from?: string } | null)?.from ?? "/";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  if (session) return <Navigate to={from} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (password.length < 8) {
      setError("Use at least 8 characters.");
      return;
    }
    setBusy(true);
    setError(undefined);
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: {
        data: { name: name.trim() },
        emailRedirectTo: `${window.location.origin}${from}`,
      },
    });
    setBusy(false);
    if (error) return setError(friendly(error.message));
    // With email confirmation on, no session is returned until the link is clicked.
    if (!data.session) setSent(true);
  }

  if (sent)
    return (
      <AuthShell title="Check your email" footer={<Link to="/login">Back to sign in</Link>}>
        <Alert tone="success">
          We sent a confirmation link to <strong>{email}</strong>. Open it to activate your account, then sign in.
        </Alert>
      </AuthShell>
    );

  return (
    <AuthShell
      title="Create account"
      subtitle="Your datasets, experiments and models are private to your account."
      footer={<>Already have an account? <Link to="/login" state={{ from }}>Sign in</Link></>}
    >
      <form onSubmit={submit} className="stack-sm">
        <Field label="Name" htmlFor="name">
          <input id="name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
        </Field>
        <Field label="Email" htmlFor="email">
          <input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field label="Password" htmlFor="password" hint="At least 8 characters.">
          <input id="password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </Field>
        <ErrorBanner error={error} />
        <Button type="submit" variant="primary" loading={busy} className="btn-block">
          Create account
        </Button>
      </form>
    </AuthShell>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    setBusy(false);
    if (error) setError(friendly(error.message));
    else setSent(true);
  }

  return (
    <AuthShell title="Reset password" subtitle="We'll email you a link to choose a new password." footer={<Link to="/login">Back to sign in</Link>}>
      {sent ? (
        <Alert tone="success">If an account exists for <strong>{email}</strong>, a reset link is on its way.</Alert>
      ) : (
        <form onSubmit={submit} className="stack-sm">
          <Field label="Email" htmlFor="email">
            <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
          </Field>
          <ErrorBanner error={error} />
          <Button type="submit" variant="primary" loading={busy} className="btn-block">
            Send reset link
          </Button>
        </form>
      )}
    </AuthShell>
  );
}

export function ResetPassword() {
  const { session, initializing, clearPasswordRecovery } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  if (initializing) return <Loading />;
  if (!session)
    return (
      <AuthShell title="Link expired" footer={<Link to="/forgot-password">Request a new link</Link>}>
        <p className="muted">This reset link is invalid or has expired.</p>
      </AuthShell>
    );

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (password.length < 8) return setError("Use at least 8 characters.");
    setBusy(true);
    setError(undefined);
    const { error } = await supabase.auth.updateUser({ password });
    setBusy(false);
    if (error) return setError(friendly(error.message));
    clearPasswordRecovery();
    navigate("/", { replace: true });
  }

  return (
    <AuthShell title="Choose a new password">
      <form onSubmit={submit} className="stack-sm">
        <Field label="New password" htmlFor="password" hint="At least 8 characters.">
          <input id="password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required autoFocus />
        </Field>
        <ErrorBanner error={error} />
        <Button type="submit" variant="primary" loading={busy} className="btn-block">
          Update password
        </Button>
      </form>
    </AuthShell>
  );
}
