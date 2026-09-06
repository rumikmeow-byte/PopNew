# Render startup compatibility and ECLIPSE referral reward patch.
import aiosqlite
import builtins
import db as _db

# Some existing modules call init_db through the builtins compatibility hook.
builtins.init_db = _db.init_db

_original_add_referral = _db.add_referral


async def _eclipse_add_referral(inviter_id: int, invited_id: int):
    created = await _original_add_referral(inviter_id, invited_id)
    if not created:
        return False
    async with aiosqlite.connect(_db.DB_NAME) as conn:
        await conn.execute(
            "UPDATE users SET balance=balance+0.15, ref_earned=ref_earned+0.15 WHERE user_id=?",
            (inviter_id,),
        )
        await conn.commit()
    return True


_db.add_referral = _eclipse_add_referral
