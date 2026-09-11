(() => {
  'use strict';

  const KEY = 'giftsmms-demo-v3';
  const DEFAULT_STATE = { balance: 1250, wins: 0, referrals: 3 };
  const screen = document.getElementById('screen');
  const toastEl = document.getElementById('toast');
  let state;

  try { state = JSON.parse(localStorage.getItem(KEY) || 'null') || { ...DEFAULT_STATE }; }
  catch (_) { state = { ...DEFAULT_STATE }; }

  const menu = [
    ['📣','Канал','Последние новости и обновления','channel'],
    ['💬','Поддержка','Поможем с любым вопросом','support'],
    ['⭐','Пополнить','Оплата от 15 ⭐ до 100 ⭐','topup'],
    ['👛','Баланс','Ваши средства','balance'],
    ['🎁','Рефералы','Приглашай друзей и зарабатывай','refs'],
    ['🧰','Кейсы','Открывай и получай призы','cases'],
    ['🎡','Рулетка','Испытай удачу','roulette'],
    ['💳','Вывод','Получай свои призы','withdraw'],
    ['⚙️','Админ-панель','Управление ботом','admin']
  ];

  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (_) {} }
  function money(value) { return Number(value || 0).toLocaleString('ru-RU'); }
  function toast(text) {
    if (!toastEl) return;
    toastEl.textContent = text;
    toastEl.classList.add('show');
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => toastEl.classList.remove('show'), 2200);
  }
  function openTelegram(username, text = '') {
    const url = `https://t.me/${username}${text ? `?text=${encodeURIComponent(text)}` : ''}`;
    try {
      if (window.Telegram?.WebApp?.openTelegramLink) window.Telegram.WebApp.openTelegramLink(url);
      else window.open(url, '_blank', 'noopener,noreferrer');
    } catch (_) { window.location.href = url; }
  }
  function card(item) {
    return `<button type="button" class="card ${item[3] === 'admin' ? 'wide' : ''}" data-action="${item[3]}">
      <div class="icon">${item[0]}</div><div class="copy"><strong>${item[1]}</strong><span>${item[2]}</span></div><div class="arrow">›</div>
    </button>`;
  }
  function renderMenu() {
    screen.innerHTML = `<section class="welcome"><h2>👋 Добро пожаловать в GiftsMMS!</h2><p>Зарабатывай, открывай кейсы и получай крутые призы.</p></section><div class="grid">${menu.map(card).join('')}</div>`;
  }
  function panel(title, body) {
    screen.innerHTML = `<h2 class="page-title">${title}</h2><div class="panel">${body}</div><button type="button" class="btn secondary" data-action="menu">← Вернуться в меню</button>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  function render(action) {
    if (action === 'menu') return renderMenu();
    if (action === 'messages') return panel('✉️ Сообщения','<p>Новых сообщений нет.</p><p class="muted">Здесь будут уведомления об акциях, выигрышах и ответах поддержки.</p>');
    if (action === 'explore') return panel('◈ Исследовать','<p>Следи за новыми кейсами и акциями GiftsMMS.</p><div class="list"><div class="row"><span>🎁 Новые кейсы</span><b>Скоро</b></div><div class="row"><span>⚡ Бонусы</span><b>Скоро</b></div><div class="row"><span>📣 Новости</span><b>@eclipsedlf</b></div></div>');
    if (action === 'profile') return panel('♙ Копилот',`<div class="list"><div class="row"><span>Баланс</span><b>${money(state.balance)} ⭐</b></div><div class="row"><span>Выигрышей</span><b>${state.wins}</b></div><div class="row"><span>Рефералов</span><b>${state.referrals}</b></div></div><p class="hint">Новости и обновления: @eclipsedlf</p>`);
    if (action === 'channel') return panel('📣 Канал','<p>Новости, обновления, акции и розыгрыши GiftsMMS.</p><div class="pay-note">Наш Telegram-канал: <b>@eclipsedlf</b></div><br><button type="button" class="btn" data-channel>Открыть канал</button>');
    if (action === 'support') return panel('💬 Поддержка','<p>Есть вопрос по оплате, кейсам или выводу? Напиши нам — ответим максимально быстро.</p><button type="button" class="btn" data-support>Написать в поддержку</button><p class="hint">Оплата согласовывается с @Xoyli.</p>');
    if (action === 'balance') return panel('👛 Баланс',`<div class="muted">Текущий баланс</div><div class="balance">${money(state.balance)} ⭐</div><div class="actions"><button type="button" class="btn" data-action="topup">Пополнить</button><button type="button" class="btn secondary" data-action="withdraw">Вывести</button></div>`);
    if (action === 'topup') return panel('⭐ Пополнение',`<div class="pay-head"><div class="pay-badge">⭐</div><div><b>Пополнение Stars</b><div class="muted">Выбери сумму от 15 ⭐</div></div></div><div class="pay-grid"><button type="button" class="pay-option" data-pay="15"><b>15 ⭐</b><span>Оплатить</span></button><button type="button" class="pay-option" data-pay="25"><b>25 ⭐</b><span>Оплатить</span></button><button type="button" class="pay-option" data-pay="50"><b>50 ⭐</b><span>Оплатить</span></button><button type="button" class="pay-option" data-pay="100"><b>100 ⭐</b><span>Оплатить</span></button></div><div class="pay-note">💬 Оплата отправляется/согласовывается через <b>@Xoyli</b>. После оплаты сохрани подтверждение и напиши в поддержку.</div><p class="hint">Важно: эта версия интерфейса не подтверждает платеж автоматически. Реальную проверку Stars нужно подключить через Telegram Bot API на сервере.</p>`);
    if (action === 'refs') return panel('🎁 Рефералы',`<p>Приглашай друзей и получай бонусы.</p><div class="row"><div><b class="ref-link">https://t.me/Xoyli</b></div><button type="button" class="btn" data-copy>Копировать</button></div><p class="muted">Приглашено: ${state.referrals}</p>`);
    if (action === 'cases') return panel('🧰 Кейсы',`<p class="muted">Открывай кейс за ⭐ и смотри, какой приз выпадет.</p><div class="case-grid"><div class="case"><div class="gift">🎁</div><b>Стартовый</b><span class="muted">100 ⭐</span><button type="button" class="btn" data-case="100">Открыть</button></div><div class="case"><div class="gift">💎</div><b>Премиум</b><span class="muted">300 ⭐</span><button type="button" class="btn" data-case="300">Открыть</button></div><div class="case"><div class="gift">👑</div><b>VIP</b><span class="muted">700 ⭐</span><button type="button" class="btn" data-case="700">Открыть</button></div></div>`);
    if (action === 'roulette') return panel('🎡 Рулетка','<div class="roulette"><div id="wheel" class="wheel">🎡</div><p>Стоимость вращения: <b>100 ⭐</b></p><button type="button" class="btn" data-spin>Крутить</button><p id="result" class="result"></p></div>');
    if (action === 'withdraw') return panel('💳 Вывод','<p>Минимальная сумма вывода: <b>1 000 ⭐</b></p><input id="amount" type="number" placeholder="Сумма ⭐" min="1000" inputmode="numeric"><button type="button" class="btn" data-withdraw>Создать заявку</button><p class="hint">Заявка не списывается автоматически в реальной версии — вывод должен подтверждаться сервером и администратором.</p>');
    if (action === 'admin') return panel('⚙️ Админ-панель','<div class="list"><div class="row"><span>Пользователей</span><b>—</b></div><div class="row"><span>Пополнений</span><b>—</b></div><div class="row"><span>Выводов</span><b>—</b></div></div><p class="muted">Раздел подготовлен под защищённый backend. Доступ администратора должен проверяться на сервере.</p>');
  }
  function setActive(page) { document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.page === page)); }

  document.addEventListener('click', async event => {
    const actionEl = event.target.closest('[data-action]');
    if (actionEl) { event.preventDefault(); const action = actionEl.dataset.action; setActive(action); render(action); return; }
    const payEl = event.target.closest('[data-pay]');
    if (payEl) { event.preventDefault(); const amount = Number(payEl.dataset.pay); toast(`Открываю @Xoyli — оплата ${amount} ⭐`); openTelegram('Xoyli', `GiftsMMS — хочу оплатить ${amount} ⭐`); return; }
    if (event.target.closest('[data-channel]')) { event.preventDefault(); openTelegram('eclipsedlf'); return; }
    const addEl = event.target.closest('[data-add]');
    if (addEl) { event.preventDefault(); state.balance += Number(addEl.dataset.add); save(); toast('Баланс пополнен в демо-режиме'); render('balance'); return; }
    const caseEl = event.target.closest('[data-case]');
    if (caseEl) {
      event.preventDefault(); const cost = Number(caseEl.dataset.case);
      if (state.balance < cost) return toast('Недостаточно ⭐');
      caseEl.disabled = true; caseEl.textContent = 'Открываем…';
      await new Promise(r => setTimeout(r, 700));
      state.balance -= cost; const prizes = [0, Math.round(cost*.4), cost, Math.round(cost*2), Math.round(cost*5)]; const prize = prizes[Math.floor(Math.random()*prizes.length)]; state.balance += prize; state.wins += 1; save(); toast(`🎉 Приз: ${prize} ⭐`); render('cases'); return;
    }
    if (event.target.closest('[data-spin]')) {
      event.preventDefault(); if (state.balance < 100) return toast('Недостаточно ⭐');
      const button = event.target.closest('[data-spin]'); const wheel = document.getElementById('wheel'); const result = document.getElementById('result'); button.disabled = true; button.textContent = 'Крутим…'; if (wheel) { wheel.classList.remove('spinning'); void wheel.offsetWidth; wheel.classList.add('spinning'); }
      await new Promise(r => setTimeout(r, 1200)); const prize = [0,50,100,150,300,500][Math.floor(Math.random()*6)]; state.balance = state.balance - 100 + prize; state.wins += 1; save(); if (result) result.textContent = `🎉 Выпало: ${prize} ⭐`; button.disabled = false; button.textContent = 'Крутить'; return;
    }
    if (event.target.closest('[data-withdraw]')) { event.preventDefault(); const input = document.getElementById('amount'); const amount = Number(input?.value || 0); if (amount < 1000 || amount > state.balance) return toast('Проверь сумму вывода'); state.balance -= amount; save(); toast('Заявка создана'); render('balance'); return; }
    if (event.target.closest('[data-copy]')) { event.preventDefault(); try { await navigator.clipboard.writeText('https://t.me/Xoyli'); toast('Ссылка скопирована'); } catch (_) { toast('Ссылка: https://t.me/Xoyli'); } return; }
    if (event.target.closest('[data-support]')) { event.preventDefault(); openTelegram('Xoyli', 'GiftsMMS — нужна помощь'); return; }
  });

  try { if (window.Telegram?.WebApp) { window.Telegram.WebApp.ready(); window.Telegram.WebApp.expand(); } } catch (_) {}
  renderMenu();
})();