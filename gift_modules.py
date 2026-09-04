import json
import random
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.filters import Command

router = Router()

# Список Telegram ID администраторов (замените на свой ID)
ADMIN_IDS = [123456789]

# Адрес горячего кошелька бота для приема средств
BOT_TON_WALLET = "EQ_ВАШ_АДРЕС_КОШЕЛЬКА_БОТА"

# Лимиты
MIN_WITHDRAW_TON = 1.0
MIN_DEPOSIT_TON = 0.1


# ==================== 1. ИНИЦИАЛИЗАЦИЯ ТАБЛИЦ БД ====================

async def init_db_tables(db_pool):
    """Создание всех необходимых таблиц в PostgreSQL / SQLite"""
    async with db_pool.acquire() as conn:
        # Пользователи
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                ton_balance NUMERIC DEFAULT 0,
                stars_balance NUMERIC DEFAULT 0,
                referrer_id BIGINT NULL,
                ref_count INT DEFAULT 0,
                last_free_spin TIMESTAMP NULL
            );
        """)
        
        # NFT Инвентарь
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_nfts (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                title VARCHAR(255) NOT NULL,
                status VARCHAR(50) DEFAULT 'available', -- 'available', 'on_market'
                price_ton NUMERIC DEFAULT 0
            );
        """)
        
        # Активные сессии игры «Мины»
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS mine_games (
                user_id BIGINT PRIMARY KEY,
                field JSONB NOT NULL,
                bet_amount NUMERIC NOT NULL,
                step INT DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE
            );
        """)

        # Транзакции (Пополнение и Вывод)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                type VARCHAR(20) NOT NULL, -- 'deposit' или 'withdraw'
                amount NUMERIC NOT NULL,
                wallet_address VARCHAR(255) NULL,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)


# ==================== 2. СТАРТ И РЕФЕРАЛКА (0.85 ⭐) ====================

@router.message(Command("start"))
async def start_cmd(message: types.Message, db_pool):
    """Команда /start с обработкой реферального перехода"""
    user_id = message.from_user.id
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    referrer_id = int(args[0]) if args and args[0].isdigit() and int(args[0]) != user_id else None

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            user_exists = await conn.fetchval("SELECT user_id FROM users WHERE user_id = $1", user_id)
            
            if not user_exists:
                await conn.execute(
                    "INSERT INTO users (user_id, referrer_id) VALUES ($1, $2)",
                    user_id, referrer_id
                )
                
                # Начисление 0.85 звезд пригласившему
                if referrer_id:
                    await conn.execute("""
                        UPDATE users 
                        SET stars_balance = stars_balance + 0.85, 
                            ref_count = ref_count + 1 
                        WHERE user_id = $1
                    """, referrer_id)
                    
                    try:
                        await message.bot.send_message(
                            referrer_id, 
                            f"🎉 По вашей ссылке зарегистрировался новый пользователь! Вам начислено **0.85 ⭐**"
                        )
                    except Exception:
                        pass

    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="👥 Профиль & Рефералы", callback_data="ref_system")],
        [types.InlineKeyboardButton(text="💳 Пополнить (от 0.1 TON)", callback_data="deposit_ton")],
        [types.InlineKeyboardButton(text="🎁 Инвентарь", callback_data="inventory"), types.InlineKeyboardButton(text="🛒 Рынок", callback_data="open_market")],
        [types.InlineKeyboardButton(text="💣 «Мины»", callback_data="start_mines"), types.InlineKeyboardButton(text="🎁 0.1 TON Бонус", callback_data="daily_free_spin")]
    ])

    await message.answer(
        f"👋 **Добро пожаловать в GiftsEzz!**\n\n"
        f"🔗 Ваша реферальная ссылка:\n`{ref_link}`\n\n"
        f"За каждого приглашённого друга вы получаете **0.85 ⭐**!",
        reply_markup=kb,
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "ref_system")
async def show_ref_info(callback: types.CallbackQuery, db_pool):
    """Профиль пользователя и реферальная статистика"""
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT stars_balance, ref_count, ton_balance FROM users WHERE user_id = $1", 
            callback.from_user.id
        )
        
    stars = user['stars_balance'] if user else 0
    refs = user['ref_count'] if user else 0
    ton = user['ton_balance'] if user else 0
    
    bot_info = await callback.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={callback.from_user.id}"

    text = (
        f"📊 **Ваш профиль**\n\n"
        f"⭐ Баланс Звёзд: **{stars:.2f} ⭐**\n"
        f"💎 Баланс TON: **{ton:.2f} TON**\n"
        f"👥 Приглашено друзей: **{refs}**\n\n"
        f"💸 Награда за друга: **0.85 ⭐**\n"
        f"📤 Вывод TON доступен от **{MIN_WITHDRAW_TON} TON** (команда `/withdraw`)\n\n"
        f"🔗 Ссылка для приглашения:\n`{ref_link}`"
    )
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💳 Пополнить TON", callback_data="deposit_ton")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


# ==================== 3. ПОПОЛНЕНИЕ И ВЫВОД TON ====================

@router.callback_query(F.data == "deposit_ton")
async def show_deposit_info(callback: types.CallbackQuery):
    """Информация о пополнении TON (от 0.1 TON)"""
    user_id = callback.from_user.id
    
    text = (
        f"💳 **Пополнение баланса TON**\n\n"
        f"🔹 Минимальная сумма: **{MIN_DEPOSIT_TON} TON**\n\n"
        f"Переведите TON на кошелёк бота:\n"
        f"`{BOT_TON_WALLET}`\n\n"
        f"⚠️ **КРИТИЧЕСКИ ВАЖНО:**\n"
        f"В поле «Комментарий» (Memo) перевода обязательно укажите:\n"
        f"`dep_{user_id}`\n\n"
        f" Без этого комментария пополнение не зачислится!"
    )
    await callback.message.edit_text(text, parse_mode="Markdown")


@router.message(Command("withdraw"))
async def process_withdraw_request(message: types.Message, db_pool):
    """Вывод TON (от 1.0 TON)"""
    args = message.text.split()
    
    if len(args) < 3:
        await message.answer(
            f"⚠️ **Формат вывода:**\n`/withdraw АДРЕС_КОШЕЛЬКА СУММА`\n\n"
            f"🔹 Минимальный вывод: **{MIN_WITHDRAW_TON} TON**",
            parse_mode="Markdown"
        )
        return

    wallet_address = args[1]
    try:
        amount = float(args[2])
    except ValueError:
        await message.answer("❌ Некорректная сумма.")
        return

    if amount < MIN_WITHDRAW_TON:
        await message.answer(f"❌ Минимальная сумма вывода — **{MIN_WITHDRAW_TON} TON**.")
        return

    user_id = message.from_user.id

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            user_balance = await conn.fetchval(
                "SELECT ton_balance FROM users WHERE user_id = $1 FOR UPDATE", 
                user_id
            ) or 0

            if user_balance < amount:
                await message.answer(f"❌ Недостаточно средств! Ваш баланс: **{user_balance:.2f} TON**.")
                return

            # Списание баланса
            await conn.execute(
                "UPDATE users SET ton_balance = ton_balance - $1 WHERE user_id = $2", 
                amount, user_id
            )
            
            # Регистрация заявки
            await conn.execute(
                "INSERT INTO transactions (user_id, type, amount, wallet_address, status) VALUES ($1, 'withdraw', $2, $3, 'success')",
                user_id, amount, wallet_address
            )

    await message.answer(
        f"✅ **Заявка на вывод создана!**\n\n"
        f"💸 Отправка: **{amount} TON**\n"
        f"📍 На адрес: `{wallet_address}`",
        parse_mode="Markdown"
    )


# ==================== 4. ИНВЕНТАРЬ И РЫНОК ====================

@router.callback_query(F.data == "inventory")
async def show_inventory(callback: types.CallbackQuery, db_pool):
    async with db_pool.acquire() as conn:
        nfts = await conn.fetch(
            "SELECT id, title, status FROM user_nfts WHERE user_id = $1 AND status = 'available'",
            callback.from_user.id
        )
    
    if not nfts:
        await callback.message.edit_text("Ваш инвентарь пуст.")
        return

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=f"Продать: {nft['title']}", callback_data=f"sell_nft_{nft['id']}")]
        for nft in nfts
    ])
    await callback.message.edit_text("🎁 **Ваш инвентарь NFT:**", reply_markup=kb)


@router.callback_query(F.data.startswith("sell_nft_"))
async def list_on_market(callback: types.CallbackQuery, db_pool):
    nft_id = int(callback.data.split("_")[2])
    price = 5.0

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            updated = await conn.execute(
                "UPDATE user_nfts SET status = 'on_market', price_ton = $1 WHERE id = $2 AND user_id = $3 AND status = 'available'",
                price, nft_id, callback.from_user.id
            )
            if updated == "UPDATE 0":
                await callback.answer("Ошибка: предмет недоступен для продажи.", show_alert=True)
                return

    await callback.answer(f"NFT выставлен на рынок за {price} TON!", show_alert=True)


@router.callback_query(F.data == "open_market")
async def show_market(callback: types.CallbackQuery, db_pool):
    async with db_pool.acquire() as conn:
        market_items = await conn.fetch("""
            SELECT id, title, price_ton, user_id 
            FROM user_nfts 
            WHERE status = 'on_market' AND user_id != $1 
            LIMIT 10
        """, callback.from_user.id)

    if not market_items:
        await callback.message.edit_text("🛒 Рынок пуст.")
        return

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text=f"Купить {item['title']} — {item['price_ton']} TON", 
            callback_data=f"buy_nft_{item['id']}"
        )]
        for item in market_items
    ])
    await callback.message.edit_text("🛒 **Рынок NFT:**", reply_markup=kb)


@router.callback_query(F.data.startswith("buy_nft_"))
async def buy_nft_process(callback: types.CallbackQuery, db_pool):
    nft_id = int(callback.data.split("_")[2])
    buyer_id = callback.from_user.id

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            nft = await conn.fetchrow(
                "SELECT id, title, price_ton, user_id FROM user_nfts WHERE id = $1 AND status = 'on_market' FOR UPDATE",
                nft_id
            )
            
            if not nft:
                await callback.answer("Предмет недоступен.", show_alert=True)
                return

            price = nft['price_ton']
            seller_id = nft['user_id']

            buyer_balance = await conn.fetchval("SELECT ton_balance FROM users WHERE user_id = $1", buyer_id) or 0
            if buyer_balance < price:
                await callback.answer(f"Недостаточно TON! Требуется: {price} TON", show_alert=True)
                return

            await conn.execute("UPDATE users SET ton_balance = ton_balance - $1 WHERE user_id = $2", price, buyer_id)
            await conn.execute("UPDATE users SET ton_balance = ton_balance + $1 WHERE user_id = $2", price, seller_id)
            await conn.execute(
                "UPDATE user_nfts SET user_id = $1, status = 'available', price_ton = 0 WHERE id = $2",
                buyer_id, nft_id
            )

    await callback.answer(f"Вы купили {nft['title']} за {price} TON!", show_alert=True)


# ==================== 5. БОНУС И ИГРЫ ====================

@router.callback_query(F.data == "daily_free_spin")
async def process_daily_spin(callback: types.CallbackQuery, db_pool):
    user_id = callback.from_user.id
    async with db_pool.acquire() as conn:
        last_spin = await conn.fetchval("SELECT last_free_spin FROM users WHERE user_id = $1", user_id)
        
        now = datetime.utcnow()
        if last_spin and now < last_spin + timedelta(hours=24):
            time_left = (last_spin + timedelta(hours=24)) - now
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes = remainder // 60
            await callback.answer(f"Бонус доступен через {hours}ч {minutes}мин.", show_alert=True)
            return

        async with conn.transaction():
            await conn.execute(
                "INSERT INTO users (user_id, ton_balance, last_free_spin) VALUES ($1, 0.1, $2) "
                "ON CONFLICT (user_id) DO UPDATE SET ton_balance = users.ton_balance + 0.1, last_free_spin = $2",
                user_id, now
            )
            
    await callback.answer("Вы получили 0.1 TON!", show_alert=True)


@router.callback_query(F.data == "start_mines")
async def start_mines_game(callback: types.CallbackQuery, db_pool):
    user_id = callback.from_user.id
    mines_count, field_size = 3, 25
    
    field = [False] * field_size
    for pos in random.sample(range(field_size), mines_count):
        field[pos] = True

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO mine_games (user_id, field, bet_amount, step, is_active)
            VALUES ($1, $2, 0.1, 0, TRUE)
            ON CONFLICT (user_id) DO UPDATE 
            SET field = $2, bet_amount = 0.1, step = 0, is_active = TRUE
        """, user_id, json.dumps(field))

    await callback.message.edit_text("💣 **Игра «Мины» началась!**")


