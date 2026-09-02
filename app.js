const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); try{tg.setHeaderColor('#0c0614');tg.setBackgroundColor('#0c0614');}catch(e){} }

let stars = 127, ton = 0, dailyClaimed = false, refCount = 0, refEarned = 0;
let currentCase = null, inventory = [], selectedUpgrade = null;
let dailyDate = '';

// ========== SAVE / LOAD ==========
function saveData() {
  const data = {
    stars, ton, dailyClaimed, dailyDate, refCount, refEarned, inventory, tasks
  };
  try { localStorage.setItem('giftsEzz_save', JSON.stringify(data)); } catch(e){}
}

function loadData() {
  try {
    const raw = localStorage.getItem('giftsEzz_save');
    if (!raw) return;
    const data = JSON.parse(raw);
    if (typeof data.stars === 'number') stars = data.stars;
    if (typeof data.ton === 'number') ton = data.ton;
    if (typeof data.refCount === 'number') refCount = data.refCount;
    if (typeof data.refEarned === 'number') refEarned = data.refEarned;
    if (Array.isArray(data.inventory)) inventory = data.inventory;
    if (Array.isArray(data.tasks)) {
      data.tasks.forEach((t, i) => {
        if (tasks[i]) {
          tasks[i].done = t.done;
          if (t.progress !== undefined) tasks[i].progress = t.progress;
        }
      });
    }
    // Daily reset at new day
    const today = new Date().toDateString();
    if (data.dailyDate === today && data.dailyClaimed) {
      dailyClaimed = true;
      dailyDate = today;
    } else {
      dailyClaimed = false;
      dailyDate = today;
    }
  } catch(e){}
}

const marketPrices = [
  {e:'🍦',n:'Ice Cream',v:454},{e:'🐰',n:'Bunny',v:455},{e:'🔮',n:'Crystal Ball',v:449},
  {e:'🍭',n:'Candy Cane',v:449},{e:'🔦',n:'Flashlight',v:380},{e:'🕯️',n:'Candle',v:320},
  {e:'🧸',n:'Teddy Bear',v:520},{e:'💍',n:'Ring',v:890},{e:'💎',n:'Diamond',v:1250},
  {e:'👑',n:'Crown',v:2800},{e:'🐸',n:'Pepe',v:3400},{e:'🦄',n:'Unicorn',v:5500}
];

const prizes = {
  free:[{e:'🕯️',n:'Candle',v:15},{e:'🍭',n:'Candy',v:20},{e:'🍦',n:'Ice Cream',v:25},{e:'🐰',n:'Bunny',v:30}],
  basic:[{e:'🔦',n:'Flashlight',v:40},{e:'🧸',n:'Teddy',v:60},{e:'🔮',n:'Crystal',v:90},{e:'🍦',n:'Ice Cream',v:70}],
  rare:[{e:'💍',n:'Ring',v:150},{e:'💎',n:'Diamond',v:200},{e:'🐰',n:'Gold Bunny',v:180},{e:'👑',n:'Mini Crown',v:250}],
  epic:[{e:'👑',n:'Crown',v:400},{e:'💎',n:'Big Diamond',v:450},{e:'🐸',n:'Pepe',v:500},{e:'🦄',n:'Unicorn',v:600}],
  legend:[{e:'👑',n:'Legend Crown',v:1200},{e:'🐸',n:'Rare Pepe',v:1500},{e:'🦄',n:'Mythic Unicorn',v:2000}],
  eggs:[{e:'🥚',n:'Egg',v:50},{e:'🐣',n:'Chick',v:90},{e:'🐥',n:'Bird',v:130}],
  slots:[{e:'🍒',n:'Cherry',v:70},{e:'🍋',n:'Lemon',v:90},{e:'7️⃣',n:'Seven',v:200}]
};

const casePrices = {free:0,basic:50,rare:150,epic:400,legend:1000,eggs:80,slots:120};
const caseNames = {free:'Бесплатный',basic:'Базовый',rare:'Редкий',epic:'Эпический',legend:'Легендарный',eggs:'Яйца',slots:'Слоты'};

