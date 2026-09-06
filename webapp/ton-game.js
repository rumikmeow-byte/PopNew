// GiftsEZZ compatibility patch: use the server-generated TON transfer URI so the unique
// deposit comment is preserved and can be verified on-chain by the backend.
(() => {
  const boot = () => {
    const button = document.getElementById('createTon');
    if (button && !button.dataset.giftsEzzPatched) {
      button.dataset.giftsEzzPatched = '1';
      button.onclick = async () => {
        try {
          const tg = window.Telegram?.WebApp;
          const amount = Number(document.querySelector('[data-ton].active')?.dataset.ton || 0.25);
          const headers = {'Content-Type':'application/json'};
          if (tg?.initData) headers['X-Telegram-Init-Data'] = tg.initData;
          const r = await fetch('/api/ton/deposit', {method:'POST', headers, body:JSON.stringify({amount})});
          const d = await r.json();
          if (!d.ok) throw new Error(d.message || 'TON-платёж не создан');
          const info = document.getElementById('tonDepositInfo');
          if (info) info.textContent = `Отправьте ${d.amount} TON на ${d.destination}. Комментарий: ${d.comment}`;
          if (tg?.openLink) tg.openLink(d.ton_uri);
          else window.location.href = d.ton_uri;
        } catch (e) {
          if (window.toast) window.toast(e.message || 'TON-платёж не создан');
        }
      };
    }

    // Add the architecture scheme directly inside the Mini App.
    if (!document.getElementById('giftsEzzSchemaBtn')) {
      const style = document.createElement('style');
      style.textContent = `
        #giftsEzzSchemaBtn{position:fixed;right:12px;bottom:92px;z-index:70;width:46px;height:46px;border-radius:15px;background:#19171f;border:1px solid #6d35e888;color:#ffd700;font-size:21px;box-shadow:0 10px 30px #0009}
        #giftsEzzSchema{position:fixed;inset:0;z-index:300;display:none;background:#000d;align-items:flex-end}
        #giftsEzzSchema.open{display:flex}
        #giftsEzzSchema .box{width:100%;height:92vh;background:#0d0d0f;border-radius:26px 26px 0 0;overflow:auto;padding:14px 10px calc(18px + env(safe-area-inset-bottom));box-shadow:0 -20px 80px #000}
        #giftsEzzSchema .bar{display:flex;align-items:center;justify-content:space-between;padding:4px 4px 12px;position:sticky;top:0;background:#0d0d0f;z-index:2}
        #giftsEzzSchema h3{margin:0;font-size:18px}.gse-close{background:#242429;color:#fff;border-radius:12px;padding:9px 12px;font-weight:900}
        #giftsEzzSchema img{display:block;width:100%;height:auto;border-radius:18px;border:1px solid #ffffff12}
      `;
      document.head.appendChild(style);
      const btn = document.createElement('button');
      btn.id = 'giftsEzzSchemaBtn'; btn.type = 'button'; btn.textContent = '🗺️'; btn.title = 'Схема GiftsEZZ';
      const sheet = document.createElement('div');
      sheet.id = 'giftsEzzSchema';
      sheet.innerHTML = `<div class="box"><div class="bar"><h3>🎁 Как устроен GiftsEZZ</h3><button class="gse-close" type="button">Закрыть</button></div><img src="/giftsezz-schema.svg" alt="Схема архитектуры GiftsEZZ"></div>`;
      document.body.append(btn, sheet);
      const close = () => sheet.classList.remove('open');
      btn.onclick = () => sheet.classList.add('open');
      sheet.querySelector('.gse-close').onclick = close;
      sheet.addEventListener('click', e => { if (e.target === sheet) close(); });
    }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(boot, 50));
  else setTimeout(boot, 50);
})();