# ==================== 6. АДМИН-ПАНЕЛЬ ====================

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    text = (
        "⚙️ **Панель Администратора**\n\n"
        "• `/give_nft USER_ID Название` — выдать NFT\n"
        "• `/give_stars USER_ID Кол-во` — начислить Звёзды"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("give_nft"))
async def give_nft_cmd(message: types.Message, db_pool):
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Формат: `/give_nft 123456789 Золотой Подарок`", parse_mode="Markdown")
        return

    target_user_id, nft_title = int(args[1]), args[2]

    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO user_nfts (user_id, title, status) VALUES ($1, $2, 'available')",
            target_user_id, nft_title
        )

    await message.answer(f"✅ NFT **{nft_title}** отправлен пользователю `{target_user_id}`!")


@router.message(Command("give_stars"))
async def give_stars_cmd(message: types.Message, db_pool):
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split()
    if len(args) < 3:
        await message.answer("Формат: `/give_stars 123456789 50`", parse_mode="Markdown")
        return

    target_user_id, amount = int(args[1]), float(args[2])

    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET stars_balance = stars_balance + $1 WHERE user_id = $2",
            amount, target_user_id
        )

    await message.answer(f"⭐ Начислено **{amount}** звёзд пользователю `{target_user_id}`!")


# ==================== 7. РЕГИСТРАЦИЯ МОДУЛЯ ====================

def register_handlers(dp):
    dp.include_router(router)