const tasks = [
  {id:1,icon:'📅',title:'Ежедневный вход',reward:1,done:false},
  {id:2,icon:'👥',title:'Пригласи 1 друга',reward:0.5,done:false},
  {id:3,icon:'📦',title:'Открой 3 кейса',reward:5,done:false,progress:0,max:3},
  {id:4,icon:'💰',title:'Пополни от 50 ⭐',reward:10,done:false},
  {id:5,icon:'🚀',title:'Сыграй в Краш',reward:3,done:false}
];

function go(name) {
  document.querySelectorAll('.screen').forEach(s=>{s.classList.remove('active');s.style.display='none';});
  const el = document.getElementById(name);
  if(!el) return;
  el.classList.add('active'); el.style.display='block';
  document.querySelectorAll('.nav-item').forEach(item=>{
    item.classList.toggle('active', item.dataset.s === name);
  });
  if(name==='cases') renderCases();
  if(name==='tasks') renderTasks();
  if(name==='leaderboard') renderLeaderboard();
  if(name==='profile') renderInventory();
  if(name==='topup') renderMarket();
}

function updateBalance() {
  document.getElementById('stars').textContent = Math.floor(stars*10)/10;
  document.getElementById('ton').textContent = ton.toFixed(2);
  const invS = document.getElementById('invStars');
  const invT = document.getElementById('invTon');
  if (invS) invS.textContent = Math.floor(stars*10)/10;
  if (invT) invT.textContent = ton.toFixed(2);
  saveData();
}

function claimDaily() {
  if(dailyClaimed) return;
  dailyClaimed = true;
  dailyDate = new Date().toDateString();
  stars += 1;
  updateBalance();
  document.getElementById('dailyBox').classList.add('claimed');
  document.getElementById('dailyBtn').textContent = 'Получено ✓';
  document.getElementById('dailyText').textContent = 'Возвращайся завтра!';
  toast('+1 ⭐ ежедневный бонус');
  completeTask(1);
  saveData();
}

function switchTab(btn,id) {
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  btn.classList.add('active');
  ['starsTab','tonTab','giftsTab'].forEach(t=>{
    document.getElementById(t).classList.toggle('hidden', t!==id);
  });
}
function setAmount(v){ document.getElementById('topupAmount').textContent=v; }
function setTon(v){ document.getElementById('tonAmount').textContent=v; }

function doTopupStars() {
  const v = parseInt(document.getElementById('topupAmount').textContent);
  if(v < 15){ toast('Минимум 15 ⭐'); return; }
  stars += v;
  updateBalance();
  toast('+'+v+' ⭐ пополнено!');
  if(v >= 50) completeTask(4);
  go('main');
}
function doTopupTon() {
  const v = parseFloat(document.getElementById('tonAmount').textContent);
  ton += v;
  const bonus = Math.floor(v * 150);
  stars += bonus;
  updateBalance();
  toast('+'+v+' TON и +'+bonus+' ⭐');
  go('main');
}
function renderMarket() {
  document.getElementById('marketGifts').innerHTML = marketPrices.map(g=>`
    <div class="inv-item"><div class="e">${g.e}</div><div class="p">⭐ ${g.v}</div></div>
  `).join('');
}

function renderCases() {
  const list = [{t:'basic',e:'📦'},{t:'rare',e:'🎁'},{t:'epic',e:'💎'},{t:'legend',e:'👑'},{t:'eggs',e:'🥚'},{t:'slots',e:'🎰'}];
  document.getElementById('casesGrid').innerHTML = list.map(c=>`
    <div class="case-card" onclick="openCase('${c.t}')">
      <div class="emoji">${c.e}</div>
      <div class="name">${caseNames[c.t]}</div>
      <div class="price">⭐ ${casePrices[c.t]}</div>
    </div>
  `).join('');
}

