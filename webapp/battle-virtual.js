(() => {
  const tg = window.Telegram && window.Telegram.WebApp;
  const auth = () => ({
    "X-Telegram-Init-Data": (tg && tg.initData) || "",
    "Content-Type": "application/json"
  });
  const list = () => document.getElementById("battleList");

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
    const left = data.countdown_end ? Math.max(0, Number(data.countdown_end) - now) : 0;
    const active = data.status === "active";
    const waiting = data.status === "waiting";
    const playerText = players.length ? players.map((p, i) => `
      <div class="card" style="padding:10px 12px;display:flex;justify-content:space-between;align-items:center">
        <span>👤 ${escapeHtml(p.user_id)}</span><b>${p.bet} pts · ${p.chance}%</b>
      </div>`).join("") : `<div class="muted" style="padding:14px 0">Пока никто не вошёл. Будь первым.</div>`;

    el.innerHTML = `
      <div class="card" style="overflow:hidden">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
          <div><b>⚔️ PUBLIC BATTLE</b><div class="sub">Одна общая комната · виртуальные очки</div></div>
          <b style="color:var(--gold)">${data.bank} pts</b>
        </div>
        <div style="position:relative;height:190px;margin:14px 0;border-radius:24px;background:#090b12;display:flex;align-items:center;justify-content:center">
          <div style="width:150px;height:150px;border-radius:50%;background:${wheelGradient(players)};box-shadow:0 0 35px #35d9ff33;display:flex;align-items:center;justify-content:center">
            <div style="width:88px;height:88px;border-radius:50%;background:#10131c;border:1px solid #ffffff18;display:flex;align-items:center;justify-content:center;font-size:42px">🚀</div>
          </div>
          <div style="position:absolute;top:7px;left:50%;transform:translateX(-50%);font-size:20px">▼</div>
          <div style="position:absolute;bottom:8px;left:50%;transform:translateX(-50%);font-weight:800;font-size:24px">${active ? `🚀 ${left}s` : "🚀 ГОТОВ"}</div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
          ${[25,100,500].map(amount => `<button class="btn" onclick="joinPublicBattle(${amount})" ${active ? "disabled" : ""}>${amount} pts</button>`).join("")}
        </div>
        <div class="sub" style="margin-top:10px">Твои очки: <b>${data.points}</b> · шанс зависит от твоей доли банка</div>
      </div>
      <div style="display:grid;gap:8px;margin-top:10px">${playerText}</div>`;
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

  // Disable the old room-creation action: the public round is always shared.
  window.createBattle = () => loadPublicBattle();
  window.loadBattles = loadPublicBattle;

  function boot() {
    const oldCreate = document.querySelector("#battles .create");
    if (oldCreate) oldCreate.style.display = "none";
    loadPublicBattle();
    setInterval(loadPublicBattle, 700);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
