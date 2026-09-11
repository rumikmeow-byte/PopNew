const KEY='giftsmms-demo';
const state=JSON.parse(localStorage.getItem(KEY)||'{"balance":1250,"wins":0,"referrals":3}');
const screen=document.getElementById('screen');
const toastEl=document.getElementById('toast');
const menu=[['📣','Канал','Последние новости и обновления','channel'],['💬','Поддержка','Поможем с любым вопросом','support'],['⭐','Пополнить','Удобные способы оплаты','topup'],['👛','Баланс','Ваши средства','balance'],['🎁','Рефералы','Приглашай друзей и зарабатывай','refs'],['🧰','Кейсы','Открывай и получай призы','cases'],['🎡','Рулетка','Испытай удачу','roulette'],['💳','Вывод','Получай свои призы','withdraw'],['⚙️','Админ-панель','Управление ботом','admin']];
function save(){localStorage.setItem(KEY,JSON.stringify(state))}
function toast(t){toastEl.textContent=t;toastEl.classList.add('show');setTimeout(()=>toastEl.classList.remove('show'),1800)}
function card(x){return `<button class="card ${x[3]==='admin'?'wide':''}" data-action="${x[3]}"><div class="icon">${x[0]}</div><div class="copy"><strong>${x[1]}</strong><span>${x[2]}</span></div><div class="arrow">›</div></button>`}
function renderMenu(){screen.innerHTML=`<section class="welcome"><h2>👋 Добро пожаловать в GiftsMMS!</h2><p>Зарабатывай, открывай кейсы, получай крутые призы!</p></section><div class="grid">${menu.map(card).join('')}</div>`}
function panel(title,body){screen.innerHTML=`<h2 class="page-title">${title}</h2><div class="panel">${body}</div><button class="btn secondary" data-action="menu">← Вернуться в меню</button>`}
function render(action){
 if(action==='menu'){renderMenu();return}
 if(action==='channel') panel('📣 Канал','<p>Здесь будут новости, акции и обновления GiftsMMS.</p><p class="muted">Канал: @Xoyli</p>');
 if(action==='support') panel('💬 Поддержка','<p>Опиши вопрос — в полной версии сообщение будет отправлено оператору.</p><button class="btn" onclick="toast(\'Заявка создана\')">Написать в поддержку</button>');
 if(action==='balance') panel('👛 Баланс',`<div class="muted">Текущий баланс</div><div class="balance">${state.balance.toLocaleString('ru-RU')} ⭐</div><div class="actions"><button class="btn" data-action="topup">Пополнить</button><button class="btn secondary" data-action="withdraw">Вывести</button></div>`);
 if(action==='topup') panel('⭐ Пополнение','<p>Демо-режим: реальные платежи подключаются через выбранного платёжного провайдера.</p><div class="actions"><button class="btn" data-add="500">+500 ⭐</button><button class="btn" data-add="1000">+1000 ⭐</button><button class="btn" data-add="5000">+5000 ⭐</button></div>');
 if(action==='refs') panel('🎁 Рефералы',`<p>Твоя реферальная ссылка:</p><div class="row"><b>GiftsMMS • @Xoyli</b><button class="btn" onclick="navigator.clipboard?.writeText('https://t.me/Xoyli');toast('Ссылка скопирована')">Копировать</button></div><p class="muted">Приглашено: ${state.referrals}</p>`);
 if(action==='cases') panel('🧰 Кейсы',`<div class="case-grid"><div class="case"><div class="gift">🎁</div><b>Стартовый</b><span class="muted">100 ⭐</span><br><button class="btn" data-case="100">Открыть</button></div><div class="case"><div class="gift">💎</div><b>Премиум</b><span class="muted">300 ⭐</span><br><button class="btn" data-case="300">Открыть</button></div><div class="case"><div class="gift">👑</div><b>VIP</b><span class="muted">700 ⭐</span><br><button class="btn" data-case="700">Открыть</button></div></div>`);
 if(action==='roulette') panel('🎡 Рулетка',`<div style="text-align:center"><div style="font-size:80px">🎡</div><p>Стоимость вращения: <b>100 ⭐</b></p><button class="btn" id="spin">Крутить</button><p id="result" class="muted"></p></div>`);
 if(action==='withdraw') panel('💳 Вывод','<p>Минимальная сумма вывода: 1 000 ⭐</p><input id="amount" type="number" placeholder="Сумма" min="1000" style="width:100%;padding:14px;border-radius:12px;border:1px solid #31505e;background:#071820;color:white;margin:10px 0"><button class="btn" id="withdrawBtn">Создать заявку</button>');
 if(action==='admin') panel('⚙️ Админ-панель','<div class="list"><div class="row"><span>Пользователей</span><b>—</b></div><div class="row"><span>Пополнений</span><b>—</b></div><div class="row"><span>Выводов</span><b>—</b></div></div><p class="muted">Для реального управления подключается защищённый backend с правами администратора.</p>');
}
document.addEventListener('click',e=>{const a=e.target.closest('[data-action]');if(a){const action=a.dataset.action;document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n.dataset.page===action));render(action)}
 const add=e.target.closest('[data-add]');if(add){state.balance+=Number(add.dataset.add);save();toast('Баланс пополнен в демо-режиме');render('balance')}
 const c=e.target.closest('[data-case]');if(c){const cost=Number(c.dataset.case);if(state.balance<cost){toast('Недостаточно ⭐');return}state.balance-=cost;const prizes=[0,Math.round(cost*.4),cost,Math.round(cost*2),Math.round(cost*5)];const prize=prizes[Math.floor(Math.random()*prizes.length)];state.balance+=prize;state.wins++;save();toast(`Приз: ${prize} ⭐`);render('cases')}
 if(e.target.id==='spin'){if(state.balance<100){toast('Недостаточно ⭐');return}state.balance-=100;const prize=[0,50,100,150,300,500][Math.floor(Math.random()*6)];state.balance+=prize;save();document.getElementById('result').textContent=`Выпало: ${prize} ⭐`;}}
 if(e.target.id==='withdrawBtn'){const n=Number(document.getElementById('amount').value);if(n<1000||n>state.balance){toast('Проверь сумму');return}state.balance-=n;save();toast('Заявка на вывод создана');render('balance')}});
renderMenu();
