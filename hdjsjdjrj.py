import os
import sqlite3
import telebot
from telebot import types
from dotenv import load_dotenv
from datetime import datetime, date

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- ССЫЛКИ ----------
LINKS = [
    "https://t.me/+Uzd2O-2AR_M4ZWYx",
    "https://t.me/+Uzd2O-2AR_M4ZWYx",
    "https://t.me/+Uzd2O-2AR_M4ZWYx"
]

# ---------- БАЗА ДАННЫХ ----------
DB_NAME = "users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            first_seen TEXT,
            last_seen TEXT,
            messages_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def register_user(message):
    user = message.from_user
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user.id,))
    row = cur.fetchone()

    if row is None:
        cur.execute("""
            INSERT INTO users (user_id, username, first_name, first_seen, last_seen, messages_count)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (user.id, user.username or "", user.first_name or "", now, now))
    else:
        cur.execute("""
            UPDATE users SET last_seen = ?, messages_count = messages_count + 1,
            username = ?, first_name = ?
            WHERE user_id = ?
        """, (now, user.username or "", user.first_name or "", user.id))

    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]

    today = date.today().strftime("%Y-%m-%d")

    cur.execute("SELECT COUNT(*) FROM users WHERE first_seen LIKE ?", (today + "%",))
    new_today = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE last_seen LIKE ?", (today + "%",))
    active_today = cur.fetchone()[0]

    cur.execute("""
        SELECT user_id, username, first_name, last_seen, messages_count
        FROM users ORDER BY last_seen DESC LIMIT 10
    """)
    last_users = cur.fetchall()

    conn.close()
    return total, new_today, active_today, last_users

# ---------- КЛАВИАТУРЫ ----------
def main_keyboard(is_admin=False):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("🎲 Бросить кубик"))
    if is_admin:
        keyboard.add(types.KeyboardButton("⚙️ Админ-панель"))
    return keyboard

def admin_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("📊 Статистика"))
    keyboard.add(types.KeyboardButton("👥 Последние пользователи"))
    keyboard.add(types.KeyboardButton("⬅️ Назад"))
    return keyboard

# ---------- ХЕНДЛЕРЫ ----------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    register_user(message)
    text = "sливы ниже👇\n\n" + "\n".join(LINKS)
    is_admin = message.from_user.id == ADMIN_ID
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(is_admin))

@bot.message_handler(func=lambda m: m.text == "🎲 Бросить кубик")
def send_dice(message):
    register_user(message)
    is_admin = message.from_user.id == ADMIN_ID
    bot.send_dice(message.chat.id, reply_markup=main_keyboard(is_admin))

# ---------- АДМИН-ПАНЕЛЬ ----------
@bot.message_handler(func=lambda m: m.text == "⚙️ Админ-панель" and m.from_user.id == ADMIN_ID)
def open_admin(message):
    bot.send_message(message.chat.id, "Админ-панель:", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "📊 Статистика" and m.from_user.id == ADMIN_ID)
def show_stats(message):
    total, new_today, active_today, _ = get_stats()
    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{total}</b>\n"
        f"🆕 Зашло сегодня (впервые): <b>{new_today}</b>\n"
        f"🔥 Активных сегодня: <b>{active_today}</b>\n"
        f"📅 Дата: {date.today().strftime('%d.%m.%Y')}"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "👥 Последние пользователи" and m.from_user.id == ADMIN_ID)
def last_users(message):
    _, _, _, users = get_stats()
    if not users:
        bot.send_message(message.chat.id, "Пользователей пока нет.", reply_markup=admin_keyboard())
        return

    text = "👥 <b>Последние 10 пользователей:</b>\n\n"
    for uid, username, first_name, last_seen, msgs in users:
        uname = f"@{username}" if username else "—"
        text += (
            f"👤 {first_name or '—'} ({uname})\n"
            f"🆔 <code>{uid}</code>\n"
            f"🕒 Последняя активность: {last_seen}\n"
            f"💬 Сообщений: {msgs}\n\n"
        )
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "⬅️ Назад" and m.from_user.id == ADMIN_ID)
def back_to_main(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_keyboard(True))

# ---------- FALLBACK: считаем активность ----------
@bot.message_handler(func=lambda m: True)
def track_activity(message):
    register_user(message)

# ---------- ЗАПУСК ----------
if __name__ == '__main__':
    init_db()
    print("Бот запущен...")
    bot.polling(none_stop=True)