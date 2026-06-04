import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from countries_data import COUNTRIES
from config import BOT_TOKEN

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_wrong_options(correct_country: dict, all_countries: list, count: int = 3) -> list:
    wrong = [c for c in all_countries if c["name"] != correct_country["name"]]
    return random.sample(wrong, count)


def build_question_keyboard(session: dict, options: list) -> InlineKeyboardMarkup:
    """Build keyboard: answer options + available hints + quit button."""
    hints_used = session.get("hints_used", set())
    hints_total = session.get("hints_total", 0)
    remaining_hints = 3 - hints_total

    # Answer options
    keyboard = []
    for opt in options:
        keyboard.append([InlineKeyboardButton(
            text=opt["name_tr"],
            callback_data=f"answer_{opt['name']}"
        )])

    # Hint buttons — each hint can only be used once per game
    hint_row = []
    if remaining_hints > 0:
        if "5050" not in hints_used:
            hint_row.append(InlineKeyboardButton("🎯 50/50", callback_data="hint_5050"))
        if "flag" not in hints_used:
            hint_row.append(InlineKeyboardButton("🏳️ Bayrak", callback_data="hint_flag"))
        if "currency" not in hints_used:
            hint_row.append(InlineKeyboardButton("💰 Para", callback_data="hint_currency"))

    if hint_row:
        keyboard.append(hint_row)

    # Quit button always visible
    keyboard.append([InlineKeyboardButton("🚪 Oyundan Çık", callback_data="quit_game")])

    return InlineKeyboardMarkup(keyboard)


def get_stats(user_data: dict) -> tuple[int, int]:
    """Return (total_games, total_correct)."""
    return (
        user_data.get("total_games", 0),
        user_data.get("total_correct", 0),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_games, total_correct = get_stats(context.user_data)

    stats_text = ""
    if total_games > 0:
        stats_text = (
            f"\n\n📊 *İstatistikleriniz:*\n"
            f"🎮 Oynanan oyun: *{total_games}*\n"
            f"✅ Toplam doğru cevap: *{total_correct}*\n"
            f"📈 Ortalama: *{total_correct}/{total_games * 50}* "
            f"(%{round(total_correct / (total_games * 50) * 100)})"
        )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Oyunu Başlat!", callback_data="start_game")]
    ])

    text = (
        "🌍 *Coğrafya Bilgi Yarışması'na Hoş Geldiniz!*\n\n"
        "📋 *Nasıl Oynanır:*\n"
        "• 50 farklı ülke hakkında ipuçları verilecek\n"
        "• Her soruda 4 seçenek arasından doğru ülkeyi seçmelisiniz\n"
        "• Tüm 50 ülkeyi doğru tahmin ederek oyunu tamamlayın!\n\n"
        "💡 *İpuçları (Oyun başına 3 hak, her biri 1 kez):*\n"
        "🎯 *50/50* — 4 seçenekten 2'si elenir\n"
        "🏳️ *Bayrak* — Ülkenin bayrağı gösterilir\n"
        "💰 *Para Birimi* — Ülkenin para birimi söylenir\n\n"
        "Hazır mısınız? Hadi başlayalım! 🚀"
        f"{stats_text}"
    )

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def start_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    shuffled = COUNTRIES.copy()
    random.shuffle(shuffled)

    context.user_data["session"] = {
        "questions": shuffled,
        "current_index": 0,
        "score": 0,
        "hints_used": set(),   # tracks which hint TYPES used this game: "5050", "flag", "currency"
        "hints_total": 0,      # total hints used this game (max 3)
        "active": True,
        "current_options": None,
    }

    await query.edit_message_text(
        "🎮 *Oyun başlıyor!*\n\n50 soru sizi bekliyor. Başarılar! 🌟",
        parse_mode="Markdown"
    )

    await send_question(update, context)


async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = context.user_data.get("session")
    if not session or not session["active"]:
        return

    idx = session["current_index"]
    if idx >= len(session["questions"]):
        await end_game(update, context)
        return

    correct = session["questions"][idx]
    wrong_options = get_wrong_options(correct, COUNTRIES, 3)
    options = wrong_options + [correct]
    random.shuffle(options)

    session["current_options"] = options

    hints_total = session["hints_total"]
    remaining_hints = 3 - hints_total

    clues = "\n".join([f"• {clue}" for clue in correct["clues"]])

    text = (
        f"🌍 *Soru {idx + 1}/50*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔍 *Bu ülke hangisi?*\n\n"
        f"{clues}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Doğru: {session['score']} | ❓ Kalan: {50 - idx} | 💡 İpucu: {remaining_hints}"
    )

    keyboard = build_question_keyboard(session, options)
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    session = context.user_data.get("session")
    if not session or not session["active"]:
        return

    chosen_name = query.data.replace("answer_", "")
    idx = session["current_index"]
    correct = session["questions"][idx]

    is_correct = chosen_name == correct["name"]

    if is_correct:
        session["score"] += 1
        result_text = (
            f"✅ *Doğru!* Harika!\n\n"
            f"{correct['flag']} *{correct['name_tr']}*\n"
            f"_{correct['fun_fact']}_"
        )
    else:
        chosen = next((c for c in COUNTRIES if c["name"] == chosen_name), None)
        chosen_tr = chosen["name_tr"] if chosen else chosen_name
        result_text = (
            f"❌ *Yanlış!*\n\n"
            f"Seçtiğiniz: {chosen_tr}\n"
            f"Doğru cevap: {correct['flag']} *{correct['name_tr']}*\n\n"
            f"_{correct['fun_fact']}_"
        )

    session["current_index"] += 1

    await query.edit_message_text(text=result_text, parse_mode="Markdown")

    if session["current_index"] >= 50:
        await end_game(update, context)
    else:
        await send_question(update, context)


