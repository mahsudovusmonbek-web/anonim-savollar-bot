import os
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")  # masalan: amonm_bot (@siz)

DB_PATH = "anon.db"

def get_con():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS links (
            token TEXT PRIMARY KEY,
            owner_id INTEGER NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            msg_id INTEGER PRIMARY KEY,
            sender_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL
        )
    """)
    con.commit()
    return con

def make_token(user_id: int) -> str:
    return f"u{user_id}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    con = get_con()

    # Agar start=token bilan kelsa
    if context.args:
        token = context.args[0]
        row = con.execute("SELECT owner_id FROM links WHERE token=?", (token,)).fetchone()
        if not row:
            await update.message.reply_text("Havola noto‘g‘ri yoki eskirgan.")
            return
        owner_id = int(row[0])

        if owner_id == user_id:
            await update.message.reply_text("Bu sizning havolangiz 🙂 Boshqalarga yuboring.")
            return

        context.user_data["target_owner_id"] = owner_id
        await update.message.reply_text("Anonim xabaringizni yozing. Men egasiga yuboraman ✅")
        return

    # Oddiy /start: shaxsiy havola beramiz
    token = make_token(user_id)
    con.execute("INSERT OR REPLACE INTO links(token, owner_id) VALUES (?,?)", (token, user_id))
    con.commit()

    link = f"https://t.me/{BOT_USERNAME}?start={token}"
    await update.message.reply_text(
        "Bu sizning shaxsiy havolangiz:\n"
        f"{link}\n\n"
        "Shuni do‘stlaringizga yuboring. Ular yozsa, sizga anonim keladi."
    )

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    owner_id = context.user_data.get("target_owner_id")

    if owner_id:
        sent = await context.bot.send_message(
            chat_id=owner_id,
            text=f"📩 Anonim xabar:\n\n{text}\n\n(Javob berish uchun shu xabarga Reply qiling)"
        )
        con = get_con()
        con.execute(
            "INSERT OR REPLACE INTO threads(msg_id, sender_id, owner_id) VALUES (?,?,?)",
            (sent.message_id, update.effective_user.id, owner_id)
        )
        con.commit()
        await update.message.reply_text("✅ Yuborildi.")
        return

    await update.message.reply_text("Boshlash uchun /start bosing.")

async def on_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    replied_id = update.message.reply_to_message.message_id
    con = get_con()
    row = con.execute("SELECT sender_id, owner_id FROM threads WHERE msg_id=?", (replied_id,)).fetchone()
    if not row:
        return

    sender_id, owner_id = int(row[0]), int(row[1])
    if update.effective_user.id != owner_id:
        return

    answer = update.message.text or ""
    await context.bot.send_message(chat_id=sender_id, text=f"💬 Javob:\n\n{answer}")

def main():
    if not BOT_TOKEN or not BOT_USERNAME:
        raise RuntimeError("BOT_TOKEN va BOT_USERNAME env kerak")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, on_reply))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
