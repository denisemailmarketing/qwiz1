# 🌍 Coğrafya Bilgi Yarışması Botu

Telegram-бот — географическая викторина на турецком языке. 50 стран, 4 варианта ответа, 3 подсказки на игру.

---

## 🚀 Деплой на Railway

### Шаг 1 — Создай бота в Telegram
1. Открой [@BotFather](https://t.me/BotFather)
2. Отправь `/newbot`, придумай имя и username
3. Скопируй **токен** (вида `123456789:AAF...`)

### Шаг 2 — Загрузи проект на GitHub
```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/ТВОЙюзернейм/geo-quiz-bot.git
git push -u origin main
```

### Шаг 3 — Деплой на Railway
1. Зайди на [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Выбери свой репозиторий
3. Перейди в **Variables** и добавь переменную:
   - Key: `BOT_TOKEN`
   - Value: твой токен от BotFather
4. Railway автоматически запустит бота через `Procfile`

> ⚠️ Railway определяет тип сервиса как **worker** (не web), потому что боту не нужен HTTP-порт. Это нормально.

---

## 💻 Локальный запуск

```bash
pip install -r requirements.txt
BOT_TOKEN="твой_токен" python bot.py
```

Или создай файл `.env` (не забудь добавить в `.gitignore`):
```
BOT_TOKEN=твой_токен
```
И запусти:
```bash
pip install python-dotenv
python bot.py
```

---

## 📁 Структура проекта

```
geo_quiz_bot/
├── bot.py              # Логика бота
├── countries_data.py   # 50 стран с подсказками (на турецком)
├── config.py           # Читает BOT_TOKEN из env
├── requirements.txt    # Зависимости
├── Procfile            # Команда запуска для Railway
├── runtime.txt         # Версия Python
└── .gitignore
```

---

## 🎮 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/stop` | Остановить игру |
