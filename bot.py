import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "8895635780:AAFFNShtEGgH3atRvI9nA6_sOB9MbmKyLSs")
MY_ID = int(os.environ.get("MY_ID", "8332707731"))
DATA_FILE = "plans.json"

def load_plans():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_plans(plans):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(plans, f, ensure_ascii=False, indent=2)

def today_key():
    return datetime.now().strftime("%Y-%m-%d")

def tomorrow_key():
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

def format_date_cz(date_str):
    y, m, d = date_str.split("-")
    days = ["pondělí","úterý","středa","čtvrtek","pátek","sobota","neděle"]
    months = ["ledna","února","března","dubna","května","června","července","srpna","září","října","listopadu","prosince"]
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{days[dt.weekday()]} {int(d)}. {months[int(m)-1]} {y}"

# /start
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    await update.message.reply_text(
        "👋 Ahoj! Jsem tvůj denní plánovač.\n\n"
        "📝 *Příkazy:*\n"
        "/plan – zapiš plán na zítřek\n"
        "/dnes – zobraz dnešní plán\n"
        "/hotovo 1 – označ úkol č.1 jako splněný\n"
        "/zitra – zobraz zítřejší plán\n"
        "/historie – posledních 7 dní\n"
        "/pomoc – zobraz nápovědu",
        parse_mode="Markdown"
    )

# /pomoc
async def pomoc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    await update.message.reply_text(
        "📖 *Nápověda*\n\n"
        "*/plan* – začni psát plán na zítřek\n"
        "Pak piš úkoly, každý na nový řádek.\n"
        "Nakonec napiš *hotovo* pro uložení.\n\n"
        "*/dnes* – zobraz dnešní úkoly\n"
        "*/hotovo 2* – splň úkol č.2\n"
        "*/zitra* – zobraz zítřejší plán\n"
        "*/historie* – přehled posledních dní",
        parse_mode="Markdown"
    )

# /plan – spustí zadávání
planning_mode = {}

async def plan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    planning_mode[MY_ID] = {"tasks": [], "note": "", "step": "tasks"}
    await update.message.reply_text(
        f"📝 Zapisuji plán na *{format_date_cz(tomorrow_key())}*\n\n"
        "Piš úkoly – každý úkol na samostatnou zprávu.\n"
        "Až budeš hotový, napiš *uložit*.",
        parse_mode="Markdown"
    )

# zpracování zpráv při plánování
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    text = update.message.text.strip()

    if MY_ID in planning_mode:
        if text.lower() in ["uložit", "ulozit", "hotovo", "done", "ok"]:
            tasks = planning_mode[MY_ID]["tasks"]
            if not tasks:
                await update.message.reply_text("⚠️ Žádné úkoly! Přidej aspoň jeden.")
                return
            plans = load_plans()
            plans[tomorrow_key()] = {
                "tasks": [{"text": t, "done": False} for t in tasks],
                "note": "",
                "saved_at": datetime.now().isoformat()
            }
            save_plans(plans)
            del planning_mode[MY_ID]
            task_list = "\n".join([f"  {i+1}. {t}" for i, t in enumerate(tasks)])
            await update.message.reply_text(
                f"✅ *Plán uložen!*\n\n"
                f"*{format_date_cz(tomorrow_key())}*\n{task_list}\n\n"
                f"Dobrou noc! 🌙",
                parse_mode="Markdown"
            )
        else:
            planning_mode[MY_ID]["tasks"].append(text)
            count = len(planning_mode[MY_ID]["tasks"])
            await update.message.reply_text(f"✓ Úkol {count} přidán. Piš dál nebo napiš *uložit*.", parse_mode="Markdown")
    else:
        await update.message.reply_text("Napiš /pomoc pro seznam příkazů.")

# /dnes
async def dnes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    plans = load_plans()
    plan_data = plans.get(today_key())
    if not plan_data or not plan_data["tasks"]:
        await update.message.reply_text("📭 Na dnešek nemáš žádný plán.")
        return
    await update.message.reply_text(format_plan(today_key(), plan_data), parse_mode="Markdown")

# /zitra
async def zitra(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    plans = load_plans()
    plan_data = plans.get(tomorrow_key())
    if not plan_data or not plan_data["tasks"]:
        await update.message.reply_text("📭 Na zítřek ještě nemáš plán. Napiš /plan")
        return
    await update.message.reply_text(format_plan(tomorrow_key(), plan_data), parse_mode="Markdown")

def format_plan(date_key, plan_data):
    tasks = plan_data["tasks"]
    done = sum(1 for t in tasks if t["done"])
    total = len(tasks)
    lines = [f"📋 *{format_date_cz(date_key)}*", f"Splněno: {done}/{total}\n"]
    for i, t in enumerate(tasks):
        check = "✅" if t["done"] else "⬜"
        lines.append(f"{check} {i+1}. {t['text']}")
    return "\n".join(lines)

# /hotovo 1
async def hotovo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    args = ctx.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Použití: /hotovo 1 (číslo úkolu)")
        return
    idx = int(args[0]) - 1
    plans = load_plans()
    plan_data = plans.get(today_key())
    if not plan_data or idx < 0 or idx >= len(plan_data["tasks"]):
        await update.message.reply_text("⚠️ Úkol nenalezen.")
        return
    plan_data["tasks"][idx]["done"] = True
    plans[today_key()] = plan_data
    save_plans(plans)
    task_name = plan_data["tasks"][idx]["text"]
    await update.message.reply_text(f"✅ Splněno: *{task_name}*", parse_mode="Markdown")

# /historie
async def historie(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    plans = load_plans()
    keys = sorted(plans.keys(), reverse=True)[:7]
    if not keys:
        await update.message.reply_text("📭 Zatím žádná historie.")
        return
    lines = ["📅 *Posledních 7 dní*\n"]
    for k in keys:
        p = plans[k]
        done = sum(1 for t in p["tasks"] if t["done"])
        total = len(p["tasks"])
        bar = "█" * done + "░" * (total - done)
        lines.append(f"*{format_date_cz(k)}*\n{bar} {done}/{total}\n")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ranní notifikace v 8:00
async def morning_notification(ctx: ContextTypes.DEFAULT_TYPE):
    plans = load_plans()
    plan_data = plans.get(today_key())
    if not plan_data or not plan_data["tasks"]:
        await ctx.bot.send_message(
            chat_id=MY_ID,
            text="☀️ Dobré ráno! Na dnešek nemáš žádný plán.\nNapiš /plan a naplánuj si den."
        )
        return
    msg = "☀️ *Dobré ráno!*\n\n" + format_plan(today_key(), plan_data)
    await ctx.bot.send_message(chat_id=MY_ID, text=msg, parse_mode="Markdown")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pomoc", pomoc))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CommandHandler("dnes", dnes))
    app.add_handler(CommandHandler("zitra", zitra))
    app.add_handler(CommandHandler("hotovo", hotovo))
    app.add_handler(CommandHandler("historie", historie))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ranní notifikace v 8:00
    app.job_queue.run_daily(
        morning_notification,
        time=datetime.strptime("08:00", "%H:%M").time().replace(tzinfo=__import__("pytz").timezone("Europe/Prague"))
    )

    print("Bot běží...")
    app.run_polling()

if __name__ == "__main__":
    main()
