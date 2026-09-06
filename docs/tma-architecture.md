# PopNew / GiftsEZZ — TMA architecture

## 1. Components

- **Telegram bot:** Python + aiogram 3.x (`main.py`, `user_handlers.py`).
- **API:** aiohttp routes in `main.py`.
- **Auth:** Telegram Web App `initData` is validated with HMAC-SHA256 before API access.
- **Database:** SQLite through `aiosqlite` for users, referrals, deposits and virtual arena state.
- **TMA frontend:** React + Vite + Tailwind CSS in `frontend/`.
- **Telegram SDK:** `@telegram-apps/sdk` bootstraps the Mini App and reads Telegram launch parameters.

## 2. Referral flow

The Mini App generates `https://t.me/<bot>?startapp=ref_<telegram_user_id>`. Telegram passes the launch parameter in Web App init data. `/api/me` validates the signed init data and processes the referral once. The existing bot `/start ref_<id>` flow remains compatible.

Referral reward is **0.85 ⭐** per successful referred user.

## 3. Game flow

The public arena is multiplayer and server-authoritative. It shows real Telegram users and a countdown. A round needs at least two real players. It uses virtual points only; there is no cash wagering or cash-out logic in the arena.

## 4. Telegram setup

1. Create the bot in `@BotFather`.
2. Set the bot token as `BOT_TOKEN`.
3. Add the bot as an administrator of `@eclipsedlf` so membership checks work reliably.
4. Set `WEBAPP_URL` to the HTTPS URL of the deployed Mini App.
5. In BotFather, configure the Mini App/menu button to the same HTTPS URL.
6. For the React frontend, run `cd frontend && npm install && npm run build`.

## 5. Required backend environment

- `BOT_TOKEN`
- `ADMIN_ID`
- `WEBAPP_URL` (for the bot's `/open` command)
- `DB_NAME` (optional, defaults to `data/bot.db`)
- Stars/TON variables only for legitimate digital-goods deposits; they are not used as arena wagers.

## 6. Local development

Backend:

```bash
pip install -r requirements.txt
python main.py
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

For Telegram, the production frontend must be served over HTTPS. If the existing aiohttp web UI remains the deployed UI, the React frontend is an isolated, buildable replacement ready to be wired to the same API endpoints.
