(() => {
  const $ = id => document.getElementById(id);
  const remove = el => el?.remove();

  // Only the free case remains in the product UI.
  document.querySelectorAll('.case').forEach(remove);
  document.querySelectorAll('.section-title').forEach(el => {
    const title = el.querySelector('h2')?.textContent?.trim() || '';
    if (title === 'Коллекции' || title === 'Мини-игры') remove(el);
  });
  document.querySelectorAll('.cards').forEach(el => {
    const text = el.textContent || '';
    if (text.includes('Slots') || text.includes('Roulette')) remove(el);
  });

  // Remove contests and legacy game pages/nav entries.
  remove($('contests')); remove($('battles')); remove($('crash'));
  document.querySelectorAll('.nav button').forEach(btn => {
    const text = btn.textContent || '';
    if (text.includes('Конкурсы')) remove(btn);
  });
  const nav = document.querySelector('.nav');
  if (nav) nav.style.gridTemplateColumns = 'repeat(4,1fr)';

  const hero = document.querySelector('.hero p');
  if (hero) hero.textContent = 'Бесплатный ежедневный подарок. Пополняйте баланс отдельно в Telegram Stars или TON.';

  // Reliable Telegram Stars top-up.
  window.payStars = async () => {
    const raw = prompt('Сколько Stars пополнить?', '100');
    if (raw === null) return;
    const amount = Number.parseInt(raw, 10);
    if (!Number.isInteger(amount) || amount <= 0) return window.toast?.('Введите корректное количество Stars');
    const d = await window.api?.('/api/stars/invoice', {
      method: 'POST', body: JSON.stringify({ amount })
    });
    if (!d?.ok) return window.toast?.(d?.message || 'Не удалось создать счёт Stars');
    if (window.tg?.openInvoice) {
      window.tg.openInvoice(d.invoice_link, status => {
        if (status === 'paid') {
          window.toast?.(`✅ Оплачено ${amount} ⭐`);
          setTimeout(() => window.loadMe?.(), 1200);
        }
      });
    } else {
      location.href = d.invoice_link;
    }
  };

  // TON top-up: create a unique transfer, open wallet, then verify tx hash on server.
  window.tonTopup = async () => {
    const raw = prompt('Сколько TON пополнить?', '0.1');
    if (raw === null) return;
    const amount = Number.parseFloat(raw);
    if (!Number.isFinite(amount) || amount <= 0) return window.toast?.('Введите корректную сумму TON');
    const d = await window.api?.('/api/ton/deposit', {
      method: 'POST', body: JSON.stringify({ amount })
    });
    if (!d?.ok) return window.toast?.(d?.message || 'TON-пополнение недоступно');
    if (window.tg?.openLink) window.tg.openLink(d.ton_uri); else location.href = d.ton_uri;
    setTimeout(async () => {
      const tx = prompt('После перевода вставьте hash TON-транзакции для проверки:');
      if (!tx) return;
      const c = await window.api?.('/api/ton/confirm', {
        method: 'POST', body: JSON.stringify({ tx_hash: tx.trim() })
      });
      window.toast?.(c?.ok ? `✅ Зачислено ${c.credited_ton} TON` : (c?.message || 'Транзакция пока не найдена'));
      if (c?.ok) window.loadMe?.();
    }, 2500);
  };

  // Refresh after DOM is ready because the legacy inline script builds some blocks later.
  setTimeout(() => {
    document.querySelectorAll('.case').forEach(remove);
    document.querySelectorAll('.cards').forEach(el => {
      const text = el.textContent || '';
      if (text.includes('Slots') || text.includes('Roulette')) remove(el);
    });
    remove($('contests')); remove($('battles')); remove($('crash'));
    document.querySelectorAll('.nav button').forEach(btn => {
      if ((btn.textContent || '').includes('Конкурсы')) remove(btn);
    });
    if (nav) nav.style.gridTemplateColumns = 'repeat(4,1fr)';
  }, 50);
})();
