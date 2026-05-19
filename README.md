# МЕТР² ПОД КЛЮЧ — Telegram-бот

Сбор заявок на готовые дизайн-проекты под планировки ЖК «Первый Нагатинский».

## Стек
Python 3.10+, aiogram 3.x, SQLite, systemd-сервис на VPS.

## Сценарии
- `/start` — приветствие + каталог проектов
- `/start project_<id>` — deep-link с сайта на конкретный проект
- FSM-анкета: имя → телефон → канал связи → сроки → согласие → сохранение
- Уведомление админу при новой заявке

## Админ-команды (только для `ADMIN_USERNAME`)
- `/stats` — сводка по заявкам и просмотрам
- `/orders` — последние 20 заявок
- `/projects` — каталог со счётчиками
- `/admin` — меню админа

## Деплой на VPS
См. [deploy/install.sh](deploy/install.sh). Запускается один раз от root, всё ставится автоматом.

## Локальный запуск
```bash
pip install -r requirements.txt
export BOT_TOKEN=...
python -B bot.py
```

## Env-переменные
| Variable | Default | Описание |
|---|---|---|
| `BOT_TOKEN` | — | Токен от @BotFather |
| `ADMIN_USERNAME` | `Dmitry_Dolgoter` | Telegram-username владельца (без `@`) |
| `BOT_DB_PATH` | `/tmp/metr2.sqlite3` | Путь к SQLite-файлу |
| `PRIVACY_POLICY_URL` | плейсхолдер | Ссылка на политику конфиденциальности |
