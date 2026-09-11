(() => {
  'use strict';

  const KEY = 'giftsmms-demo-v2';
  const DEFAULT_STATE = { balance: 1250, wins: 0, referrals: 3 };
  const screen = document.getElementById('screen');
  const toastEl = document.getElementById('toast');

  let state;
  try {
    state = JSON.parse(localStorage.getItem(KEY) || 'null') || { ...DEFAULT_STATE };
  } catch (_) {
    state = { ...DEFAULT_STATE };
  }

  const menu = [
    ['📣','Канал','Последние новости и обновления','channel'],
    ['💬','Поддержка','Поможем с любым вопросом','support'],
    ['⭐','Пополнить','Удобные способы оплаты','topup'],
    ['👛','Баланс','Ваши средства','balance'],
    ['🎁','Рефералы','Приглашай друзей и зарабатывай','refs'],
    ['🧰','Кейсы','Открывай и получай призы','cases'],
    ['🎡','Рулетка','Испытай удачу','roulette'],
    ['💳','Вывод','Получай свои призы','withdraw'],
    ['⚙️','Админ-панель','Управление ботом','admin']
  ];

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (_) {}
  }

  function toast(text) {
    if (!toastEl) return;
    toastEl.textContent = text;
    toastEl.classList.add('show');
    window.clearTimeout(toast.timer);
    toast.timer = window.setTimeout(() => toastEl.classList.remove('show'), 1800);
  }

  function card(item) {
    return `<button type="button" class="card ${item[3] === 'admin' ? 'wide' : ''}" data-action="${item[3]}">
      <div class="icon">${item[0]}</div>
      <div class="copy"><strong>${item[1]}</strong><span>${item[2]}</span></div>
      <div class="arrow">›</div>
    </button>`;
  }

  function renderMenu() {
    screen.innerHTML = `<section class="welcome">
      <h2>👋 Добро пожаловать в GiftsMMS!</h2>
      <p>Зарабатывай, открывай кейсы, получай крутые призы!</p>
    </section><div class="grid">${menu.map(card).join('')}</div>`;
  }

  function panel(title, body) {
    screen.innerHTML = `<h2 class="page-title">${title}</h2><div class="panel">${body}</div>
      <button type="button" class="btn secondary" data-action="menu">← Вернуться в меню</button>`;
  }

  function render(action) {
    if (action === 'menu') return renderMenu();
    if (action === 'messages') return panel('✉️ Сообщения','<p>Новых сообщений нет.</p><p class="muted">Когда появится сообщение от поддержки, оно будет здесь.</p>');
    if (action === 'explore') return panel('◈ Исследовать','<p>Здесь будут новые кейсы, акции и специальные предложения.</p>');
    if (action === 'profile') return panel('♙ Копилот','<p>Профиль пользователя GiftsMMS.</p><p class="muted">В полной версии здесь будет Telegram-профиль и настройки.</p>');
    if (action === 'channel') return panel('📣 Канал','<p>Здесь будут новости, акции и обновления GiftsMMS.</p><p class="muted">Канал: @Xoyli</p>');
    if (action === 'support') return panel('💬 Поддержка','<p>Опиши вопрос — в полной версии сообщение будет отправлено оператору.</p><button type="button" class="btn" data-support>Написать в поддержку</button>');
    if (action === 'balance') return panel('👛 Баланс',`<div class="muted">Текущий баланс</div><div class="balance">${Number(state.balance).toLocaleString('ru-RU')} ⭐</div><div class="actions"><button type="button" class="btn" data-action="topup">Пополнить</button><button type="button" class="btn secondary" data-action="withdraw">Вывести</button></div>`);
    if (action === 'topup') return panel('⭐ Пополнение','<p>Демо-режим: реальные платежи подключаются через выбранного платёжного провайдера.</p><div class="actions"><button type="button" class="btn" data-add="500">+500 ⭐</button><button type="button" class="btn" data-add="1000">+1000 ⭐</button><button type="button" class="btn" data-add="5000">+5000 ⭐</button></div>');
    if (action === 'refs') return panel('🎁 Рефералы',`<p>Твоя реферальная ссылка:</p><div class="row"><b>GiftsMMS • @Xoyli</b><button type="button" class="btn" data-copy>Копировать</button></div><p class="muted">Приглашено: ${state.referrals}</p>`);
    if (action === 'cases') return panel('🧰 Кейсы',`<div class="case-grid"><div class="case"><div class="gift">🎁</div><b>Стартовый</b><span class="muted">100 ⭐</span><br><button type="button" class="btn" data-case="100">Открыть</button></div><div class="case"><div class="gift">💎</div><b>Премиум</b><span class="muted">300 ⭐</span><br><button type="button" class="btn" data-case="300">Открыть</button></div><div class="case"><div class="gift">👑</div><b>VIP</b><span class="muted">700 ⭐</span><br><button type="button" class="btn" data-case="700">Открыть</button></div></div>`);
    if (action === 'roulette') return panel('🎡 Рулетка','<div style="text-align:center"><div style="font-size:80px">🎡</div><p>Стоимость вращения: <b>100 ⭐</b></p><button type="button" class="btn" data-spin>Крутить</button><p id="result" class="muted"></p></div>');
    if (action === 'withdraw') return panel('💳 Вывод','<p>Минимальная сумма вывода: 1 000 ⭐</p><input id="amount" type="number" placeholder="Сумма" min="1000" style="width:100%;padding:14px;border-radius:12px;border:1px solid #31505e;background:#071820;color:white;margin:10px 0"><button type="button" class="btn" data-withdraw>Создать заявку</button>');
    if (action === 'admin') return panel('⚙️ Админ-панель','<div class="list"><div class="row"><span>Пользователей</span><b>—</b></div><div class="row"><span>Пополнений</span><b>—</b></div><div class="row"><span>Выводов</span><b>—</b></div></div><p class="muted">Для реального управления подключается защищённый backend с правами администратора.</p>');
  }

  function setActive(page) {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.page === page));
  }

  document.addEventListener('click', async (event) => {
    const actionEl = event.target.closest('[data-action]');
    if (actionEl) {
      event.preventDefault();
      const action = actionEl.dataset.action;
      setActive(action);
      render(action);
      return;
    }

    const addEl = event.target.closest('[data-add]');
    if (addEl) {
      event.preventDefault();
      state.balance += Number(addEl.dataset.add);
      save();
      toast('Баланс пополнен в демо-режиме');
      render('balance');
      return;
    }

    const caseEl = event.target.closest('[data-case]');
    if (caseEl) {
      event.preventDefault();
      const cost = Number(caseEl.dataset.case);
      if (state.balance < cost) return toast('Недостаточно ⭐');
      state.balance -= cost;
      const prizes = [0, Math.round(cost * .4), cost, Math.round(cost * 2), Math.round(cost * 5)];
      const prize = prizes[Math.floor(Math.random() * prizes.length)];
      state.balance += prize;
      state.wins += 1;
      save();
      toast(`Приз: ${prize} ⭐`);
      render('cases');
      return;
    }

    if (event.target.closest('[data-spin]')) {
      event.preventDefault();
      if (state.balance < 100) return toast('Недостаточно ⭐');
      state.balance -= 100;
      const prize = [0,50,100,150,300,500][Math.floor(Math.random() * 6)];
      state.balance += prize;
      save();
      const result = document.getElementById('result');
      if (result) result.textContent = `Выпало: ${prize} ⭐`;
      return;
    }

    if (event.target.closest('[data-withdraw]')) {
      event.preventDefault();
      const input = document.getElementById('amount');
      const amount = Number(input?.value || 0);
      if (amount < 1000 || amount > state.balance) return toast('Проверь сумму');
      state.balance -= amount;
      save();
      toast('Заявка на вывод создана');
      render('balance');
      return;
    }

    if (event.target.closest('[data-copy]')) {
      event.preventDefault();
      try {
        await navigator.clipboard.writeText('https://t.me/Xoyli');
        toast('Ссылка скопирована');
      } catch (_) {
        toast('Скопируй ссылку: https://t.me/Xoyli');
      }
      return;
    }

    if (event.target.closest('[data-support]')) {
      event.preventDefault();
      toast('Заявка создана');
    }
  });

  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', event => {
      event.preventDefault();
      const page = item.dataset.page;
      setActive(page);
      render(page);
    });
  });

  // Telegram Mini App support, if opened inside Telegram.
  try {
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
    }
  } catch (_) {}

  renderMenu();
})();
