import random
import time
from urllib.parse import quote

import aiosqlite
from aiohttp import web


class MiniAppFeatures:
    def __init__(self, db_name, bot):
        self.db_name = db_name
        self.bot = bot

    async def init(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS mini_users (user_id INTEGER PRIMARY KEY, tickets INTEGER DEFAULT 5)")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_tasks (task_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, reward INTEGER NOT NULL, kind TEXT NOT NULL, url TEXT DEFAULT '')")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_task_claims (user_id INTEGER, task_id INTEGER, claimed_at INTEGER, PRIMARY KEY(user_id, task_id))")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kind TEXT, title TEXT, amount TEXT, created_at INTEGER)")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_contest_entries (contest_id INTEGER, user_id INTEGER, tickets INTEGER, created_at INTEGER, PRIMARY KEY(contest_id,user_id))")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_contests (contest_id INTEGER PRIMARY KEY, title TEXT, prize TEXT, entry_tickets INTEGER, ends_at INTEGER, active INTEGER DEFAULT 1)")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_case_opens (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, case_id TEXT, reward TEXT, created_at INTEGER)")
            await db.execute("CREATE TABLE IF NOT EXISTS mini_leaderboard (user_id INTEGER PRIMARY KEY, score INTEGER DEFAULT 0)")
            tasks = await db.execute("SELECT COUNT(*) FROM mini_tasks")
            count = (await tasks.fetchone())[0]
            if count == 0:
                await db.executemany("INSERT INTO mini_tasks(title,reward,kind,url) VALUES(?,?,?,?)", [
                    ("Подпишись на GIFTSMMS News", 1, "subscribe", "https://t.me/GIFTSMMSNews"),
                    ("Поделись GIFTSMMS с другом", 5, "share", ""),
                    ("Открой Mini App", 2, "visit", ""),
                ])
            contest = await db.execute("SELECT COUNT(*) FROM mini_contests")
            if (await contest.fetchone())[0] == 0:
                await db.execute("INSERT INTO mini_contests VALUES(1,?,?,?,?,1)", ("GIFTSMMS Weekly", "1000 ⭐", 5, int(time.time()) + 7 * 86400))
            await db.commit()

    async def _user(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT OR IGNORE INTO mini_users(user_id,tickets) VALUES(?,5)", (user_id,))
            await db.execute("INSERT OR IGNORE INTO mini_leaderboard(user_id,score) VALUES(?,0)", (user_id,))
            await db.commit()
            async with db.execute("SELECT tickets FROM mini_users WHERE user_id=?", (user_id,)) as c:
                tickets = (await c.fetchone())[0]
        return tickets

    async def snapshot(self, user_id):
        tickets = await self._user(user_id)
        now = int(time.time())
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT task_id,title,reward,kind,url FROM mini_tasks ORDER BY task_id") as c:
                tasks = [{"id":r[0],"title":r[1],"reward":r[2],"kind":r[3],"url":r[4]} for r in await c.fetchall()]
            async with db.execute("SELECT task_id FROM mini_task_claims WHERE user_id=?", (user_id,)) as c:
                claimed = {r[0] for r in await c.fetchall()}
            async with db.execute("SELECT contest_id,title,prize,entry_tickets,ends_at FROM mini_contests WHERE active=1 ORDER BY contest_id LIMIT 1") as c:
                contest = await c.fetchone()
            async with db.execute("SELECT user_id,score FROM mini_leaderboard ORDER BY score DESC, user_id LIMIT 20") as c:
                leaders = [{"user_id":r[0],"score":r[1]} for r in await c.fetchall()]
            async with db.execute("SELECT id,kind,title,amount,created_at FROM mini_history WHERE user_id=? ORDER BY id DESC LIMIT 20", (user_id,)) as c:
                history = [{"id":r[0],"kind":r[1],"title":r[2],"amount":r[3],"created_at":r[4]} for r in await c.fetchall()]
            async with db.execute("SELECT case_id,reward,created_at FROM mini_case_opens WHERE user_id=? ORDER BY id DESC LIMIT 12", (user_id,)) as c:
                case_history = [{"case_id":r[0],"reward":r[1],"created_at":r[2]} for r in await c.fetchall()]
            entry = None
            if contest:
                async with db.execute("SELECT tickets FROM mini_contest_entries WHERE contest_id=? AND user_id=?", (contest[0],user_id)) as c:
                    row = await c.fetchone(); entry = row[0] if row else 0
        return {"tickets":tickets,"tasks":tasks,"claimed_tasks":list(claimed),"contest":({"id":contest[0],"title":contest[1],"prize":contest[2],"entry_tickets":contest[3],"ends_at":contest[4],"my_tickets":entry} if contest else None),"leaders":leaders,"history":history,"case_history":case_history,"now":now}

    async def claim_task(self, user_id, task_id):
        await self._user(user_id)
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT title,reward,kind,url FROM mini_tasks WHERE task_id=?", (task_id,)) as c:
                task = await c.fetchone()
            if not task: return {"ok":False,"message":"Задание не найдено"}
            async with db.execute("SELECT 1 FROM mini_task_claims WHERE user_id=? AND task_id=?", (user_id,task_id)) as c:
                if await c.fetchone(): return {"ok":True,"already":True,"message":"Награда уже получена"}
            # Verification is deliberately server-side and idempotent; channel subscription is checked for subscribe tasks.
            if task[2] == "subscribe":
                try:
                    member = await self.bot.get_chat_member("@GIFTSMMSNews", user_id)
                    if member.status not in ("member","administrator","creator"):
                        return {"ok":False,"message":"Сначала подпишитесь на @GIFTSMMSNews"}
                except Exception:
                    return {"ok":False,"message":"Не удалось проверить подписку. Попробуйте ещё раз."}
            await db.execute("INSERT INTO mini_task_claims VALUES(?,?,?)", (user_id,task_id,int(time.time())))
            await db.execute("UPDATE mini_users SET tickets=tickets+? WHERE user_id=?", (task[1],user_id))
            await db.execute("UPDATE mini_leaderboard SET score=score+? WHERE user_id=?", (task[1],user_id))
            await db.execute("INSERT INTO mini_history(user_id,kind,title,amount,created_at) VALUES(?,?,?,?,?)", (user_id,"task",task[0],f"+{task[1]} 🎫",int(time.time())))
            await db.commit()
        return {"ok":True,"reward":task[1],"message":"Награда получена ✅"}

    async def enter_contest(self, user_id):
        await self._user(user_id)
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT contest_id,entry_tickets,ends_at FROM mini_contests WHERE active=1 ORDER BY contest_id LIMIT 1") as c: contest=await c.fetchone()
            if not contest or contest[2] <= int(time.time()): return {"ok":False,"message":"Конкурс завершён"}
            async with db.execute("SELECT tickets FROM mini_users WHERE user_id=?",(user_id,)) as c: tickets=(await c.fetchone())[0]
            if tickets < contest[1]: return {"ok":False,"message":"Недостаточно билетов"}
            await db.execute("UPDATE mini_users SET tickets=tickets-? WHERE user_id=?",(contest[1],user_id))
            await db.execute("INSERT OR REPLACE INTO mini_contest_entries VALUES(?,?,?,?)",(contest[0],user_id,contest[1],int(time.time())))
            await db.commit()
        return {"ok":True,"message":"Участие подтверждено 🏆"}

    async def open_case(self, user_id, case_id):
        await self._user(user_id)
        cases={"free":{"price":0,"rewards":["Telegram Gift — Common","Rare Sticker","Premium Gift"]},"starter":{"price":10,"rewards":["GIFTSMMS Sticker Pack","Collector Card","Premium Gift"]},"legend":{"price":50,"rewards":["Legendary GIFTSMMS Card","Collector Gift","Premium Gift"]}}
        case=cases.get(case_id)
        if not case:return {"ok":False,"message":"Кейс не найден"}
        if case_id != "free":
            return {"ok":False,"message":"Покупка кейса за Stars выполняется через Telegram Stars invoice; случайные ставки на реальные Stars отключены."}
        reward=random.choice(case["rewards"])
        now=int(time.time())
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("INSERT INTO mini_case_opens(user_id,case_id,reward,created_at) VALUES(?,?,?,?)",(user_id,case_id,reward,now))
            await db.execute("INSERT INTO mini_history(user_id,kind,title,amount,created_at) VALUES(?,?,?,?,?)",(user_id,"case","Бесплатный кейс",reward,now))
            await db.commit()
        return {"ok":True,"reward":reward}

    async def routes(self, app, auth):
        async def state(request):
            uid,_=auth(request); return web.json_response(await self.snapshot(uid))
        async def task(request):
            uid,_=auth(request); body=await request.json(); return web.json_response(await self.claim_task(uid,int(body.get("task_id",0))))
        async def contest(request):
            uid,_=auth(request); return web.json_response(await self.enter_contest(uid))
        async def case(request):
            uid,_=auth(request); body=await request.json(); return web.json_response(await self.open_case(uid,str(body.get("case_id",""))))
        async def share(request):
            uid,_=auth(request); return web.json_response({"ok":True,"share_url":f"https://t.me/share/url?url={quote('https://t.me/GIFTSMMSBot')}&text={quote('Попробуй GIFTSMMS 🎁')}"})
        app.router.add_get("/api/mini/state",state)
        app.router.add_post("/api/mini/task/claim",task)
        app.router.add_post("/api/mini/contest/enter",contest)
        app.router.add_post("/api/mini/case/open",case)
        app.router.add_get("/api/mini/share",share)
