import secrets

def play(stake: int, chance: float):
    if not 1 <= chance <= 99:
        raise ValueError("chance must be between 1 and 99")
    coefficient = round(100 / chance * 0.975, 4)
    roll = secrets.randbelow(100) + 1
    win = roll <= chance
    delta = int(stake * (coefficient - 1)) if win else -stake
    return {"roll": roll, "win": win, "coefficient": coefficient, "delta": delta}
