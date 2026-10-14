/** Lazy per-session history cache; refresh invalidates it after prescription changes. */
export function createHistoryLoader<T>(fetchHistory: (id: string) => Promise<T[]>) {
  const cache = new Map<string, Promise<T[]>>();
  const get = (id: string): Promise<T[]> => {
    const existing = cache.get(id);
    if (existing) return existing;
    const pending = fetchHistory(id).catch(error => {
      if (cache.get(id) === pending) cache.delete(id);
      throw error;
    });
    cache.set(id, pending);
    return pending;
  };
  return {
    get,
    clear: () => cache.clear(),
    async all(ids: string[]): Promise<Record<string, T[]>> {
      const result: Record<string, T[]> = {};
      let next = 0;
      await Promise.all(Array.from({ length: Math.min(4, ids.length) }, async () => {
        while (next < ids.length) {
          const id = ids[next++];
          result[id] = await get(id);
        }
      }));
      return result;
    },
  };
}
