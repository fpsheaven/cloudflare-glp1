export function mount(fetchCount, doc) {
  const timer = setInterval(() => {
    if (doc.visibilityState === 'visible') fetchCount();
  }, 30000);
  return () => clearInterval(timer);
}
