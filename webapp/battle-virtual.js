(() => {
  const tg = window.Telegram && window.Telegram.WebApp;
  const auth = () => ({
    "X-Telegram-Init-Data": (tg && tg.initData) || "",
    "Content-Type": "application/json"
  });
  const list = () => document.getElementById("battleList");
  let lastBattleId = null;
  let lastStatus = null;

  function injectStyles() {
    if (document.getElementById("giftsmms-battle-style")) return;
    const style = document.createElement("style");
    style.id = "giftsmms-battle-style";
    style.textContent = `
      #battles .create { display:none !important; }
      #battleList { transition: opacity .25s ease, transform .25s ease; }
      .g-battle { animation:gBattleIn .45s cubic-bezier(.2,.8,.2,1); }
      .g-wheel { animation:gWheelFloat 4s ease-in-out infinite; transition:transform .7s cubic-bezier(.2,.8,.2,1), filter .4s ease; }
      .g-wheel.running { animation:gWheelSpin 1.25s linear infinite; filter:drop-shadow(0 0 18px rgba(53,217,255,.28)); }
      .g-rocket { animation:gRocketFloat 1.8s ease-in-out infinite; }
      .g-rocket.running { animation:gRocketFly .7s ease-in-out infinite alternate; }
      .g-count { text-shadow:0 0 18px rgba(53,217,255,.65); transition:transform .25s ease, opacity .25s ease; }
      .g-count.tick { transform:scale(1.12); }
      .g-bet { transition:transform .18s ease, box-shadow .18s ease, opacity .18s ease; }
      .g-bet:not(:disabled):active { transform:scale(.96); }
      .g-player { animation:gPlayerIn .35s ease both; }
      .g-chip { padding:5px 9px;border-radius:999px;background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.07); }
      @keyframes gBattleIn { from{opacity:0;transform:translateY(12px) scale(.985)} to{opacity:1;transform:none} }
      @keyframes gPlayerIn { from{opacity:0;transform:translateX(-8px)} to{opacity:1;transform:none} }
      @keyframes gWheelFloat { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-4px) rotate(1deg)} }
      @keyframes gWheelSpin { to{transform:rotate(360deg)} }
      @keyframes gRocketFloat { 0%,100%{transform:translateY(0) rotate(-3deg)} 50%{transform:translateY(-6px) rotate(3deg)} }
      @keyframes gRocketFly { from{transform:translateY(0) rotate(-4deg)} to{transform:translateY(-7px) rotate(4deg)} }
    `;
    document.head.appendChild(style);
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>\"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[ch]));
  }

  function wheelGradient(players) {
    if (!players.length) return "conic-gradient(#242938 0 100%)";
    let cursor = 0;
    const parts = players.map((p, i) => {
      const start = cursor;
      cursor += Number(p.chance || 0);
      return `hsl(${185 + i * 43} 85% 60%) ${start}% ${cursor}%`;
    });
    return `conic-gradient(${parts.join(",")})`;
  }

  function renderBattle(data) {
    const el = list();
    if (!el || !data) return;
    const players = data.players || [];
    const now = Math.floor(Date.now() / 1000);
    const active = data.status === "active";
    const left = active && data.countdown_end ? Math.max(0, Number(data.countdown_end) - now) : 10;
    const statusText = active ? `СТАРТ ЧЕРЕЗ ${left}` : "СТАРТ ЧЕРЕЗ 10";
    const playerText = players.length ? players.map((p, i) => `
      <div class="card g-player" style="padding:11px 12px;display:flex;justify-content:space-between;align-items:center;animation-delay:${i * 45}ms">
        <span>👤 ${escapeHtml(p.user_id)}</span><b>${p.bet} pts · ${p.chance}%</b>
      </div>`).join("") : `<div class="muted" style="padding:14px 0">Пока никто не вошёл. Будь первым.</div>`;

    el.innerHTML = `
      <div class="card g-battle" style="overflow:hidden;background:linear-gradient(145deg,rgba(25,29,43,.96),rgba(11,14,20,.98));border:1px solid rgba(130,100,255,.16);box-shadow:0 16px 50px rgba(0,0,0,.22)">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
          <div><b style="letter-spacing:.5px">⚔️ PUBLIC BATTLE</b><div class="sub">Одна общая комната · виртуальные очки</div></div>
          <div class="g-chip"><b style="color:var(--gold)">${data.bank} pts</b></div>
        </div>
        <div style="position:relative;height:215px;margin:14px 0;border-radius:26px;background:radial-gradient(circle at 50% 35%,rgba(72,49,140,.22),transparent 48%),#090b12;display:flex;align-items:center;justify-content:center;overflow:hidden">
          <div style="position:absolute;inset:0;background:linear-gradient(115deg,transparent 0 46%,rgba(53,217,255,.035) 50%,transparent 54%);pointer-events:none"></div>
          <div class="g-wheel ${active ? "running" : ""}" style="width:158px;height:158px;border-radius:50%;background:${wheelGradient(players)};box-shadow:0 0 45px rgba(53,217,255,.16),inset 0 0 25px rgba(255,255,255,.08);display:flex;align-items:center;justify-content:center">
            <div style="width:92px;height:92px;border-radius:50%;background:#10131c;border:1px solid rgba(255,255,255,.1);display:flex;align-items:center;justify-content:center;box-shadow:inset 0 0 25px rgba(0,0,0,.35)"><span class="g-rocket ${active ? "running" : ""}" style="font-size:44px">🚀</span></div>
          </div>
          <div style="position:absolute;top:7px;left:50%;transform:translateX(-50%);font-size:21px;text-shadow:0 0 12px rgba(255,255,255,.3)">▼</div>
          <div class="g-count" style="position:absolute;bottom:9px;left:50%;transform:translateX(-50%);font-weight:900;font-size:22px;white-space:nowrap">🚀 ${statusText}</div>
          <div style="position:absolute;top:12px;right:12px;font-size:12px;opacity:.7">500 ⭐ / 0</div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
          ${[25,100,500].map(amount => `<button class="btn g-bet" onclick="joinPublicBattle(${amount})" ${active ? "disabled" : ""}>${amount} pts</button>`).join("")}
        </div>
        <div class="sub" style="margin-top:10px">Твои очки: <b>${data.points}</b> · шанс зависит от твоей доли банка</div>
      </div>
      <div style="display:grid;gap:8px;margin-top:10px">${playerText}</div>`;

    if (active && left > 0) {
      const count = el.querySelector(".g-count");
      if (count) {
        count.classList.add("tick");
        setTimeout(() => count.classList.remove("tick"), 180);
      }
    }
    lastBattleId = data.battle_id;
    lastStatus = data.status;
  }

  async function loadPublicBattle() {
    try {
      const response = await fetch("/api/public-battle", { headers: auth(), cache: "no-store" });
      if (!response.ok) return;
      renderBattle(await response.json());
    } catch (_) {}
  }

  window.joinPublicBattle = async function(amount) {
    try {
      const response = await fetch("/api/public-battle/join", {
        method: "POST",
        headers: auth(),
        body: JSON.stringify({ amount })
      });
      const data = await response.json();
      if (!data.ok) alert(data.message || "Не удалось войти в раунд");
      await loadPublicBattle();
    } catch (_) {
      alert("Не удалось подключиться к батлу");
    }
  };

  window.createBattle = () => loadPublicBattle();
  window.loadBattles = loadPublicBattle;

  function boot() {
    injectStyles();
    const oldCreate = document.querySelector("#battles .create");
    if (oldCreate) oldCreate.remove();
    loadPublicBattle();
    setInterval(loadPublicBattle, 700);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
