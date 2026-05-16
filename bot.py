import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import pytz

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
MY_ID = int(os.environ.get("MY_ID"))
DATA_FILE = "plans.json"
TZ = pytz.timezone("Europe/Prague")

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
    return datetime.now(TZ).strftime("%Y-%m-%d")

def tomorrow_key():
    return (datetime.now(TZ) + timedelta(days=1)).strftime("%Y-%m-%d")

def format_date_cz(date_str):
    y, m, d = date_str.split("-")
    days = ["pondělí","úterý","středa","čtvrtek","pátek","sobota","neděle"]
    months = ["ledna","února","března","dubna","května","června","července","srpna","září","října","listopadu","prosince"]
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{days[dt.weekday()]} {int(d)}. {months[int(m)-1]} {y}"

def format_plan(date_key, plan_data):
    tasks = plan_data["tasks"]
    done = sum(1 for t in tasks if t["done"])
    total = len(tasks)
    lines = [f"📋 {format_date_cz(date_key)}", f"Splněno: {done}/{total}\n"]
    for i, t in enumerate(tasks):
        check = "✅" if t["done"] else "⬜"
        lines.append(f"{check} {i+1}. {t['text']}")
    return "\n".join(lines)

planning_mode = {}

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    await update.message.reply_text(
        "👋 Ahoj! Jsem tvůj denní plánovač.\n\n"
        "📝 Příkazy:\n"
        "/plan – zapiš plán na zítřek\n"
        "/dnes – zobraz dnešní plán\n"
        "/hotovo 1 – splň úkol č.1\n"
        "/zitra – zobraz zítřejší plán\n"
        "/historie – posledních 7 dní"
    )

async def plan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    planning_mode[MY_ID] = {"tasks": []}
    await update.message.reply_text(
        f"📝 Plán na {format_date_cz(tomorrow_key())}\n\n"
        "Piš úkoly – každý jako samostatnou zprávu.\n"
        "Až budeš hotový, napiš: ulozit"
    )

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    text = update.message.text.strip()
    if MY_ID in planning_mode:
        if text.lower() in ["uložit", "ulozit", "hotovo", "ok"]:
            tasks = planning_mode[MY_ID]["tasks"]
            if not tasks:
                await update.message.reply_text("Přidej aspoň jeden úkol!")
                return
            plans = load_plans()
            plans[tomorrow_key()] = {
                "tasks": [{"text": t, "done": False} for t in tasks],
                "saved_at": datetime.now().isoformat()
            }
            save_plans(plans)
            del planning_mode[MY_ID]
            task_list = "\n".join([f"{i+1}. {t}" for i, t in enumerate(tasks)])
            await update.message.reply_text(f"✅ Uloženo!\n\n{task_list}\n\nDobrou noc! 🌙")
        else:
            planning_mode[MY_ID]["tasks"].append(text)
            count = len(planning_mode[MY_ID]["tasks"])
            await update.message.reply_text(f"✓ Úkol {count} přidán. Piš dál nebo napiš: ulozit")
    else:
        await update.message.reply_text("Napiš /start pro nápovědu.")

async def dnes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    plans = load_plans()
    plan_data = plans.get(today_key())
    if not plan_data or not plan_data["tasks"]:
        await update.message.reply_text("Na dnešek nemáš žádný plán.")
        return
    await update.message.reply_text(format_plan(today_key(), plan_data))

async def zitra(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    plans = load_plans()
    plan_data = plans.get(tomorrow_key())
    if not plan_data or not plan_data["tasks"]:
        await update.message.reply_text("Na zítřek ještě nemáš plán. Napiš /plan")
        return
    await update.message.reply_text(format_plan(tomorrow_key(), plan_data))

async def hotovo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    args = ctx.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Použití: /hotovo 1")
        return
    idx = int(args[0]) - 1
    plans = load_plans()
    plan_data = plans.get(today_key())
    if not plan_data or idx < 0 or idx >= len(plan_data["tasks"]):
        await update.message.reply_text("Úkol nenalezen.")
        return
    plan_data["tasks"][idx]["done"] = True
    plans[today_key()] = plan_data
    save_plans(plans)
    await update.message.reply_text(f"✅ Splněno: {plan_data['tasks'][idx]['text']}")

async def historie(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_ID:
        return
    plans = load_plans()
    keys = sorted(plans.keys(), reverse=True)[:7]
    if not keys:
        await update.message.reply_text("Zatím žádná historie.")
        return
    lines = ["📅 Posledních 7 dní\n"]
    for k in keys:
        p = plans[k]
        done = sum(1 for t in p["tasks"] if t["done"])
        total = len(p["tasks"])
        lines.append(f"{format_date_cz(k)}: {done}/{total} splněno")
    await update.message.reply_text("\n".join(lines))

async def morning_job(ctx: ContextTypes.DEFAULT_TYPE):
    plans = load_plans()
    plan_data = plans.get(today_key())
    if not plan_data or not plan_data["tasks"]:
        msg = "☀️ Dobré ráno! Na dnešek nemáš žádný plán.\nNapiš /plan"
    else:
        msg = "☀️ Dobré ráno!\n\n" + format_plan(today_key(), plan_data)
    await ctx.bot.send_message(chat_id=MY_ID, text=msg)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CommandHandler("dnes", dnes))
    app.add_handler(CommandHandler("zitra", zitra))
    app.add_handler(CommandHandler("hotovo", hotovo))
    app.add_handler(CommandHandler("historie", historie))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.job_queue.run_daily(
        morning_job,
        time=datetime.now(TZ).replace(hour=8, minute=0, second=0, microsecond=0).timetz()
    )

    print("Bot běží...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
