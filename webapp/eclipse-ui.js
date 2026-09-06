(() => {
  const boot = () => {
    const app = document.querySelector('.app');
    if (!app) return;

    const oldTabs = document.querySelector('.tabs');
    const oldNav = document.querySelector('.nav');
    if (oldTabs) oldTabs.style.display = 'none';
    if (oldNav) oldNav.style.display = 'none';

    const brand = document.querySelector('.brand');
    if (brand) brand.innerHTML = '<span class="eclipse-mark"></span><span>ECLIPSE</span>';
    document.title = 'ECLIPSE';

    const style = document.createElement('style');
    style.textContent = `
      :root{--purple:#7c4dff;--purple2:#9a7bff;--e-bg:#0b0b10;--e-panel:#15151c;--e-muted:#8d8d9a}
      body{background:var(--e-bg)!important}
      .app{background:radial-gradient(circle at 50% -8%,#25173c 0,#101016 34%,#0b0b10 78%)!important}
      .eclipse-mark{width:34px;height:34px;border-radius:12px;display:block;background:radial-gradient(circle at 38% 35%,#bda9ff 0 11%,transparent 12%),linear-gradient(145deg,#8d68ff,#4e2db8);box-shadow:0 8px 24px #6f4dff55;position:relative}
      .eclipse-mark:after{content:"";position:absolute;inset:7px;border-radius:50%;border:1px solid #fff5}
      .eclipse-nav{position:fixed;z-index:900;left:0;right:0;bottom:0;padding:8px 8px calc(7px + env(safe-area-inset-bottom));background:#101016ee;border-top:1px solid #ffffff10;backdrop-filter:blur(16px);display:grid;grid-template-columns:repeat(4,1fr);gap:6px;box-shadow:0 -14px 35px #0009}
      .eclipse-nav button{height:44px;border-radius:13px;background:transparent;color:#81818e;font-size:11px;font-weight:850}
      .eclipse-nav button.active{background:#211a35;color:#fff;box-shadow:inset 0 0 0 1px #8c6cff44}
      .eclipse-nav button span{display:block;line-height:1.1}
      .eclipse-page{display:none}
      .eclipse-page.active{display:block}
      .eclipse-card{padding:16px;border-radius:22px;background:linear-gradient(145deg,#191720,#121219);border:1px solid #ffffff0c;margin-top:11px}
      .eclipse-card h2{margin:0 0 7px;font-size:20px}
      .eclipse-card p{margin:0;color:var(--e-muted);font-size:13px;line-height:1.45}
      .eclipse-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
      .eclipse-action{min-height:50px;border-radius:15px;background:#211d2c;color:#fff;border:1px solid #ffffff0a;font-weight:900}
      .eclipse-action.primary{background:linear-gradient(135deg,#805cff,#5d36d5)}
      .eclipse-action.ghost{background:#1b1b23}
      .eclipse-balance{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
      .eclipse-balance>div{padding:14px;border-radius:16px;background:#191920;border:1px solid #ffffff08}
      .eclipse-balance strong{display:block;font-size:22px;margin-top:3px}
      .eclipse-label{font-size:10px;color:#888896;text-transform:uppercase;letter-spacing:.08em}
      .eclipse-message{margin-top:10px;padding:12px;border-radius:14px;background:#171720;color:#b4b4c0;font-size:12px;line-height:1.4}
      .eclipse-share{word-break:break-all;padding:11px;border-radius:12px;background:#101017;color:#b8aaff;font-size:11px;margin-top:10px}
      .app{padding-bottom:calc(68px + env(safe-area-inset-bottom))!important}
    `;
    document.head.appendChild(style);

    const games = document.getElementById('games');
    if (!games) return;

    const rocket = document.getElementById('crashMode');
    const game2 = document.getElementById('arenaMode');
    const caseEl = document.querySelector('.case');
    const profile = document.querySelector('.profile-card');
    const refEl = document.querySelector('.ref');
    const history = document.querySelector('.history');

    const pages = {};
    const makePage = (id) => {
      const p = document.createElement('section');
      p.className = 'eclipse-page';
      p.id = `eclipse-${id}`;
      games.appendChild(p);
      pages[id] = p;
      return p;
    };
    const rocketPage = makePage('rocket');
    const game2Page = makePage('game2');
    const casePage = makePage('case');
    const walletPage = makePage('wallet');
    const withdrawalPage = makePage('withdrawal');
    const invitePage = makePage('invite');
    const supportPage = makePage('support');

    if (rocket) rocketPage.appendChild(rocket);
    if (game2) game2Page.appendChild(game2);
    if (caseEl) casePage.appendChild(caseEl);
    if (profile) walletPage.appendChild(profile);
    if (history) walletPage.appendChild(history);
    if (refEl) invitePage.appendChild(refEl);

    const withdrawalCard = document.createElement('div');
    withdrawalCard.className = 'eclipse-card';
    withdrawalCard.innerHTML = `<h2>Withdrawal</h2><p>TON withdrawal is handled only when a confirmed wallet and a supported payout provider are configured. No fake payout status is shown.</p><div class="eclipse-grid"><button class="eclipse-action ghost" id="eclipseWalletBtn">Wallet</button><button class="eclipse-action primary" id="eclipseTopUpBtn">Top up</button></div>`;
    withdrawalPage.appendChild(withdrawalCard);

    const supportCard = document.createElement('div');
    supportCard.className = 'eclipse-card';
    supportCard.innerHTML = `<h2>Support</h2><p>Need help with your account, deposits, or access? Contact the configured ECLIPSE support channel.</p><div class="eclipse-message">Support: @Eclipsed_consult</div>`;
    supportPage.appendChild(supportCard);

    const inviteIntro = document.createElement('div');
    inviteIntro.className = 'eclipse-card';
    inviteIntro.innerHTML = `<h2>Invite friends</h2><p>Invite a new Telegram account and receive <b>+1 Star</b> once. Each account can be counted only once.</p><div class="eclipse-share" id="eclipseInviteLink">Loading invite link…</div><div class="eclipse-grid"><button class="eclipse-action primary" id="eclipseShareBtn">Share</button><button class="eclipse-action ghost" id="eclipseCopyBtn">Copy</button></div>`;
    invitePage.prepend(inviteIntro);

    const walletExtra = document.createElement('div');
    walletExtra.className = 'eclipse-card';
    walletExtra.innerHTML = `<h2>Wallet</h2><p>Balances are shown from the server.</p><div class="eclipse-balance"><div><span class="eclipse-label">Stars</span><strong id="eclipseStars">0</strong></div><div><span class="eclipse-label">TON</span><strong id="eclipseTon">0</strong></div></div><div class="eclipse-grid"><button class="eclipse-action primary" id="eclipseDepositBtn">Top up</button><button class="eclipse-action ghost" id="eclipseWithdrawBtn">Withdrawal</button></div>`;
    walletPage.prepend(walletExtra);

    const nav = document.createElement('nav');
    nav.className = 'eclipse-nav';
    const items = [['rocket','Rocket'],['game2','Game 2'],['case','Case'],['wallet','Wallet'],['withdrawal','Withdrawal'],['invite','Invite friends'],['support','Support']];
    items.forEach(([id,label]) => {
      const b = document.createElement('button');
      b.type='button'; b.dataset.page=id; b.innerHTML=`<span>${label}</span>`;
      b.addEventListener('click',()=>show(id)); nav.appendChild(b);
    });
    document.body.appendChild(nav);

    function show(id){
      Object.values(pages).forEach(p=>p.classList.remove('active'));
      pages[id]?.classList.add('active');
      nav.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.page===id));
      window.scrollTo({top:0,behavior:'smooth'});
      if(id==='case') document.getElementById('openCase')?.scrollIntoView({block:'nearest'});
      if(id==='wallet') refreshMe();
      if(id==='invite') refreshInvite();
    }

    async function refreshMe(){
      try{
        const tg=window.Telegram?.WebApp;
        const r=await fetch('/api/me',{headers:tg?.initData?{'X-Telegram-Init-Data':tg.initData}:{}});
        if(!r.ok)return;
        const d=await r.json();
        const stars=Number(d.profile?.balance||0); const ton=Number(d.profile?.ton_balance||0);
        const s=document.getElementById('eclipseStars'); const t=document.getElementById('eclipseTon');
        if(s)s.textContent=stars.toFixed(2); if(t)t.textContent=ton.toFixed(4);
        const top=document.getElementById('topStars'); if(top)top.textContent=stars.toFixed(2);
      }catch(e){}
    }
    async function refreshInvite(){
      try{
        const tg=window.Telegram?.WebApp;
        const r=await fetch('/api/referrals',{headers:tg?.initData?{'X-Telegram-Init-Data':tg.initData}:{}});
        if(!r.ok)return; const d=await r.json();
        const el=document.getElementById('eclipseInviteLink'); if(el)el.textContent=d.link||'Invite link unavailable';
      }catch(e){}
    }
    const openDeposit=()=>document.getElementById('topDeposit')?.click();
    document.getElementById('eclipseDepositBtn')?.addEventListener('click',openDeposit);
    document.getElementById('eclipseTopUpBtn')?.addEventListener('click',openDeposit);
    document.getElementById('eclipseWalletBtn')?.addEventListener('click',()=>show('wallet'));
    document.getElementById('eclipseWithdrawBtn')?.addEventListener('click',()=>show('withdrawal'));
    document.getElementById('eclipseShareBtn')?.addEventListener('click',async()=>{
      const tg=window.Telegram?.WebApp; const link=document.getElementById('eclipseInviteLink')?.textContent||'';
      if(tg?.openTelegramLink && link){ tg.openTelegramLink('https://t.me/share/url?url='+encodeURIComponent(link)); }
      try{await fetch('/api/share',{method:'POST',headers:tg?.initData?{'X-Telegram-Init-Data':tg.initData}:{} });}catch(e){}
    });
    document.getElementById('eclipseCopyBtn')?.addEventListener('click',async()=>{
      try{await navigator.clipboard.writeText(document.getElementById('eclipseInviteLink')?.textContent||'');}catch(e){}
    });

    show('rocket');
    refreshMe();
  };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true}); else boot();
})();
