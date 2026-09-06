(() => {
  const boot = () => {
    const crashMode = document.getElementById('crashMode');
    const crashTab = document.querySelector('.tabs button[data-mode="crash"]');
    const arenaTab = document.querySelector('.tabs button[data-mode="arena"]');
    const arenaMode = document.getElementById('arenaMode');
    const arenaTon = document.getElementById('arenaTon');

    if (crashMode) crashMode.style.display = 'none';
    if (crashTab) crashTab.style.display = 'none';
    if (arenaTon) arenaTon.style.display = 'none';
    if (arenaTab) {
      document.querySelectorAll('.tabs button').forEach(b => b.classList.remove('active'));
      arenaTab.classList.add('active');
    }
    if (!arenaMode) return;
    arenaMode.style.display = 'block';

    const style = document.createElement('style');
    style.id = 'ice-arena-style';
    style.textContent = `
      #arenaMode .ice-shell{margin-top:8px}
      #arenaMode .ice-arena{position:relative;height:clamp(300px,82vw,390px);overflow:hidden;border-radius:28px;background:#626b76;box-shadow:inset 0 0 90px #1118,0 16px 42px #0007;border:1px solid #ffffff1c;isolation:isolate}
      #arenaMode .ice-arena.waiting{background:#626b76}
      #arenaMode .ice-arena.active{background:#56616e}
      #arenaMode .ice-arena:before{content:"";position:absolute;inset:0;z-index:1;background:radial-gradient(circle at 50% 45%,#ffffff18,transparent 38%),linear-gradient(120deg,#ffffff08,transparent 35%,#00000018 70%,#ffffff08);pointer-events:none}
      #arenaMode .ice-arena:after{content:"";position:absolute;inset:0;z-index:2;background-image:linear-gradient(115deg,transparent 0 47%,#fff1 48%,transparent 49%),linear-gradient(25deg,transparent 0 63%,#fff0 64%,transparent 65%);background-size:170px 150px,210px 190px;opacity:.35;mix-blend-mode:screen;pointer-events:none}
      #arenaMode .territory-layer{position:absolute;inset:0;z-index:0;transition:filter .35s ease,transform .35s ease}
      #arenaMode .ice-arena.active .territory-layer{filter:saturate(1.18) brightness(1.04)}
      #arenaMode .territory-pulse{position:absolute;inset:12%;border:1px solid #fff2;border-radius:50%;box-shadow:0 0 30px #fff1;pointer-events:none;z-index:3}
      #arenaMode .arena-hud{position:absolute;z-index:8;top:10px;left:10px;right:10px;display:flex;justify-content:space-between;gap:8px;pointer-events:none}
      #arenaMode .arena-pill{padding:7px 10px;border-radius:12px;background:#101820cc;border:1px solid #ffffff18;backdrop-filter:blur(9px);font-size:11px;font-weight:900;box-shadow:0 6px 16px #0005}
      #arenaMode .arena-pill.live{color:#d9f7ff}
      #arenaMode .arena-center{position:absolute;z-index:7;left:50%;top:50%;transform:translate(-50%,-50%);width:132px;height:94px;border-radius:26px;display:grid;place-items:center;text-align:center;background:#111923e8;border:1px solid #ffffff26;box-shadow:0 12px 35px #0009, inset 0 0 25px #ffffff08;font-size:12px;font-weight:900;pointer-events:none;backdrop-filter:blur(7px)}
      #arenaMode .arena-center b{font-size:24px;color:#dff7ff;letter-spacing:.02em}
      #arenaMode .arena-center .small{font-size:10px;color:#aebbc8}
      #arenaMode .territory{position:absolute;z-index:4;left:50%;top:50%;width:0;height:0;transform-origin:0 0;pointer-events:none}
      #arenaMode .territory-badge{position:absolute;left:0;top:0;transform:translate(-50%,-50%);width:64px;height:64px;border-radius:50%;display:grid;place-items:center;text-align:center;background:#f3fbff;color:#12202c;border:3px solid #d9f6ff;box-shadow:0 8px 25px #0008,0 0 22px #dff9ff66;font-size:10px;font-weight:950;line-height:1.05}
      #arenaMode .territory-badge b{display:block;font-size:16px}
      #arenaMode .territory-badge span{display:block;max-width:58px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      #arenaMode .territory-badge.me{outline:2px solid #fff;outline-offset:3px}
      #arenaMode .ice-note{margin-top:9px;padding:10px 12px;border-radius:15px;background:#17202a;border:1px solid #ffffff0c;color:#b9c5d0;font-size:11px;line-height:1.35}
      #arenaMode .ice-note b{color:#eaf8ff}
      #arenaMode .arena-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:9px}
      #arenaMode .arena-stat{padding:10px 8px;border-radius:15px;background:#1b242e;border:1px solid #ffffff09;text-align:center}
      #arenaMode .arena-stat strong{display:block;font-size:17px}
      #arenaMode .arena-stat span{display:block;margin-top:2px;color:#8f9daa;font-size:10px}
      #arenaMode .ice-players{display:grid;gap:7px;margin-top:10px}
      #arenaMode .ice-player{display:grid;grid-template-columns:38px minmax(0,1fr) auto;align-items:center;gap:9px;padding:9px 10px;border-radius:15px;background:#1b2027;border:1px solid #ffffff08}
      #arenaMode .ice-avatar{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;background:#dfeaf1;color:#15202a;font-weight:950;overflow:hidden}
      #arenaMode .ice-avatar img{width:100%;height:100%;object-fit:cover}
      #arenaMode .ice-name{font-weight:850;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      #arenaMode .ice-meta{margin-top:2px;color:#8794a0;font-size:10px}
      #arenaMode .ice-chance{text-align:right;font-weight:950;color:#e8f7ff}
      #arenaMode .ice-chance small{display:block;color:#83909d;font-size:10px;font-weight:700}
      #arenaMode .ice-history{margin-top:10px;display:grid;gap:7px}
      #arenaMode .history-row{display:flex;justify-content:space-between;gap:10px;padding:10px 11px;border-radius:14px;background:#171c22;font-size:11px}
      #arenaMode .history-row b{font-size:12px}
      #arenaMode .history-row .win{color:#9ce7c0}.history-row .loss{color:#ffb2b2}.history-row .void{color:#aeb8c2}
      #arenaMode .ice-actions{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:10px}
      #arenaMode .ice-bet{height:45px;border-radius:14px;background:linear-gradient(145deg,#edfaff,#b9d9e8);color:#12202b;font-weight:950;box-shadow:inset 0 1px #fff,0 7px 18px #0004}
      #arenaMode .ice-bet:disabled{opacity:.38;box-shadow:none}
      #arenaMode .ice-bet small{display:block;font-size:9px;color:#516675}
      #arenaMode .confirm-backdrop{position:fixed;z-index:1200;inset:0;display:none;align-items:flex-end;background:#02070bcc;backdrop-filter:blur(5px)}
      #arenaMode .confirm-backdrop.open{display:flex}
      #arenaMode .confirm-card{width:100%;padding:18px 15px calc(16px + env(safe-area-inset-bottom));border-radius:25px 25px 0 0;background:#121a22;border:1px solid #ffffff14;box-shadow:0 -20px 60px #000b}
      #arenaMode .confirm-card h3{margin:0 0 6px;font-size:19px}.confirm-card p{margin:0;color:#aeb9c4;font-size:12px;line-height:1.4}
      #arenaMode .confirm-total{margin:13px 0;padding:13px;border-radius:16px;background:#1b2630;text-align:center}.confirm-total b{font-size:26px;color:#e8f9ff}
      #arenaMode .confirm-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}.confirm-actions button{height:48px;border-radius:14px;font-weight:950}.confirm-cancel{background:#252e37;color:#fff}.confirm-ok{background:#e8f9ff;color:#111d26}
      @media(max-width:390px){#arenaMode .ice-arena{height:290px}#arenaMode .territory-badge{width:56px;height:56px}#arenaMode .arena-center{width:118px;height:86px}}
    `;
    if (!document.getElementById('ice-arena-style')) document.head.appendChild(style);

    const arenaCard = arenaMode.querySelector('.card');
    const shell = document.createElement('div');
    shell.className = 'ice-shell';
    shell.innerHTML = `
      <div class="ice-arena waiting" id="iceArenaField">
        <div class="territory-layer" id="iceTerritories"></div>
        <div class="territory-pulse"></div>
        <div class="arena-hud"><span class="arena-pill live" id="iceStatus">● СБОР ИГРОКОВ</span><span class="arena-pill" id="iceTimer">15 сек</span></div>
        <div class="arena-center"><span>БАНК</span><b>◆ <span id="iceBank">0</span></b><span class="small">АРЕНА #<span id="iceId">—</span></span></div>
      </div>
      <div class="arena-stats"><div class="arena-stat"><strong id="icePlayersCount">0/8</strong><span>участники</span></div><div class="arena-stat"><strong id="iceEntry">25–500</strong><span>вход, очки</span></div><div class="arena-stat"><strong id="iceBalance">0</strong><span>мой баланс</span></div></div>
      <div class="ice-note"><b>Ставка = шанс.</b> Территория каждого игрока занимает долю поля, равную его доле банка. Чем больше ставка, тем больше сектор и шанс на победу. Все решения принимает сервер.</div>
      <div class="ice-actions" id="iceBetActions"></div>
      <div class="ice-players" id="icePlayers"></div>
      <div class="card" style="margin-top:10px"><div class="section-title"><h2>Мои матчи</h2><span class="small">последние 20</span></div><div class="ice-history" id="iceHistory"><div class="small">История появится после завершённых раундов.</div></div></div>
      <div class="confirm-backdrop" id="iceConfirm"><div class="confirm-card"><h3>Подтвердить участие?</h3><p>После подтверждения очки будут зарезервированы сервером. Виртуальные очки не являются денежной ставкой и не выводятся.</p><div class="confirm-total"><span>Вход</span><br><b id="iceConfirmAmount">0 ◆</b></div><div class="confirm-actions"><button class="confirm-cancel" id="iceConfirmCancel">Отмена</button><button class="confirm-ok" id="iceConfirmOk">Подтвердить</button></div></div></div>
    `;

    const oldArena = arenaMode.querySelector('.arena');
    if (oldArena) oldArena.remove();
    const oldPlayers = arenaMode.querySelector('#arenaPlayers');
    if (oldPlayers) oldPlayers.closest('.card')?.remove();
    const betRow = arenaMode.querySelector('.bet-row');
    if (betRow) betRow.remove();
    if (arenaCard) arenaCard.remove();
    arenaMode.insertBefore(shell, arenaMode.firstChild?.nextSibling || arenaMode.firstChild);

    const field = document.getElementById('iceArenaField');
    const territories = document.getElementById('iceTerritories');
    const statusEl = document.getElementById('iceStatus');
    const timerEl = document.getElementById('iceTimer');
    const bankEl = document.getElementById('iceBank');
    const idEl = document.getElementById('iceId');
    const playersCountEl = document.getElementById('icePlayersCount');
    const entryEl = document.getElementById('iceEntry');
    const balanceEl = document.getElementById('iceBalance');
    const playersEl = document.getElementById('icePlayers');
    const historyEl = document.getElementById('iceHistory');
    const actionsEl = document.getElementById('iceBetActions');
    const confirm = document.getElementById('iceConfirm');
    const confirmAmount = document.getElementById('iceConfirmAmount');
    const confirmCancel = document.getElementById('iceConfirmCancel');
    const confirmOk = document.getElementById('iceConfirmOk');
    let pendingAmount = 0;
    let latest = null;
    let serverOffset = 0;
    let polling = false;

    const tg = window.Telegram?.WebApp;
    if (tg?.expand) tg.expand();
    const headers = () => tg?.initData ? {'X-Telegram-Init-Data': tg.initData} : {};
    const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
    const initials = name => {
      const parts = String(name || 'Игрок').trim().split(/\s+/).filter(Boolean);
      return ((parts[0]?.[0] || 'И') + (parts[1]?.[0] || '')).toUpperCase();
    };
    const palette = ['#a8d8ff','#b7f0e1','#c8c0ff','#b9e7ff','#d7f2bd','#e8c9ff','#a9e8f5','#c9d5ff'];

    function territoryGradient(players, active) {
      if (!players.length) return '#626b76';
      let cursor = 0;
      const stops = [];
      players.forEach((p, index) => {
        const chance = Math.max(0, Number(p.chance || 0));
        const start = cursor;
        cursor += chance;
        const c = palette[index % palette.length];
        const alpha = active ? 'dd' : 'a8';
        stops.push(`${c}${alpha} ${start.toFixed(3)}% ${cursor.toFixed(3)}%`);
      });
      if (cursor < 100) stops.push(`#626b76 ${cursor.toFixed(3)}% 100%`);
      return `conic-gradient(from -90deg,${stops.join(',')})`;
    }

    function renderTerritories(players, active) {
      territories.innerHTML = '';
      if (!players.length) return;
      let angle = -90;
      players.forEach((p, index) => {
        const chance = Math.max(0, Number(p.chance || 0));
        const mid = angle + chance * 1.8;
        angle += chance * 3.6;
        const item = document.createElement('div');
        item.className = 'territory';
        const radius = Math.min(38, 24 + chance * .12);
        item.style.transform = `translate(-50%,-50%) rotate(${mid}deg) translateX(${radius}%)`;
        const badge = document.createElement('div');
        badge.className = 'territory-badge' + (Number(p.user_id) === Number(latest?.self_user_id) ? ' me' : '');
        const photo = p.photo_url ? `<img src="${esc(p.photo_url)}" alt="" loading="lazy">` : '';
        badge.innerHTML = photo || `<b>${esc(initials(p.name))}</b><span>${esc(p.name)}</span><b>${Number(p.chance || 0).toFixed(1)}%</b>`;
        if (photo) badge.innerHTML += `<span>${esc(p.name)}</span><b>${Number(p.chance || 0).toFixed(1)}%</b>`;
        item.appendChild(badge);
        territories.appendChild(item);
      });
    }

    function renderPlayers(players) {
      if (!players.length) {
        playersEl.innerHTML = '<div class="small">Пока никто не вошёл. Поле остаётся серым.</div>';
        return;
      }
      playersEl.innerHTML = players.map((p, index) => {
        const photo = p.photo_url ? `<img src="${esc(p.photo_url)}" alt="" loading="lazy">` : esc(initials(p.name));
        return `<div class="ice-player"><div class="ice-avatar">${photo}</div><div><div class="ice-name">${esc(p.name)}</div><div class="ice-meta">Игрок ${index + 1} · ${Number(p.bet).toLocaleString('ru-RU')} ◆</div></div><div class="ice-chance">${Number(p.chance || 0).toFixed(2)}%<small>к победе</small></div></div>`;
      }).join('');
    }

    function renderHistory(history) {
      if (!Array.isArray(history) || !history.length) {
        historyEl.innerHTML = '<div class="small">История появится после завершённых раундов.</div>';
        return;
      }
      historyEl.innerHTML = history.map(h => {
        const cls = h.result === 'win' ? 'win' : h.result === 'loss' ? 'loss' : 'void';
        const label = h.result === 'win' ? `Победа +${Number(h.bank || 0).toLocaleString('ru-RU')} ◆` : h.result === 'loss' ? 'Проигрыш' : 'Отмена';
        return `<div class="history-row"><span><b>#${h.battle_id}</b><br>${new Date(Number(h.ended_at || h.created_at) * 1000).toLocaleString('ru-RU')}</span><span class="${cls}">${label}</span></div>`;
      }).join('');
    }

    function updateTimer() {
      if (!latest) return;
      const now = Date.now() / 1000 + serverOffset;
      const seconds = Math.max(0, Math.ceil(Number(latest.countdown_end || 0) - now));
      if (latest.status === 'waiting') {
        statusEl.textContent = '● СБОР ИГРОКОВ';
        timerEl.textContent = `${seconds} сек · ${latest.players.length}/${latest.max_players || 8}`;
        field.classList.add('waiting'); field.classList.remove('active');
      } else if (latest.status === 'active') {
        statusEl.textContent = '● АРЕНА LIVE';
        timerEl.textContent = `${seconds} сек`;
        field.classList.remove('waiting'); field.classList.add('active');
      } else {
        statusEl.textContent = '● НОВЫЙ РАУНД';
        timerEl.textContent = 'завершён';
      }
    }

    function render(data) {
      latest = data;
      if (data?.server_time) serverOffset = Number(data.server_time) - Date.now() / 1000;
      bankEl.textContent = Number(data?.bank || 0).toLocaleString('ru-RU');
      idEl.textContent = data?.battle_id ?? '—';
      balanceEl.textContent = Number(data?.points || 0).toLocaleString('ru-RU');
      playersCountEl.textContent = `${Array.isArray(data?.players) ? data.players.length : 0}/${data?.max_players || 8}`;
      entryEl.textContent = (data?.entry_options || [25,100,500]).join(' · ');
      const players = Array.isArray(data?.players) ? data.players : [];
      territories.style.background = territoryGradient(players, data?.status === 'active');
      renderTerritories(players, data?.status === 'active');
      renderPlayers(players);
      renderHistory(data?.history);
      actionsEl.innerHTML = (data?.entry_options || [25,100,500]).map(amount => `<button class="ice-bet" data-ice-bet="${amount}" ${data?.status !== 'waiting' || Number(data?.points || 0) < amount || players.length >= Number(data?.max_players || 8) ? 'disabled' : ''}>◆ ${amount}<small>очков</small></button>`).join('');
      actionsEl.querySelectorAll('[data-ice-bet]').forEach(btn => btn.addEventListener('click', () => openConfirm(Number(btn.dataset.iceBet))));
      updateTimer();
    }

    async function load() {
      if (polling) return;
      polling = true;
      try {
        const response = await fetch('/api/public-battle', {headers: headers(), cache: 'no-store'});
        if (response.status === 403) return;
        if (!response.ok) throw new Error('arena');
        const data = await response.json();
        data.self_user_id = data.self_user_id || null;
        render(data);
      } catch (_) {
        statusEl.textContent = '● СВЯЗЬ…';
      } finally {
        polling = false;
      }
    }

    function openConfirm(amount) {
      if (!latest || latest.status !== 'waiting') return;
      if (Number(latest.points || 0) < amount) {
        document.getElementById('topDeposit')?.click();
        return;
      }
      pendingAmount = amount;
      confirmAmount.textContent = `${amount.toLocaleString('ru-RU')} ◆`;
      confirm.classList.add('open');
    }

    confirmCancel.onclick = () => { pendingAmount = 0; confirm.classList.remove('open'); };
    confirm.addEventListener('click', e => { if (e.target === confirm) confirmCancel.click(); });
    confirmOk.onclick = async () => {
      if (!pendingAmount) return;
      confirmOk.disabled = true;
      confirmOk.textContent = 'Проверяем…';
      try {
        const response = await fetch('/api/public-battle/join', {method:'POST',headers:{...headers(),'Content-Type':'application/json'},body:JSON.stringify({amount:pendingAmount})});
        const result = await response.json();
        if (!result.ok) throw new Error(result.message || 'Не удалось войти');
        confirm.classList.remove('open');
        pendingAmount = 0;
        if (result.battle) render(result.battle);
        await load();
      } catch (err) {
        alert(err.message || 'Не удалось войти в арену');
      } finally {
        confirmOk.disabled = false;
        confirmOk.textContent = 'Подтвердить';
      }
    };

    document.querySelectorAll('[data-arena]').forEach(btn => btn.style.display = 'none');
    document.querySelectorAll('[data-bet]').forEach(btn => btn.textContent = `${btn.dataset.bet} очков`);

    const ref = document.querySelector('.ref');
    if (ref) {
      const heading = ref.querySelector('h3');
      const text = ref.querySelector('p');
      if (heading) heading.textContent = 'Пригласите друзей · +0.85 ⭐';
      if (text) text.textContent = '+0.85 ⭐ за каждого приглашённого. Для кейса нужны 3 реальных приглашённых.';
    }

    let countdownTimer = window.setInterval(updateTimer, 250);
    let pollTimer = null;
    const startPolling = () => {
      load();
      pollTimer = window.setInterval(load, 1000);
    };
    startPolling();

    const showGate = () => {
      if (document.getElementById('subscriptionGate')) return;
      const gate = document.createElement('div');
      gate.id = 'subscriptionGate';
      gate.style.cssText = 'position:fixed;inset:0;z-index:9999;display:grid;place-items:center;padding:24px;background:#0d0d0df5;color:#fff;text-align:center';
      gate.innerHTML = '<div style="width:min(420px,100%);padding:24px;border-radius:24px;background:#19191d"><div style="font-size:52px">🔒</div><h2 style="margin:8px 0">Подпишитесь на канал</h2><p style="color:#aaa;line-height:1.45">Чтобы пользоваться GiftsEZZ, подпишитесь на @eclipsedlf и затем проверьте подписку.</p><button id="gateJoin" style="width:100%;height:48px;border:0;border-radius:14px;background:#fff;color:#111;font-weight:900">📢 Подписаться</button><button id="gateCheck" style="width:100%;height:48px;margin-top:8px;border:0;border-radius:14px;background:#2a2a30;color:#fff;font-weight:900">✅ Проверить</button><div id="gateMsg" style="margin-top:10px;color:#aaa;font-size:12px"></div></div>';
      document.body.appendChild(gate);
      document.getElementById('gateJoin').onclick = () => window.Telegram?.WebApp?.openTelegramLink ? window.Telegram.WebApp.openTelegramLink('https://t.me/eclipsedlf') : (location.href = 'https://t.me/eclipsedlf');
      document.getElementById('gateCheck').onclick = async () => {
        const msg = document.getElementById('gateMsg');
        try {
          const r = await fetch('/api/me', {headers:headers()});
          if (r.ok) location.reload(); else msg.textContent = '❌ Подписка ещё не подтверждена.';
        } catch (_) { msg.textContent = '❌ Не удалось проверить подписку.'; }
      };
    };

    setTimeout(async () => {
      try {
        if (!tg?.initData) return;
        const r = await fetch('/api/me', {headers:headers(),cache:'no-store'});
        if (r.status === 403) showGate();
      } catch (_) {}
    }, 100);

    window.addEventListener('beforeunload', () => {
      if (countdownTimer) clearInterval(countdownTimer);
      if (pollTimer) clearInterval(pollTimer);
    });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, {once:true});
  else boot();
})();