function openCase(type) {
  currentCase = type;
  document.getElementById('caseTitle').textContent = caseNames[type]||'Кейс';
  document.getElementById('caseBox').textContent = type==='eggs'?'🥚':type==='slots'?'🎰':'📦';
  document.getElementById('caseBox').className = 'case-box';
  document.getElementById('prizeEmoji').className = 'prize';
  document.getElementById('prizeName').textContent = '';
  document.getElementById('prizeValue').textContent = '';
  document.getElementById('openBtn').classList.remove('hidden');
  document.getElementById('againBtn').classList.add('hidden');
  go('opencase');
}

function spinCase() {
  const price = casePrices[currentCase]||0;
  if(stars < price){ toast('Недостаточно звёзд'); return; }
  stars -= price;
  updateBalance();
  const box = document.getElementById('caseBox');
  document.getElementById('openBtn').classList.add('hidden');
  box.classList.add('shake');
  setTimeout(()=>{
    box.classList.remove('shake'); box.classList.add('open');
    const list = prizes[currentCase]||prizes.basic;
    const prize = list[Math.floor(Math.random()*list.length)];
    document.getElementById('prizeEmoji').textContent = prize.e;
    document.getElementById('prizeEmoji').classList.add('show');
    document.getElementById('prizeName').textContent = prize.n;
    document.getElementById('prizeValue').textContent = '⭐ '+prize.v;
    addToInventory(prize);
    progressTask(3);
    setTimeout(()=>document.getElementById('againBtn').classList.remove('hidden'),400);
  },700);
}
function resetCase(){ openCase(currentCase); }

function addToInventory(prize) {
  inventory.push({...prize, id:Date.now()+Math.random()});
  renderInventory();
}
function renderInventory() {
  const grid = document.getElementById('invGrid');
  if (!grid) return;
  const items = inventory.map(p=>`
    <div class="inv-item">
      <div class="e">${p.e}</div>
      <div class="p">⭐ ${p.v}</div>
      <div class="actions">
        <button onclick="sellItem(${p.id})">Продать</button>
        <button onclick="withdrawItem(${p.id})">Вывод</button>
      </div>
    </div>
  `).join('');
  grid.innerHTML = items + `<div class="add-slot" onclick="go('topup')">+</div>`;
  const cnt = document.getElementById('invCount');
  if (cnt) cnt.textContent = inventory.length;
  saveData();
}
function sellItem(id) {
  const idx = inventory.findIndex(i=>i.id===id);
  if(idx===-1) return;
  const item = inventory[idx];
  stars += item.v;
  inventory.splice(idx,1);
  updateBalance();
  renderInventory();
  toast('Продано за ⭐ '+item.v);
}
function withdrawItem(id) {
  const idx = inventory.findIndex(i=>i.id===id);
  if(idx===-1) return;
  inventory.splice(idx,1);
  renderInventory();
  toast('NFT отправлен в Telegram');
}

