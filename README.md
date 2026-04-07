# NutriBot — Telegram-бот и Mini App для учёта калорий

Полнофункциональное приложение для отслеживания питания и физической активности.
LLM (GPT-4o) извлекает **структуру еды** (продукты + граммы), а Python **детерминированно** рассчитывает калории и БЖУ из локальной базы из 120+ продуктов.
Перед сохранением — подтверждение и редактирование. Вечером — умные уведомления по прогрессу.

---

## Что умеет

- 📸 **Фото еды** — GPT-4o находит продукты и граммы → Python считает калории/БЖУ
- ✏️ **Текст** — «борщ со сметаной» → GPT-4o извлекает структуру → Python считает
- 🎤 **Голосовое** — Whisper-1 транскрибирует → GPT-4o структура → Python расчёт
- ✋ **Подтверждение** — перед сохранением: карточка еды + кнопки ✅ Сохранить / ✏️ Изменить / ❌ Отмена
- ✏️ **Редактирование** — «борщ=300», «-хлеб», «+яблоко=120» → пересчёт на лету
- ⭐ **Шаблоны** — сохранить приём как шаблон → добавить в один тап через /templates
- 🏃 **Активности** — бег, ходьба, зал → оценка расхода калорий
- ⚡ **Быстрый ввод** — 7 продуктов + 5 активностей в один тап
- 📊 **Статистика** — графики съедено/сожжено за 7/30 дней (Recharts)
- 🎯 **Цель калорий** — похудеть / поддержать / набрать массу
- 🌙 **Умные уведомления** — вечерний пуш в 20:00 (нет записей / недобор / перебор)
- 🔐 **Авторизация** — проверка подписи Telegram WebApp initData

---

## Архитектура

Три компонента работают на одной базе данных (SQLite):

| Компонент | Стек | Порт | Режим |
|---|---|---|---|
| **Telegram Bot** | aiogram 3.x | — (polling) | asyncio + polling |
| **FastAPI** | FastAPI + uvicorn | 8001 | REST API |
| **Mini App** | React + Vite | 5173 (dev) / статика (prod) | SPA |

### Пайплайн анализа еды

```
Пользователь → текст / фото / голос
       ↓
GPT-4o / Whisper → {items: [{name, grams, confidence}]}
       ↓
Python (nutrition_db.py) → calculate_meal() → {calories, protein, fat, carbs}
       ↓
Показ карточки → ✅ / ✏️ / ❌
       ↓ (✅ Сохранить)
SQLite (meals)
```

### Схема БД

```
users            — telegram_id, username, weight, height, goal_calories
meals            — user_id, description, calories, protein, fat, carbs
activities       — user_id, description, calories_burned, duration_minutes
meal_templates   — telegram_user_id, title, structure_json
notification_log — telegram_user_id, notif_type, sent_date
```

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Telegram Bot   │      │     FastAPI     │      │    Mini App     │
│   aiogram 3     │      │   uvicorn :8001 │◄─────│  React + Vite   │
│   polling       │      │   REST API      │      │  :5173 / static │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                        │
         └──────────┬─────────────┴────────────────────────┘
                    │
          ┌─────────▼─────────┐
          │   SQLite (shared) │
          │   nutrition.db    │
          │  users / meals /  │
          │  activities /     │
          │  meal_templates / │
          │  notification_log │
          └───────────────────┘
```

---

## Быстрый старт (локально)

### 1. Клонировать

```bash
cd /Users/artem/Desktop/nutrobot
```

### 2. Создать .env

```bash
cd nutrition_bot
cp .env.example .env
nano .env  # заполнить токены
```

### 3. Установить зависимости (бэкенд)

```bash
cd nutrition_bot
pip3 install -r requirements.txt
```

### 4. Запустить бота

```bash
cd nutrition_bot
python3 bot.py
```

### 5. Запустить API

```bash
cd nutrition_bot
python3 -m uvicorn api:app --port 8001 --host 0.0.0.0
```

Документация API: http://localhost:8001/docs

### 6. Запустить фронт

```bash
cd miniapp
npm install
npm run dev    # http://localhost:5173
```

---

## Деплой на VPS (Ubuntu 22.04)

### 1. Подготовка сервера

```bash
sudo apt update && sudo apt install -y python3.11 python3-pip nodejs npm nginx certbot python3-certbot-nginx
```

### 2. Копируем проект

```bash
# С локальной машины:
scp -r /Users/artem/Desktop/nutrobot/ user@YOUR_VPS_IP:/opt/nutribot/
```

### 3. Настройка окружения

```bash
cd /opt/nutribot/nutrition_bot
cp .env.example .env
nano .env  # заполни токены: TELEGRAM_TOKEN, OPENAI_API_KEY, BOT_TOKEN

pip3 install -r requirements.txt
```

### 4. Билд фронтенда

```bash
cd /opt/nutribot/miniapp
npm install

# Замени BASE URL в miniapp/src/api.js с localhost:8001 на продакшен-домен:
# const BASE = 'https://yourdomain.com/api'

npm run build
# Статика появится в miniapp/dist/
```

### 5. Nginx конфиг

```bash
sudo nano /etc/nginx/sites-available/nutribot
```

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Mini App — статика
    location / {
        root /opt/nutribot/miniapp/dist;
        try_files $uri $uri/ /index.html;
    }

    # API — проксируем на uvicorn
    location /api/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируем и ставим SSL:

```bash
sudo ln -s /etc/nginx/sites-available/nutribot /etc/nginx/sites-enabled/
sudo certbot --nginx -d yourdomain.com
sudo nginx -t && sudo systemctl reload nginx
```

### 6. Systemd сервисы

**API** — `/etc/systemd/system/nutribot-api.service`:

```ini
[Unit]
Description=NutriBot FastAPI
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/nutribot/nutrition_bot
ExecStart=/usr/bin/python3 -m uvicorn api:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Bot** — `/etc/systemd/system/nutribot-bot.service`:

