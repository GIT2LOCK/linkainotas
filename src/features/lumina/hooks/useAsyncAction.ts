import { useCallback, useRef, useState } from "react";

export function useAsyncAction<TArgs extends unknown[], TResult>(
  action: (...args: TArgs) => Promise<TResult>,
) {
  const actionRef = useRef(action);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TResult | null>(null);

  actionRef.current = action;

  const run = useCallback(async (...args: TArgs) => {
    setLoading(true);
    setError(null);

    try {
      const result = await actionRef.current(...args);
      setData(result);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, error, loading, run };
}
