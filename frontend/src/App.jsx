import { useEffect, useMemo, useState } from 'react';
import { api } from './api';

const tg = () => window.Telegram?.WebApp;

export default function App() {
  const [profile, setProfile] = useState(null);
  const [arena, setArena] = useState(null);
  const [referrals, setReferrals] = useState(null);
  const [tab, setTab] = useState('game');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      setError('');
      const [me, battle, refs] = await Promise.all([api.me(), api.arena(), api.referrals()]);
      setProfile(me.profile);
      setArena(battle);
      setReferrals(refs);
    } catch (e) { setError(e.message || 'Не удалось загрузить данные'); }
  };

  useEffect(() => {
    tg()?.expand?.();
    load();
    const timer = setInterval(async () => {
      try { setArena(await api.arena()); } catch (_) {}
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const countdown = useMemo(() => {
    if (!arena?.countdown_end) return 0;
    return Math.max(0, Number(arena.countdown_end) - Math.floor(Date.now() / 1000));
  }, [arena]);

  const tap = async () => {
    if (busy) return;
    setBusy(true);
    try {
      // Gameplay remains server-authoritative; this UI action is deliberately non-cash.
      await api.joinArena(25);
      await load();
    } catch (e) { setError(e.message || 'Попробуйте ещё раз'); }
    finally { setBusy(false); }
  };

  const invite = async () => {
    const link = referrals?.link;
    if (!link) return;
    try { await navigator.clipboard.writeText(link); } catch (_) {}
    tg()?.showPopup?.({ title: 'Реферальная ссылка', message: link, buttons: [{ type: 'close' }] });
  };

  return <main className="app">
    <header className="topbar">
      <div><span className="muted">Баланс</span><h1>{Number(profile?.balance || 0).toLocaleString('ru-RU')} ◆</h1></div>
      <div className="avatar">{profile?.username ? profile.username[0].toUpperCase() : '◆'}</div>
    </header>

    {error && <div className="error">{error}</div>}

    {tab === 'game' && <section className="stack">
      <div className="hero card">
        <span className="pill">LIVE ARENA</span>
        <h2>Игра с реальными игроками</h2>
        <p>Виртуальные очки, без ставок на деньги. Новый раунд начинается только при двух реальных игроках.</p>
        <div className="ball" onClick={tap} role="button" aria-label="Играть">⚽</div>
        <div className="timer">{arena?.status === 'waiting' ? `До начала ${countdown} сек.` : arena?.status === 'active' ? `Раунд ${countdown} сек.` : 'Новый раунд'}</div>
        <button className="primary" disabled={busy} onClick={tap}>{busy ? 'Подключение…' : 'Участвовать · 25 ◆'}</button>
      </div>

      <div className="card players">
        <div className="row"><b>Игроки</b><span>{arena?.players?.length || 0}/{arena?.min_players || 2}</span></div>
        {(arena?.players || []).map((player) => <div className="player" key={player.user_id}><span className="dot"/><span>{player.name}</span><b>{player.bet} ◆</b></div>)}
        {!arena?.players?.length && <div className="empty">Ждём первого игрока</div>}
      </div>
    </section>}

    {tab === 'gifts' && <section className="stack"><div className="card"><span className="pill">GIFTS</span><h2>Подарки</h2><p>Раздел для цифровых наград и внутриигровых предметов. Денежные розыгрыши здесь не используются.</p><button className="primary" onClick={() => tg()?.showAlert?.('Каталог подарков подключается к Telegram Stars.')}>Открыть подарки</button></div></section>}

    {tab === 'refs' && <section className="stack"><div className="card"><span className="pill">REFERRALS</span><h2>Приглашай друзей</h2><p>За каждого приглашённого пользователя начисляется <b>0.85 ⭐</b>.</p><div className="stat">{referrals?.count || 0}<span> приглашённых</span></div><button className="primary" onClick={invite}>Скопировать ссылку</button></div></section>}

    <nav className="nav">
      <button className={tab === 'game' ? 'active' : ''} onClick={() => setTab('game')}>⚽<span>Игра</span></button>
      <button className={tab === 'gifts' ? 'active' : ''} onClick={() => setTab('gifts')}>🎁<span>Подарки</span></button>
      <button className={tab === 'refs' ? 'active' : ''} onClick={() => setTab('refs')}>👥<span>Рефералы</span></button>
    </nav>
  </main>;
}