async def hint_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    session = context.user_data.get("session")
    if not session or not session["active"]:
        await query.answer("Aktif oyun bulunamadı!", show_alert=True)
        return

    hint_type = query.data.replace("hint_", "")
    hints_used: set = session.get("hints_used", set())
    hints_total: int = session.get("hints_total", 0)

    # Guard: each hint type only once per game
    if hint_type in hints_used:
        await query.answer("Bu ipucunu zaten kullandınız!", show_alert=True)
        return

    # Guard: max 3 hints per game
    if hints_total >= 3:
        await query.answer("⚠️ Oyun başına 3 ipucu hakkınız bitti!", show_alert=True)
        return

    idx = session["current_index"]
    correct = session["questions"][idx]
    options = session["current_options"]

    hints_used.add(hint_type)
    session["hints_used"] = hints_used
    session["hints_total"] = hints_total + 1
    remaining_hints = 3 - session["hints_total"]

    await query.answer()

    if hint_type == "5050":
        wrong_opts = [o for o in options if o["name"] != correct["name"]]
        keep_wrong = random.sample(wrong_opts, 1)
        new_options = keep_wrong + [correct]
        random.shuffle(new_options)
        session["current_options"] = new_options
        options = new_options
        hint_msg = "🎯 *50/50 ipucu kullanıldı!* 2 yanlış cevap elendi."

    elif hint_type == "flag":
        hint_msg = f"🏳️ *Bayrak ipucu:* {correct['flag']}"

    elif hint_type == "currency":
        hint_msg = f"💰 *Para birimi ipucu:* Bu ülkenin para birimi *{correct['currency']}*"

    else:
        return

    await query.message.reply_text(hint_msg, parse_mode="Markdown")

    # Rebuild question with updated options/keyboard
    clues = "\n".join([f"• {clue}" for clue in correct["clues"]])
    text = (
        f"🌍 *Soru {idx + 1}/50*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔍 *Bu ülke hangisi?*\n\n"
        f"{clues}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Doğru: {session['score']} | ❓ Kalan: {50 - idx} | 💡 İpucu: {remaining_hints}"
    )

    keyboard = build_question_keyboard(session, options)
    await query.edit_message_text(text=text, parse_mode="Markdown", reply_markup=keyboard)


async def quit_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle in-game quit button."""
    query = update.callback_query
    await query.answer()

    session = context.user_data.get("session")
    if not session or not session["active"]:
        return

    score = session["score"]
    answered = session["current_index"]
    session["active"] = False

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Yeni Oyun", callback_data="start_game")]
    ])

    await query.edit_message_text(
        f"🚪 *Oyundan çıkıldı.*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Yarım kalan sonuçlar:*\n\n"
        f"✅ Doğru cevap: *{score}/{answered}*\n"
        f"📋 Cevaplanan soru: *{answered}/50*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Tekrar oynamak ister misiniz?",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = context.user_data.get("session")
    score = session["score"]
    session["active"] = False

    # Update lifetime stats
    context.user_data["total_games"] = context.user_data.get("total_games", 0) + 1
    context.user_data["total_correct"] = context.user_data.get("total_correct", 0) + score

    if score == 50:
        emoji = "🏆"
        comment = "Mükemmel! Tüm ülkeleri doğru tahmin ettiniz! Coğrafya ustasısınız!"
    elif score >= 40:
        emoji = "🥇"
        comment = "Harika bir performans! Coğrafya bilginiz çok güçlü!"
    elif score >= 30:
        emoji = "🥈"
        comment = "İyi iş! Biraz daha çalışarak mükemmele ulaşabilirsiniz!"
    elif score >= 20:
        emoji = "🥉"
        comment = "Fena değil! Daha fazla pratik yaparak gelişebilirsiniz!"
    else:
        emoji = "📚"
        comment = "Endişelenmeyin! Tekrar oynayarak coğrafya bilginizi geliştirebilirsiniz!"

    total_games = context.user_data["total_games"]
    total_correct = context.user_data["total_correct"]

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Tekrar Oyna", callback_data="start_game")]
    ])

    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"{emoji} *Oyun Bitti!*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Bu oyunun sonuçları:*\n\n"
            f"✅ Doğru cevap: *{score}/50*\n"
            f"❌ Yanlış cevap: *{50 - score}/50*\n"
            f"📈 Başarı oranı: *%{score * 2}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🗂 *Genel istatistikler:*\n\n"
            f"🎮 Toplam oyun: *{total_games}*\n"
            f"✅ Toplam doğru: *{total_correct}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💬 {comment}"
        ),
        parse_mode="Markdown",
        reply_markup=keyboard
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start_game_callback, pattern="^start_game$"))
    app.add_handler(CallbackQueryHandler(answer_callback, pattern="^answer_"))
    app.add_handler(CallbackQueryHandler(hint_callback, pattern="^hint_"))
    app.add_handler(CallbackQueryHandler(quit_game_callback, pattern="^quit_game$"))

    logger.info("Bot başlatılıyor...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
