import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from countries_data import COUNTRIES
from config import BOT_TOKEN

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_wrong_options(correct_country: dict, all_countries: list, count: int = 3) -> list:
    """Get random wrong answer options."""
    wrong = [c for c in all_countries if c["name"] != correct_country["name"]]
    return random.sample(wrong, count)


def build_options_keyboard(correct: dict, options: list, hint_50_50: bool = False) -> InlineKeyboardMarkup:
    """Build answer options keyboard."""
    buttons = []
    for opt in options:
        buttons.append(InlineKeyboardButton(
            text=opt["name_tr"],
            callback_data=f"answer_{opt['name']}"
        ))
    
    rows = [[b] for b in buttons]
    return InlineKeyboardMarkup(rows)


def build_hints_keyboard(session: dict) -> InlineKeyboardMarkup:
    """Build hints keyboard."""
    hints_used = session.get("hints_used", set())
    hints_total = session.get("hints_total", 0)
    
    buttons = []
    
    if "50_50" not in hints_used:
        buttons.append(InlineKeyboardButton("🎯 50/50", callback_data="hint_5050"))
    else:
        buttons.append(InlineKeyboardButton("🎯 50/50 ✓", callback_data="hint_used"))
    
    if "flag" not in hints_used:
        buttons.append(InlineKeyboardButton("🏳️ Bayrak", callback_data="hint_flag"))
    else:
        buttons.append(InlineKeyboardButton("🏳️ Bayrak ✓", callback_data="hint_used"))
    
    if "currency" not in hints_used:
        buttons.append(InlineKeyboardButton("💰 Para Birimi", callback_data="hint_currency"))
    else:
        buttons.append(InlineKeyboardButton("💰 Para Birimi ✓", callback_data="hint_used"))
    
    remaining = 3 - hints_total
    rows = [buttons]
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Oyunu Başlat!", callback_data="start_game")]
    ])
    
    await update.message.reply_text(
        "🌍 *Coğrafya Bilgi Yarışması'na Hoş Geldiniz!*\n\n"
        "📋 *Nasıl Oynanır:*\n"
        "• 50 farklı ülke hakkında ipuçları verilecek\n"
        "• Her soruda 4 seçenek arasından doğru ülkeyi seçmelisiniz\n"
        "• Tüm 50 ülkeyi doğru tahmin ederek oyunu tamamlayın!\n\n"
        "💡 *İpuçları (Oyun başına 3 hak):*\n"
        "🎯 *50/50* — 4 seçenekten 2'si elenir\n"
        "🏳️ *Bayrak* — Ülkenin bayrağı gösterilir\n"
        "💰 *Para Birimi* — Ülkenin para birimi söylenir\n\n"
        "Hazır mısınız? Hadi başlayalım! 🚀",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def start_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initialize a new game session."""
    query = update.callback_query
    await query.answer()
    
    shuffled = COUNTRIES.copy()
    random.shuffle(shuffled)
    
    context.user_data["session"] = {
        "questions": shuffled,
        "current_index": 0,
        "score": 0,
        "hints_used": set(),
        "hints_total": 0,
        "active": True,
        "current_options": None,
    }
    
    await query.edit_message_text(
        "🎮 *Oyun başlıyor!*\n\n"
        "50 soru sizi bekliyor. Başarılar! 🌟",
        parse_mode="Markdown"
    )
    
    await send_question(update, context)


async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the current question."""
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
    session["hints_used"] = set()
    
    hints_total = session["hints_total"]
    remaining_hints = 3 - hints_total
    
    # Build clues text
    clues = "\n".join([f"• {clue}" for clue in correct["clues"]])
    
    text = (
        f"🌍 *Soru {idx + 1}/50*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔍 *Bu ülke hangisi?*\n\n"
        f"{clues}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Doğru: {session['score']} | ❓ Kalan: {50 - idx} | 💡 İpucu hakkı: {remaining_hints}"
    )
    
    # Build keyboard with options + hints
    option_buttons = []
    for opt in options:
        option_buttons.append([InlineKeyboardButton(
            text=opt["name_tr"],
            callback_data=f"answer_{opt['name']}"
        )])
    
    hint_buttons = []
    if "50_50" not in session["hints_used"] and remaining_hints > 0:
        hint_buttons.append(InlineKeyboardButton("🎯 50/50", callback_data="hint_5050"))
    if "flag" not in session["hints_used"] and remaining_hints > 0:
        hint_buttons.append(InlineKeyboardButton("🏳️ Bayrak", callback_data="hint_flag"))
    if "currency" not in session["hints_used"] and remaining_hints > 0:
        hint_buttons.append(InlineKeyboardButton("💰 Para Birimi", callback_data="hint_currency"))
    
    keyboard = option_buttons
    if hint_buttons:
        keyboard.append(hint_buttons)
    
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle answer selection."""
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
            f"🏳️ {correct['flag']} *{correct['name_tr']}*\n"
            f"_{correct['fun_fact']}_"
        )
    else:
        # Find what user chose
        chosen = next((c for c in COUNTRIES if c["name"] == chosen_name), None)
        chosen_tr = chosen["name_tr"] if chosen else chosen_name
        result_text = (
            f"❌ *Yanlış!*\n\n"
            f"Seçtiğiniz: {chosen_tr}\n"
            f"Doğru cevap: 🏳️ {correct['flag']} *{correct['name_tr']}*\n\n"
            f"_{correct['fun_fact']}_"
        )
    
    session["current_index"] += 1
    
    # Edit message to show result
    await query.edit_message_text(
        text=result_text,
        parse_mode="Markdown"
    )
    
    # Check if game is over
    if session["current_index"] >= 50:
        await end_game(update, context)
    else:
        # Send next question
        await send_question(update, context)


async def hint_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle hint usage."""
    query = update.callback_query
    
    session = context.user_data.get("session")
    if not session or not session["active"]:
        await query.answer("Aktif oyun bulunamadı!", show_alert=True)
        return
    
    hint_type = query.data.replace("hint_", "")
    hints_used = session.get("hints_used", set())
    hints_total = session.get("hints_total", 0)
    
    if hint_type == "used":
        await query.answer("Bu ipucu zaten kullanıldı!", show_alert=True)
        return
    
    if hints_total >= 3:
        await query.answer("⚠️ Oyun başına 3 ipucu hakkınız bitti!", show_alert=True)
        return
    
    if hint_type in hints_used:
        await query.answer("Bu ipucunu zaten kullandınız!", show_alert=True)
        return
    
    idx = session["current_index"]
    correct = session["questions"][idx]
    options = session["current_options"]
    
    session["hints_used"].add(hint_type)
    session["hints_total"] = hints_total + 1
    remaining_hints = 3 - session["hints_total"]
    
    await query.answer()
    
    if hint_type == "5050":
        # Remove 2 wrong answers, keep correct + 1 wrong
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
        hint_msg = f"💰 *Para birimi ipucu:* Bu ülkenin para birimi **{correct['currency']}**"
    
    # Send hint as separate message
    await query.message.reply_text(hint_msg, parse_mode="Markdown")
    
    # Rebuild current question with updated options/hints
    clues = "\n".join([f"• {clue}" for clue in correct["clues"]])
    
    text = (
        f"🌍 *Soru {idx + 1}/50*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔍 *Bu ülke hangisi?*\n\n"
        f"{clues}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Doğru: {session['score']} | ❓ Kalan: {50 - idx} | 💡 İpucu hakkı: {remaining_hints}"
    )
    
    option_buttons = []
    for opt in options:
        option_buttons.append([InlineKeyboardButton(
            text=opt["name_tr"],
            callback_data=f"answer_{opt['name']}"
        )])
    
    hint_buttons = []
    if "50_50" not in session["hints_used"] and remaining_hints > 0:
        hint_buttons.append(InlineKeyboardButton("🎯 50/50", callback_data="hint_5050"))
    if "flag" not in session["hints_used"] and remaining_hints > 0:
        hint_buttons.append(InlineKeyboardButton("🏳️ Bayrak", callback_data="hint_flag"))
    if "currency" not in session["hints_used"] and remaining_hints > 0:
        hint_buttons.append(InlineKeyboardButton("💰 Para Birimi", callback_data="hint_currency"))
    
    keyboard = option_buttons
    if hint_buttons:
        keyboard.append(hint_buttons)
    
    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show final results."""
    session = context.user_data.get("session")
    score = session["score"]
    session["active"] = False
    
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
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Tekrar Oyna", callback_data="start_game")]
    ])
    
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"{emoji} *Oyun Bitti!*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Sonuçlarınız:*\n\n"
            f"✅ Doğru cevap: *{score}/50*\n"
            f"❌ Yanlış cevap: *{50 - score}/50*\n"
            f"📈 Başarı oranı: *%{score * 2}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💬 {comment}"
        ),
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop current game."""
    if "session" in context.user_data:
        context.user_data["session"]["active"] = False
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Yeni Oyun Başlat", callback_data="start_game")]
    ])
    
    await update.message.reply_text(
        "⏹️ Oyun durduruldu. Yeni bir oyun başlatmak ister misiniz?",
        reply_markup=keyboard
    )


def main():
    """Run the bot."""
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop_game))
    app.add_handler(CallbackQueryHandler(start_game_callback, pattern="^start_game$"))
    app.add_handler(CallbackQueryHandler(answer_callback, pattern="^answer_"))
    app.add_handler(CallbackQueryHandler(hint_callback, pattern="^hint_"))
    
    logger.info("Bot başlatılıyor...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
