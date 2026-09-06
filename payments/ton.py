# TON integration placeholder.
# TON may be used only for purchasing non-redeemable virtual credits.

class TonPayments:
    async def create_payment(self, user_id: int, credits: int):
        raise NotImplementedError("Configure your TON payment provider before enabling purchases")