```ini
[Unit]
Description=NutriBot Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/nutribot/nutrition_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Активируем:

```bash
sudo systemctl daemon-reload
sudo systemctl enable nutribot-api nutribot-bot
sudo systemctl start nutribot-api nutribot-bot

# Проверка:
sudo systemctl status nutribot-api
sudo systemctl status nutribot-bot
```

### 7. Регистрация Mini App в BotFather

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Напиши `/newapp`
3. Выбери своего бота
4. Укажи название и описание Mini App
5. Укажи URL: `https://yourdomain.com`
6. Получишь ссылку вида `t.me/yourbotname/app`
7. Готово — Mini App доступен по ссылке и через кнопку меню бота

### 8. Обновление (деплой новой версии)

```bash
#!/bin/bash
set -e

echo "🚀 Deploying NutriBot..."

# Копируем файлы на сервер
scp -r /Users/artem/Desktop/nutrobot/ user@YOUR_VPS_IP:/opt/nutribot/

# Подключаемся и обновляем
ssh user@YOUR_VPS_IP << 'REMOTE'
  echo "📦 Installing backend deps..."
  cd /opt/nutribot/nutrition_bot
  pip3 install -r requirements.txt --quiet

  echo "🏗 Building frontend..."
  cd /opt/nutribot/miniapp
  npm install --quiet
  # Не забудь обновить BASE URL в api.js если нужно
  npm run build

  echo "🔄 Restarting services..."
  sudo systemctl restart nutribot-api
  sudo systemctl restart nutribot-bot

  echo "✅ Deploy complete!"
REMOTE

echo "🎉 Done!"
```

Сделай исполняемым и запускай:

```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Переменные окружения

| Переменная | Описание | Где взять |
|---|---|---|
| `TELEGRAM_TOKEN` | Токен Telegram-бота | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `BOT_TOKEN` | Тот же токен (для верификации WebApp) | Копия `TELEGRAM_TOKEN` |
| `OPENAI_API_KEY` | Ключ OpenAI API | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `DATABASE_PATH` | Путь к SQLite-файлу | По умолчанию `nutrition.db` |

---

## Структура проекта

```
nutrobot/
├── nutrition_bot/
│   ├── .env.example          # Шаблон переменных окружения
│   ├── .env                  # Реальные токены (не коммитить!)
│   ├── requirements.txt      # Python-зависимости
│   ├── bot.py                # Точка входа Telegram-бота (aiogram + scheduler)
│   ├── api.py                # FastAPI REST API (uvicorn :8001)
│   ├── auth.py               # Верификация Telegram WebApp initData (HMAC-SHA256)
│   ├── database.py           # Работа с SQLite (async + sync), все CRUD
│   ├── config.py             # Настройки и валидация .env
│   ├── scheduler.py          # Умные вечерние уведомления (20:00)
│   ├── handlers/
│   │   ├── __init__.py       # Регистрация роутеров (порядок важен!)
│   │   ├── start.py          # /start + FSM онбординг (выбор цели)
│   │   ├── food.py           # Анализ фото/текста/голоса → draft в FSM
│   │   ├── meal_confirm.py   # Подтверждение / редактирование / сохранение meal
│   │   ├── templates.py      # /templates, шаблоны приёмов пищи, ⭐ сохранение
│   │   └── stats.py          # /today — сводка за день
│   └── services/
│       ├── __init__.py
│       ├── openai_client.py  # GPT-4o (структура еды) + Whisper (голос) + активности
│       ├── nutrition.py      # MealAnalysis dataclass, парсинг JSON, форматирование
│       └── nutrition_db.py   # База 120+ продуктов, calculate_meal(), find_food()
├── miniapp/
│   ├── package.json          # Node-зависимости
│   ├── index.html            # Точка входа SPA + Telegram WebApp SDK
│   ├── vite.config.js        # Конфиг Vite
│   ├── src/
│   │   ├── main.jsx          # Рендер React-приложения
│   │   ├── App.jsx           # Роутинг: loading → onboarding → app
│   │   ├── api.js            # Axios-клиент + X-Init-Data interceptor
│   │   ├── index.css         # Глобальные стили
│   │   ├── components/
│   │   │   ├── BottomNav.jsx # Нижняя навигация (Дневник / Статистика / Профиль)
│   │   │   └── BottomNav.css
│   │   └── pages/
│   │       ├── DiaryPage.jsx     # Главная: кольцо калорий, еда/активности, быстрый ввод
│   │       ├── DiaryPage.css
│   │       ├── StatsPage.jsx     # Графики съедено/сожжено за 7/30 дней (Recharts)
│   │       ├── StatsPage.css
│   │       ├── ProfilePage.jsx   # Выбор цели калорий
│   │       ├── ProfilePage.css
│   │       ├── OnboardingPage.jsx # Экран приветствия и выбора цели
│   │       └── OnboardingPage.css
│   └── dist/                 # Собранный статический билд (для продакшена)
├── deploy.sh                 # Скрипт деплоя на VPS (создай сам по шаблону из README)
└── README.md                 # Этот файл
```
