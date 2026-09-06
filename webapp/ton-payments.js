(() => {
  const tg = window.Telegram && window.Telegram.WebApp;
  const auth = () => ({
    "Content-Type": "application/json",
    "X-Telegram-Init-Data": (tg && tg.initData) || ""
  });
  const api = async (path, options = {}) => {
    const response = await fetch(path, { ...options, headers: { ...auth(), ...(options.headers || {}) } });
    return response.json();
  };

  async function startTonDeposit() {
    const amount = parseFloat(prompt("Сколько TON пополнить?", "0.1") || "0");
    if (!Number.isFinite(amount) || amount <= 0) return;
    try {
      const data = await api("/api/ton/deposit", { method: "POST", body: JSON.stringify({ amount }) });
      if (!data.ok) return window.toast ? toast(data.message) : alert(data.message);
      window.__lastTonDeposit = data;
      const block = document.getElementById("tonDepositBlock");
      if (block) {
        block.classList.remove("hidden");
        block.querySelector(".ton-destination").textContent = data.destination;
        block.querySelector(".ton-comment").textContent = data.comment;
      }
      window.open(data.ton_uri, "_blank");
      if (window.toast) toast("TON-запрос создан. После отправки вставь hash транзакции.");
    } catch (_) {
      if (window.toast) toast("Не удалось создать TON-запрос");
    }
  }

  async function confirmTonDeposit() {
    const input = document.getElementById("tonTxHash");
    const tx_hash = (input && input.value || "").trim();
    if (!tx_hash) return window.toast ? toast("Вставь hash TON-транзакции") : alert("Вставь hash TON-транзакции");
    try {
      const data = await api("/api/ton/confirm", { method: "POST", body: JSON.stringify({ tx_hash }) });
      if (!data.ok) return window.toast ? toast(data.message) : alert(data.message);
      if (window.toast) toast(`Зачислено ${data.credited_ton} TON 💎`);
      if (typeof loadMe === "function") await loadMe();
      if (input) input.value = "";
    } catch (_) {
      if (window.toast) toast("Не удалось проверить транзакцию");
    }
  }

  function mount() {
    const deposit = document.getElementById("deposit");
    if (!deposit || document.getElementById("tonDepositBlock")) return;
    const card = deposit.querySelector(".card");
    if (!card) return;
    const block = document.createElement("div");
    block.id = "tonDepositBlock";
    block.className = "hidden";
    block.style.marginTop = "14px";
    block.innerHTML = `
      <div class="sub">💎 TON — отдельный реальный баланс, без конвертации в Stars.</div>
      <button class="cta" style="width:100%;margin-bottom:10px" onclick="startTonDeposit()">Пополнить 💎 TON</button>
      <div class="card" style="padding:13px;background:#0b0e15">
        <div class="muted" style="font-size:12px">Адрес получателя</div>
        <div class="ton-destination" style="word-break:break-all;font-size:12px;margin:5px 0 10px">—</div>
        <div class="muted" style="font-size:12px">Комментарий</div>
        <div class="ton-comment" style="word-break:break-all;font-size:12px;margin:5px 0 10px">—</div>
        <input id="tonTxHash" placeholder="Hash TON-транзакции">
        <button class="chip" style="width:100%" onclick="confirmTonDeposit()">Проверить и зачислить TON</button>
      </div>`;
    card.appendChild(block);
    window.startTonDeposit = startTonDeposit;
    window.confirmTonDeposit = confirmTonDeposit;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
