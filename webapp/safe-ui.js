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
    if (arenaMode) arenaMode.style.display = 'block';

    document.querySelectorAll('[data-arena]').forEach(btn => {
      btn.textContent = `${btn.dataset.arena} очков`;
    });
    const center = document.querySelector('.arena-center');
    if (center) center.innerHTML = 'Банк<br><b>◆ <span id="arenaBank">0</span></b><br><span class="small">Игра #<span id="arenaId">—</span></span>';
    const betTitle = document.getElementById('betTitle');
    if (betTitle) betTitle.textContent = 'Ставка в виртуальных очках';
    document.querySelectorAll('[data-bet]').forEach(btn => {
      btn.textContent = `${btn.dataset.bet} очков`;
    });

    const oldRenderArena = window.renderArena;
    if (typeof oldRenderArena === 'function' && !oldRenderArena.__safeWrapped) {
      const wrapped = function (data) {
        oldRenderArena(data);
        const bank = document.getElementById('arenaBank');
        if (bank) bank.textContent = Number(data?.bank || 0).toLocaleString('ru-RU');
        document.querySelectorAll('#arenaPlayers .gold').forEach(el => {
          el.textContent = el.textContent.replace(/^⭐\s*/, '◆ ');
        });
      };
      wrapped.__safeWrapped = true;
      window.renderArena = wrapped;
    }

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
          const tg = window.Telegram?.WebApp;
          const headers = {};
          if (tg?.initData) headers['X-Telegram-Init-Data'] = tg.initData;
          const r = await fetch('/api/me', {headers});
          if (r.ok) location.reload();
          else msg.textContent = '❌ Подписка ещё не подтверждена.';
        } catch (_) { msg.textContent = '❌ Не удалось проверить подписку.'; }
      };
    };

    setTimeout(async () => {
      try {
        const tg = window.Telegram?.WebApp;
        if (!tg?.initData) return;
        const headers = {'X-Telegram-Init-Data': tg.initData};
        const r = await fetch('/api/me', {headers});
        if (r.status === 403) showGate();
      } catch (_) {}
    }, 100);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
