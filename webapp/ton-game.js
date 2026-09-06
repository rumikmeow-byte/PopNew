// GiftsEZZ compatibility patch: use the server-generated TON transfer URI so the unique
// deposit comment is preserved and can be verified on-chain by the backend.
(() => {
  const boot = () => {
    const button = document.getElementById('createTon');
    if (!button || button.dataset.giftsEzzPatched) return;
    button.dataset.giftsEzzPatched = '1';
    button.onclick = async () => {
      try {
        const tg = window.Telegram?.WebApp;
        const amount = Number(document.querySelector('[data-ton].active')?.dataset.ton || 0.25);
        const headers = {'Content-Type':'application/json'};
        if (tg?.initData) headers['X-Telegram-Init-Data'] = tg.initData;
        const r = await fetch('/api/ton/deposit', {method:'POST', headers, body:JSON.stringify({amount})});
        const d = await r.json();
        if (!d.ok) throw new Error(d.message || 'TON-платёж не создан');
        const info = document.getElementById('tonDepositInfo');
        if (info) info.textContent = `Отправьте ${d.amount} TON на ${d.destination}. Комментарий: ${d.comment}`;
        if (tg?.openLink) tg.openLink(d.ton_uri);
        else window.location.href = d.ton_uri;
      } catch (e) {
        if (window.toast) window.toast(e.message || 'TON-платёж не создан');
      }
    };
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(boot, 50));
  else setTimeout(boot, 50);
})();
