const tg = window.Telegram.WebApp;
tg.expand();

const userId = tg.initDataUnsafe?.user?.id || 12345678;
let ws;
let isBetPlaced = false;
let hasCashedOut = false;

function connectWS() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const statusText = document.getElementById('crash-status');
        const multText = document.getElementById('crash-mult');
        const btn = document.getElementById('action-btn');
        const rocket = document.getElementById('rocket');

        if (data.type === 'tick') {
            statusText.innerText = `Взлет через: ${data.time} сек`;
            multText.innerText = "x1.00";
            if (!isBetPlaced) {
                btn.innerText = "Сделать ставку";
                btn.className = "btn btn-primary";
                btn.disabled = false;
            }
        } 
        else if (data.type === 'fly') {
            statusText.innerText = "ПОЛЕТ!";
            multText.innerText = `x${data.multiplier.toFixed(2)}`;
            rocket.style.transform = `translateY(-${Math.min((data.multiplier - 1) * 15, 50)}px)`;

            if (isBetPlaced && !hasCashedOut) {
                btn.innerText = "ЗАБРАТЬ (-10%)";
                btn.className = "btn btn-cashout";
                btn.disabled = false;
            }
        } 
        else if (data.type === 'crash') {
            statusText.innerText = "💥 ВЗРЫВ!";
            multText.innerText = `x${data.multiplier.toFixed(2)}`;
            rocket.style.transform = "translateY(0px)";
            btn.innerText = "Ожидание...";
            btn.disabled = true;

            isBetPlaced = false;
            hasCashedOut = false;
            loadUserData();
        } 
        else if (data.type === 'cashout_success') {
            hasCashedOut = true;
            document.getElementById('star-balance').innerText = data.stars;
            document.getElementById('game-result').innerText = `🎉 Забрано: ${data.win} ⭐ (комиссия 10%)`;
            btn.innerText = "Успешно!";
            btn.disabled = true;
        }
        else if (data.type === 'battle_update') {
            renderBattle(data.game);
        }
    };

    ws.onclose = () => setTimeout(connectWS, 1000);
}

function handleGameAction() {
    const btn = document.getElementById('action-btn');
    const bet = parseInt(document.getElementById('crash-bet').value);

    if (!isBetPlaced) {
        isBetPlaced = true;
        btn.innerText = "Ставка принята";
        btn.disabled = true;
    } else if (!hasCashedOut) {
        ws.send(JSON.stringify({ action: "cashout", user_id: userId, bet: bet }));
    }
}

function setBattleBet(val) {
    document.getElementById('battle-bet').value = val;
}

async function joinBattle() {
    const bet = parseInt(document.getElementById('battle-bet').value);
    const userName = tg.initDataUnsafe?.user?.first_name || "Игрок";

    const res = await fetch('/api/battle/join', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ user_id: userId, name: userName, bet: bet })
    });
    
    const data = await res.json();
    if (res.status !== 200) {
        tg.showAlert(data.error);
    } else {
        renderBattle(data.game);
        loadUserData();
    }
}

function renderBattle(game) {
    document.getElementById('battle-total-bank').innerText = game.total_bank;
    
    const list = document.getElementById('players-list');
    list.innerHTML = "";
    game.players.forEach(p => {
        list.innerHTML += `
            <div class="player-item" style="border-left: 4px solid ${p.color}">
                <div>
                    <strong>${p.name}</strong><br>
                    <small style="color: #aaa">Шанс ${p.chance}%</small>
                </div>
                <div>⭐ ${p.bet}</div>
            </div>
        `;
    });

    const canvas = document.getElementById('battleCanvas');
    const ctx = canvas.getContext('2d');
    let startAngle = 0;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    game.players.forEach(p => {
        const sliceAngle = (p.chance / 100) * 2 * Math.PI;
        ctx.beginPath();
        ctx.fillStyle = p.color;
        ctx.moveTo(110, 110);
        ctx.arc(110, 110, 100, startAngle, startAngle + sliceAngle);
        ctx.closePath();
        ctx.fill();
        startAngle += sliceAngle;
    });
}

async function payWithTon() {
    const amount = parseFloat(document.getElementById('ton-amount').value);
    if (!amount || amount <= 0) {
        tg.showAlert("Введите корректную сумму TON");
        return;
    }

    const walletAddress = "UQA6OOWd_V_-asdDgsjiHK3OYTp-FjGihgFNxpSg__dHM1h8";
    const tonUrl = `ton://transfer/${walletAddress}?amount=${amount * 1e9}&text=GiftsMMS_${userId}`;
    tg.openLink(tonUrl);

    const res = await fetch('/api/deposit/ton', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ user_id: userId, amount: amount })
    });
    
    const data = await res.json();
    if (res.status === 200) {
        tg.showAlert(`Успешно! Зачислено ${data.added_stars} ⭐ (удержано 5% комиссии).`);
        loadUserData();
    }
}

async function requestGift(giftName) {
    const res = await fetch('/api/request_gift', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ user_id: userId, gift_name: giftName })
    });
    const data = await res.json();
    if (res.status === 200) {
        tg.showAlert("Заявка отправлена администратору!");
        loadUserData();
    } else {
        tg.showAlert(data.error);
    }
}

async function loadUserData() {
    const res = await fetch(`/api/user?user_id=${userId}`);
    const data = await res.json();
    document.getElementById('star-balance').innerText = data.stars;
}

function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tab}`).classList.add('active');
    document.getElementById(`nav-${tab}`).classList.add('active');
}

loadUserData();
connectWS();
