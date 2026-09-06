(() => {
  const $ = id => document.getElementById(id);
  const remove = el => el?.remove();
  const tgApp = window.Telegram?.WebApp;
  const headers = () => ({'Content-Type':'application/json','X-Telegram-Init-Data':tgApp?.initData||''});
  const api = async (url, options={}) => {
    try {
      const r = await fetch(url, {...options, headers:{...headers(),...(options.headers||{})}, cache:'no-store'});
      return await r.json();
    } catch (_) { return null; }
  };
  const reloadBalance = async () => {
    const d = await api('/api/me');
    if (!d?.profile) return;
    $('stars') && ($('stars').textContent = d.profile.balance || 0);
    $('ton') && ($('ton').textContent = Number(d.profile.ton_balance || 0).toFixed(2));
    $('pStars') && ($('pStars').textContent = d.profile.balance || 0);
  };

  function cleanUI() {
    document.querySelectorAll('.case').forEach(remove);
    document.querySelectorAll('.section-title').forEach(el => {
      const title = el.querySelector('h2')?.textContent?.trim() || '';
      if (title === 'Коллекции' || title === 'Мини-игры') remove(el);
    });
    document.querySelectorAll('.cards').forEach(el => {
      const text = el.textContent || '';
      if (text.includes('Slots') || text.includes('Roulette')) remove(el);
    });
    remove($('contests')); remove($('battles')); remove($('crash'));
    document.querySelectorAll('.nav button').forEach(btn => {
      if ((btn.textContent || '').includes('Конкурсы')) remove(btn);
    });
    const nav = document.querySelector('.nav');
    if (nav) nav.style.gridTemplateColumns = 'repeat(4,1fr)';
    const hero = document.querySelector('.hero p');
    if (hero) hero.textContent = 'Бесплатный ежедневный подарок. Пополняйте баланс отдельно в Telegram Stars или TON.';
  }

  window.payStars = async () => {
    const raw = prompt('Сколько Stars пополнить?', '100');
    if (raw === null) return;
    const amount = Number.parseInt(raw, 10);
    if (!Number.isInteger(amount) || amount <= 0) return window.toast?.('Введите корректное количество Stars');
    const d = await api('/api/stars/invoice', {method:'POST', body:JSON.stringify({amount})});
    if (!d?.ok) return window.toast?.(d?.message || 'Не удалось создать счёт Stars');
    if (tgApp?.openInvoice) {
      tgApp.openInvoice(d.invoice_link, status => {
        if (status === 'paid') {
          window.toast?.(`✅ Оплачено ${amount} ⭐`);
          setTimeout(reloadBalance, 1200);
        }
      });
    } else location.href = d.invoice_link;
  };

  window.tonTopup = async () => {
    const raw = prompt('Сколько TON пополнить?', '0.1');
    if (raw === null) return;
    const amount = Number.parseFloat(raw);
    if (!Number.isFinite(amount) || amount <= 0) return window.toast?.('Введите корректную сумму TON');
    const d = await api('/api/ton/deposit', {method:'POST', body:JSON.stringify({amount})});
    if (!d?.ok) return window.toast?.(d?.message || 'TON-пополнение недоступно');
    if (tgApp?.openLink) tgApp.openLink(d.ton_uri); else location.href = d.ton_uri;
    setTimeout(async () => {
      const tx = prompt('После перевода вставьте hash TON-транзакции для проверки:');
      if (!tx) return;
      const c = await api('/api/ton/confirm', {method:'POST', body:JSON.stringify({tx_hash:tx.trim()})});
      window.toast?.(c?.ok ? `✅ Зачислено ${c.credited_ton} TON` : (c?.message || 'Транзакция пока не найдена'));
      if (c?.ok) reloadBalance();
    }, 2500);
  };

  cleanUI();
  setTimeout(cleanUI, 100);
})();
