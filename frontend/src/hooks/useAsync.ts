import { useCallback, useEffect, useRef, useState } from "react";

export interface AsyncState<T> {
  data: T | undefined;
  error: Error | undefined;
  loading: boolean;
  reload: () => void;
  setData: (data: T) => void;
}

// Runs a loader on mount and whenever deps change.
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(undefined);
    loaderRef
      .current()
      .then((value) => active && setData(value))
      .catch((err: Error) => active && setError(err))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload, setData };
}

// Wraps a user-triggered action (button click, form submit).
export function useAction<A extends unknown[], T>(action: (...args: A) => Promise<T>) {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<Error>();
  const [result, setResult] = useState<T>();

  const run = useCallback(
    async (...args: A): Promise<T | undefined> => {
      setRunning(true);
      setError(undefined);
      try {
        const value = await action(...args);
        setResult(value);
        return value;
      } catch (err) {
        setError(err as Error);
        return undefined;
      } finally {
        setRunning(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [action],
  );

  const reset = useCallback(() => {
    setError(undefined);
    setResult(undefined);
  }, []);

  return { run, running, error, result, reset };
}
