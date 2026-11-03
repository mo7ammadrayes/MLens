import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ButtonLink, EmptyState } from "./components/ui";
import { AuthProvider } from "./context/AuthContext";
import { ForgotPassword, ResetPassword, SignIn, SignUp } from "./pages/Auth";
import { Compare } from "./pages/Compare";
import { Dashboard } from "./pages/Dashboard";
import { DatasetDetail } from "./pages/DatasetDetail";
import { Datasets } from "./pages/Datasets";
import { Discover } from "./pages/Discover";
import { Landing } from "./pages/Landing";
import { useAuth } from "./context/AuthContext";
import { ExperimentDetail } from "./pages/ExperimentDetail";
import { Experiments } from "./pages/Experiments";
import { Models } from "./pages/Models";
import { NewExperiment } from "./pages/NewExperiment";
import { Predictions } from "./pages/Predictions";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="login" element={<SignIn />} />
          <Route path="signup" element={<SignUp />} />
          <Route path="forgot-password" element={<ForgotPassword />} />
          <Route path="reset-password" element={<ResetPassword />} />
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="datasets" element={<Datasets />} />
            <Route path="datasets/:datasetId" element={<DatasetDetail />} />
            <Route path="experiments" element={<Experiments />} />
            <Route path="experiments/new" element={<NewExperiment />} />
            <Route path="experiments/compare" element={<Compare />} />
            <Route path="experiments/:experimentId" element={<ExperimentDetail />} />
            <Route path="models" element={<Models />} />
            <Route path="predictions" element={<Predictions />} />
            <Route path="discover" element={<Discover />} />
            <Route path="explore" element={<Navigate to="/discover" replace />} />
            <Route
              path="*"
              element={<EmptyState title="Page not found" action={<ButtonLink to="/">Back to dashboard</ButtonLink>} />}
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

// Signed-out visitors get the landing page.
function Home() {
  return useAuth().session ? <Dashboard /> : <Landing />;
}