let crashRunning=false, crashMult=1, crashInterval=null, crashBetAmount=0;
function startCrash() {
  if(crashRunning) return;
  const bet = parseInt(document.getElementById('crashBet').value)||0;
  if(bet<1){ toast('Минимум 1 ⭐'); return; }
  if(stars<bet){ toast('Недостаточно звёзд'); return; }
  stars -= bet; crashBetAmount = bet; updateBalance();
  crashRunning = true; crashMult = 1;
  document.getElementById('crashMult').textContent = '1.00x';
  document.getElementById('crashMult').classList.remove('danger');
  document.getElementById('crashStatus').textContent = 'Растёт... Забирай вовремя!';
  document.getElementById('crashBtn').classList.add('hidden');
  document.getElementById('cashoutBtn').classList.remove('hidden');
  completeTask(5);
  const crashPoint = 1 + Math.random()*8;
  crashInterval = setInterval(()=>{
    crashMult += 0.05 + Math.random()*0.08;
    document.getElementById('crashMult').textContent = crashMult.toFixed(2)+'x';
    if(crashMult>3) document.getElementById('crashMult').classList.add('danger');
    if(crashMult >= crashPoint){
      clearInterval(crashInterval); crashRunning=false;
      document.getElementById('crashStatus').textContent = 'Краш на '+crashPoint.toFixed(2)+'x';
      document.getElementById('crashBtn').classList.remove('hidden');
      document.getElementById('cashoutBtn').classList.add('hidden');
      addCrashHistory(crashPoint,false);
      toast('Краш! Ставка потеряна');
    }
  },100);
}
function cashOut() {
  if(!crashRunning) return;
  clearInterval(crashInterval); crashRunning=false;
  const win = Math.floor(crashBetAmount * crashMult);
  stars += win; updateBalance();
  document.getElementById('crashStatus').textContent = 'Забрано '+crashMult.toFixed(2)+'x → +'+win+' ⭐';
  document.getElementById('crashBtn').classList.remove('hidden');
  document.getElementById('cashoutBtn').classList.add('hidden');
  addCrashHistory(crashMult,true);
  toast('+'+win+' ⭐');
}
function addCrashHistory(mult,win) {
  const h = document.getElementById('crashHistory');
  const span = document.createElement('span');
  span.className = win?'win':'lose';
  span.textContent = mult.toFixed(2)+'x';
  h.prepend(span);
  if(h.children.length>12) h.lastChild.remove();
}

function selectUpgradeItem() {
  if(inventory.length===0){ toast('Инвентарь пуст'); return; }
  selectedUpgrade = inventory[0];
  document.getElementById('upgradeFrom').innerHTML = `
    <div style="font-size:48px;">${selectedUpgrade.e}</div>
    <div style="font-weight:700;margin-top:6px;">${selectedUpgrade.n}</div>
    <div style="color:var(--gold);">⭐ ${selectedUpgrade.v}</div>`;
  const target = marketPrices[Math.floor(Math.random()*marketPrices.length)];
  document.getElementById('upgradeTo').innerHTML = `
    <div style="font-size:48px;">${target.e}</div>
    <div style="font-weight:700;margin-top:6px;">${target.n}</div>
    <div style="color:var(--gold);">⭐ ${target.v}</div>`;
  const chance = Math.min(85, Math.max(15, Math.floor(selectedUpgrade.v / target.v * 70)));
  document.getElementById('upgradeChance').textContent = 'Шанс успеха: '+chance+'%';
  document.getElementById('upgradeTo').dataset.target = JSON.stringify(target);
  document.getElementById('upgradeChance').dataset.chance = chance;
}
function doUpgrade() {
  if(!selectedUpgrade){ toast('Выберите подарок'); return; }
  const chance = parseInt(document.getElementById('upgradeChance').dataset.chance)||30;
  const success = Math.random()*100 < chance;
  const idx = inventory.findIndex(i=>i.id===selectedUpgrade.id);
  if(idx!==-1) inventory.splice(idx,1);
  if(success){
    const target = JSON.parse(document.getElementById('upgradeTo').dataset.target);
    inventory.push({...target, id:Date.now()});
    toast('Апгрейд успешен! 🎉');
  } else toast('Апгрейд не удался 😢');
  selectedUpgrade = null;
  document.getElementById('upgradeFrom').innerHTML = `<div style="font-size:40px;">+</div><div style="color:var(--muted);font-size:13px;margin-top:6px;">Выберите подарок</div>`;
  document.getElementById('upgradeTo').innerHTML = `<div style="font-size:40px;">🎁</div><div style="color:var(--muted);font-size:13px;margin-top:6px;">Цель апгрейда</div>`;
  document.getElementById('upgradeChance').textContent = 'Шанс: —';
  renderInventory();
}

function inviteFriend() {
  refCount += 1; refEarned += 0.5; stars += 0.5;
  document.getElementById('refCount').textContent = refCount;
  document.getElementById('refEarned').textContent = refEarned.toFixed(1);
  updateBalance();
  toast('+0.50 ⭐ за реферала');
  completeTask(2);
  saveData();
}

