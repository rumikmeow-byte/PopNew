# GiftsMMS Bot Extension Module

Модуль добавляет в Telegram-бота функции работы с NFT-подарками и мини-игры.

## Содержимое
- **Инвентарь**: просмотр подарков, вывод на рынок и запуск в стейкинг.
- **Стейкинг**: заморозка NFT на 7 дней под 53% APR (выплаты в GRAM).
- **Рынок**: покупка и продажа NFT за TON.
- **Игры**: «Мины», «Апгрейд» и ежедневная бесплатная ставка (0.1 TON раз в 24 часа).

## Подключение в main.py
```python
from gift_modules import register_handlers, init_db_tables

# При старте приложения:
await init_db_tables(db_pool)
register_handlers(dp)
