(() => {
  const boot = () => {
    const app = document.querySelector('.app');
    const arenaMode = document.getElementById('arenaMode');
    if (!app || !arenaMode) return;

    document.title = 'ECLIPSE';
    document.body.classList.add('eclipse-arena-only');

    const style = document.createElement('style');
    style.id = 'eclipse-arena-only-style';
    style.textContent = `
      :root{--purple:#7c4dff;--purple2:#9a7bff;--e-bg:#0b0b10}
      body{background:var(--e-bg)!important}
      .app{background:radial-gradient(circle at 50% -8%,#25173c 0,#101016 34%,#0b0b10 78%)!important;padding-bottom:16px!important}
      .tabs,.nav,.eclipse-nav{display:none!important}
      #crashMode,#crashMode *{display:none!important}
      #arenaTon{display:none!important}
      #arenaMode{display:block!important}
      .eclipse-hidden{display:none!important}
      .eclipse-arena-brand{display:flex;align-items:center;gap:10px;margin:4px 0 10px;font-weight:950;letter-spacing:.08em;font-size:18px}
      .eclipse-mark{width:32px;height:32px;border-radius:11px;display:block;background:radial-gradient(circle at 38% 35%,#bda9ff 0 11%,transparent 12%),linear-gradient(145deg,#8d68ff,#4e2db8);box-shadow:0 8px 24px #6f4dff55;position:relative}
      .eclipse-mark:after{content:"";position:absolute;inset:7px;border-radius:50%;border:1px solid #fff5}
    `;
    document.head.appendChild(style);

    const brand = document.querySelector('.brand');
    if (brand) brand.innerHTML = '<span class="eclipse-mark"></span><span>ECLIPSE</span>';

    // Remove every old navigation/control surface except Arena.
    document.querySelectorAll('button,a,[role="button"]').forEach(el => {
      const text = (el.textContent || '').trim().toLowerCase();
      const forbidden = [
        'rocket','game 2','case','wallet','withdrawal','invite friends','support',
        'ракета','игра 2','кейс','кошелек','кошелёк','вывод','пригласить','поддержка'
      ];
      if (forbidden.some(word => text.includes(word))) el.classList.add('eclipse-hidden');
    });

    // Hide legacy feature containers that could remain in the DOM.
    ['crashMode','case','profile-card','history','.ref','#referrals','withdrawal','support'].forEach(selector => {
      document.querySelectorAll(selector).forEach(el => {
        if (el !== arenaMode && !arenaMode.contains(el)) el.classList.add('eclipse-hidden');
      });
    });

    // Keep only the Arena section visible inside the game area.
    document.querySelectorAll('#games > *').forEach(el => {
      if (el !== arenaMode) el.classList.add('eclipse-hidden');
    });

    const title = arenaMode.querySelector('.section-title h2,h1,h2');
    if (title && /rocket|game 2|crash|игра/i.test(title.textContent || '')) title.textContent = 'ARENA';

    const arenaTab = document.querySelector('.tabs button[data-mode="arena"]');
    if (arenaTab) arenaTab.click();

    const tg = window.Telegram?.WebApp;
    if (tg?.expand) tg.expand();
  };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true}); else boot();
})();