function renderTasks() {
  document.getElementById('taskList').innerHTML = tasks.map(t=>`
    <div class="task">
      <div class="task-icon">${t.icon}</div>
      <div class="task-info">
        <div class="task-title">${t.title}</div>
        <div class="task-reward">+${t.reward} ⭐ ${t.progress!==undefined?'('+t.progress+'/'+t.max+')':''}</div>
      </div>
      <button class="task-btn ${t.done?'done':''}" onclick="claimTask(${t.id})" ${t.done?'disabled':''}>
        ${t.done?'✓':'Забрать'}
      </button>
    </div>
  `).join('');
  const left = tasks.filter(t=>!t.done).length;
  const badge = document.getElementById('taskBadge');
  badge.textContent = left||'';
  badge.style.display = left?'flex':'none';
}
function completeTask(id) {
  const t = tasks.find(x=>x.id===id);
  if(t && !t.done){ t.done=true; renderTasks(); saveData(); }
}
function progressTask(id) {
  const t = tasks.find(x=>x.id===id);
  if(t && !t.done && t.max){
    t.progress = (t.progress||0)+1;
    if(t.progress >= t.max) t.done=true;
    renderTasks();
    saveData();
  }
}
function claimTask(id) {
  const t = tasks.find(x=>x.id===id);
  if(!t || t.done) return;
  if(id===1 && dailyClaimed){ stars+=t.reward; t.done=true; }
  else if(id===2 && refCount>=1){ stars+=t.reward; t.done=true; }
  else if(id===3 && t.progress>=t.max){ stars+=t.reward; t.done=true; }
  else if(id===5){ stars+=t.reward; t.done=true; }
  else { toast('Сначала выполните задание'); return; }
  updateBalance(); renderTasks();
  toast('+'+t.reward+' ⭐ за задание');
}

function renderLeaderboard() {
  const names = ['CryptoKing','GiftHunter','StarLord','PepeFan','TONMaster','CaseOpener','LuckyOne','NFTQueen','MoonBoy','DiamondHands'];
  let html = `<div class="lb-item" style="border-color:var(--purple);">
    <div class="lb-rank">You</div><div class="lb-name">Вы</div>
    <div class="lb-stars">⭐ ${Math.floor(stars)}</div></div>`;
  for(let i=0;i<10;i++){
    const s = Math.floor(5000 - i*350 + Math.random()*200);
    const rc = i===0?'gold':i===1?'silver':i===2?'bronze':'';
    html += `<div class="lb-item"><div class="lb-rank ${rc}">${i+1}</div>
      <div class="lb-name">${names[i]}</div><div class="lb-stars">⭐ ${s}</div></div>`;
  }
  document.getElementById('lbList').innerHTML = html;
}

function doWithdrawStars() {
  const v = parseInt(document.getElementById('withdrawAmount').textContent);
  if(v<50){ toast('Минимум 50 ⭐'); return; }
  if(stars<v){ toast('Недостаточно звёзд'); return; }
  stars -= v; updateBalance();
  toast('Выведено '+v+' ⭐');
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2200);
}
function closeApp(){ if(tg) tg.close(); else toast('Закрытие Mini App'); }

// ========== INIT ==========
loadData();
updateBalance();

// Apply daily UI
if (dailyClaimed) {
  const box = document.getElementById('dailyBox');
  if (box) {
    box.classList.add('claimed');
    document.getElementById('dailyBtn').textContent = 'Получено ✓';
    document.getElementById('dailyText').textContent = 'Возвращайся завтра!';
  }
}

// Apply ref UI
const rc = document.getElementById('refCount');
const re = document.getElementById('refEarned');
if (rc) rc.textContent = refCount;
if (re) re.textContent = refEarned.toFixed(1);

document.getElementById('liveItems').innerHTML += document.getElementById('liveItems').innerHTML;
