const initData = () => window.Telegram?.WebApp?.initData || '';

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData(),
      ...(options.headers || {}),
    },
  });
  if (!response.ok) throw new Error(await response.text() || `HTTP ${response.status}`);
  return response.json();
}

export const api = {
  me: () => request('/api/me'),
  referrals: () => request('/api/referrals'),
  arena: () => request('/api/public-battle'),
  joinArena: (amount) => request('/api/public-battle/join', { method: 'POST', body: JSON.stringify({ amount }) }),
  share: () => request('/api/share', { method: 'POST' }),
};
