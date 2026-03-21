import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any

import gspread
from google.oauth2.service_account import Credentials

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_CHAT_ID = int(os.getenv("OWNER_CHAT_ID", "604010998"))

GOOGLE_SHEETS_ENABLED = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

BTN_BACK = "⬅️ Назад"
BTN_MENU = "🏠 Главное меню"
BTN_DONE = "ГОТОВО"

MAIN_MENU = [
    ["🌐 Создание сайта"],
    ["🛍 Карточки WB / Ozon"],
    ["📷 AI обработка фото"],
    ["🎭 Создать аватар"],
]

FORMS = {
    "🌐 Создание сайта": {
        "service_name": "Создание сайта",
        "fields": [
            ("name", "Как вас зовут?"),
            ("contact", "Ваш контакт? Укажите Telegram, телефон или e-mail."),
            ("site_type", "Какой сайт нужен?"),
            ("business", "Чем вы занимаетесь? Кратко опишите ваш бизнес или проект."),
            ("audience", "Для кого этот сайт? Кто ваша целевая аудитория?"),
            ("goal", "Какая основная цель сайта? Например: заявки, продажи, портфолио, презентация."),
            ("examples", "Есть ли сайты, которые вам нравятся? Пришлите ссылку или напишите «нет»."),
            ("texts", "Есть ли тексты для сайта? Напишите: да / нет / частично."),
            ("timeline", "Когда нужен запуск сайта?"),
            ("comment", "Дополнительные пожелания? Если нет — напишите «нет»."),
        ],
    },
    "🛍 Карточки WB / Ozon": {
        "service_name": "Карточки WB / Ozon",
        "fields": [
            ("name", "Как вас зовут?"),
            ("contact", "Ваш контакт?"),
            ("market", "Для какого маркетплейса? Напишите: WB / Ozon / оба."),
            ("product", "Что за товар?"),
            ("count", "Сколько карточек нужно сделать?"),
            ("photos", "Есть ли фотографии товара?"),
            ("tz", "Есть ли техническое задание?"),
            ("files", "Прикрепите фото товара, ТЗ или референсы. Когда закончите, напишите: ГОТОВО"),
            ("timeline", "Когда нужен результат?"),
            ("comment", "Дополнительные пожелания?"),
        ],
    },
    "📷 AI обработка фото": {
        "service_name": "AI обработка фото",
        "fields": [
            ("name", "Как вас зовут?"),
            ("contact", "Ваш контакт?"),
            ("object", "Что нужно обработать? Например: товар, портрет, интерьер."),
            ("count", "Сколько фотографий?"),
            ("style", "Какой стиль обработки нужен?"),
            ("files", "Прикрепите фотографии для обработки. Когда закончите, напишите: ГОТОВО"),
            ("timeline", "Когда нужен результат?"),
            ("comment", "Дополнительные пожелания?"),
        ],
    },
    "🎭 Создать аватар": {
        "service_name": "Создание аватара",
        "fields": [
            ("name", "Как вас зовут?"),
            ("contact", "Ваш контакт?"),
            ("style", "Какой стиль аватара нужен?"),
            ("use", "Где будет использоваться аватар?"),
            ("files", "Прикрепите свои фото или референсы. Когда закончите, напишите: ГОТОВО"),
            ("comment", "Дополнительные пожелания?"),
        ],
    },
}

# Порядок колонок в Google Sheets
SHEET_HEADERS = [
    "Дата",
    "Услуга",
    "Имя",
    "Контакт",
    "Тип сайта",
    "Бизнес / проект",
    "Целевая аудитория",
    "Цель сайта",
    "Примеры сайтов",
    "Тексты",
    "Маркетплейс",
    "Товар",
    "Количество",
    "Фото товара",
    "Техническое задание",
    "Что обработать",
    "Стиль",
    "Где будет использоваться",
    "Сроки",
    "Комментарий",
    "Количество файлов",
    "Типы файлов",
    "Имена файлов",
    "file_id / photo_id",
    "Username Telegram",
    "Telegram user_id",
]

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# =========================================================
# GOOGLE SHEETS
# =========================================================

def validate_env() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден")

    if GOOGLE_SHEETS_ENABLED:
        if not GOOGLE_SHEET_ID:
            raise ValueError("GOOGLE_SHEET_ID не задан")
        if not GOOGLE_CREDENTIALS_JSON:
            raise ValueError("GOOGLE_CREDENTIALS_JSON не задан")


def get_google_credentials() -> Credentials:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    return Credentials.from_service_account_info(creds_dict, scopes=scopes)


def get_sheet():
    creds = get_google_credentials()
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    sheet = spreadsheet.sheet1
    return sheet


def ensure_sheet_headers() -> None:
    if not GOOGLE_SHEETS_ENABLED:
        return

    try:
        sheet = get_sheet()
        first_row = sheet.row_values(1)
        if first_row != SHEET_HEADERS:
            if not first_row:
                sheet.append_row(SHEET_HEADERS)
            else:
                # если в таблице уже что-то есть, просто обновим первую строку
                end_col = len(SHEET_HEADERS)
                sheet.update(f"A1:{column_letter(end_col)}1", [SHEET_HEADERS])
        logger.info("Заголовки Google Sheets проверены")
    except Exception as e:
        logger.exception("Ошибка при проверке заголовков Google Sheets: %s", e)


def column_letter(n: int) -> str:
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


def serialize_files_for_sheet(files_data: List[Dict[str, Any]]):
    files_count = len(files_data)
    file_types = []
    file_names = []
    file_ids = []

    for item in files_data:
        file_types.append(item.get("type", ""))

        if item.get("file_name"):
            file_names.append(item["file_name"])
        else:
            file_names.append("")

        if item.get("file_id"):
            file_ids.append(item["file_id"])

    return (
        files_count,
        "; ".join(file_types),
        "; ".join(file_names),
        "; ".join(file_ids),
    )


def save_to_google_sheets(service_name: str, answers: dict, update: Update) -> None:
    if not GOOGLE_SHEETS_ENABLED:
        logger.info("Google Sheets отключен")
        return

    try:
        sheet = get_sheet()

        files_data = answers.get("files", [])
        files_count, file_types_text, file_names_text, file_ids_text = serialize_files_for_sheet(files_data)

        tg_username = update.effective_user.username if update.effective_user else ""
        tg_user_id = str(update.effective_user.id) if update.effective_user else ""

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            service_name,
            answers.get("name", ""),
            answers.get("contact", ""),
            answers.get("site_type", ""),
            answers.get("business", ""),
            answers.get("audience", ""),
            answers.get("goal", ""),
            answers.get("examples", ""),
            answers.get("texts", ""),
            answers.get("market", ""),
            answers.get("product", ""),
            answers.get("count", ""),
            answers.get("photos", ""),
            answers.get("tz", ""),
            answers.get("object", ""),
            answers.get("style", ""),
            answers.get("use", ""),
            answers.get("timeline", ""),
            answers.get("comment", ""),
            files_count,
            file_types_text,
            file_names_text,
            file_ids_text,
            f"@{tg_username}" if tg_username else "",
            tg_user_id,
        ]

        sheet.append_row(row, value_input_option="USER_ENTERED")
        logger.info("Запись в Google Sheets выполнена")

    except Exception as e:
        logger.exception("Ошибка записи в Google Sheets: %s", e)


# =========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def nav_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[BTN_BACK, BTN_MENU]], resize_keyboard=True)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)


def get_current_field(context: ContextTypes.DEFAULT_TYPE):
    service_key = context.user_data["service_key"]
    question_index = context.user_data["question_index"]
    return FORMS[service_key]["fields"][question_index]


async def ask_current_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    service_key = context.user_data["service_key"]
    question_index = context.user_data["question_index"]

    _, question_text = FORMS[service_key]["fields"][question_index]
    await update.message.reply_text(question_text, reply_markup=nav_keyboard())


def build_summary(service_name: str, answers: dict, update: Update) -> str:
    labels = {
        "name": "Имя",
        "contact": "Контакт",
        "site_type": "Тип сайта",
        "business": "Бизнес / проект",
        "audience": "Целевая аудитория",
        "goal": "Цель сайта",
        "examples": "Примеры сайтов",
        "texts": "Тексты",
        "market": "Маркетплейс",
        "product": "Товар",
        "count": "Количество",
        "photos": "Фото товара",
        "tz": "Техническое задание",
        "object": "Что обработать",
        "style": "Стиль",
        "use": "Где будет использоваться",
        "timeline": "Сроки",
        "comment": "Дополнительные пожелания",
        "files": "Вложения",
    }

    order = [
        "name",
        "contact",
        "site_type",
        "business",
        "audience",
        "goal",
        "examples",
        "texts",
        "market",
        "product",
        "count",
        "photos",
        "tz",
        "object",
        "style",
        "use",
        "timeline",
        "comment",
    ]

    lines = [
        "Новая заявка",
        "",
        f"Услуга: {service_name}",
    ]

    if update.effective_user:
        lines.append(f"Telegram user_id: {update.effective_user.id}")
        if update.effective_user.username:
            lines.append(f"Username: @{update.effective_user.username}")

    lines.append("")

    for key in order:
        if key in answers:
            lines.append(f"{labels[key]}: {answers.get(key, '')}")

    if "files" in answers:
        files_count = len(answers.get("files", []))
        lines.append(f"{labels['files']}: {files_count}")

    return "\n".join(lines)


async def send_uploaded_files_to_owner(
    context: ContextTypes.DEFAULT_TYPE,
    answers: dict,
    service_name: str
) -> None:
    files = answers.get("files", [])

    if not files:
        return

    for index, item in enumerate(files, start=1):
        try:
            caption = f"{service_name}: вложение {index}"

            if item["type"] == "photo" and item.get("file_id"):
                await context.bot.send_photo(
                    chat_id=OWNER_CHAT_ID,
                    photo=item["file_id"],
                    caption=caption
                )

            elif item["type"] == "document" and item.get("file_id"):
                await context.bot.send_document(
                    chat_id=OWNER_CHAT_ID,
                    document=item["file_id"],
                    caption=caption
                )

        except Exception as e:
            logger.exception("Ошибка отправки файла владельцу: %s", e)


async def go_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.message.reply_text("Главное меню:", reply_markup=main_menu_keyboard())


def clear_current_answer(context: ContextTypes.DEFAULT_TYPE) -> None:
    service_key = context.user_data["service_key"]
    question_index = context.user_data["question_index"]

    if question_index < len(FORMS[service_key]["fields"]):
        field_name, _ = FORMS[service_key]["fields"][question_index]
        context.user_data.setdefault("answers", {}).pop(field_name, None)


# =========================================================
# КОМАНДЫ
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.message.reply_text(
        "Здравствуйте! Я помогу оформить заявку.",
        reply_markup=main_menu_keyboard()
    )


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await context.bot.send_message(OWNER_CHAT_ID, "Тестовое сообщение от бота.")
        await update.message.reply_text("Тест отправлен.")
    except Exception:
        logger.exception("Ошибка отправки тестового сообщения")
        await update.message.reply_text("Не удалось отправить тестовое сообщение.")


# =========================================================
# ОБРАБОТКА ФАЙЛОВ НА ШАГЕ files
# =========================================================

async def process_files_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Возвращает True, если сообщение обработано как шаг files.
    """
    service_key = context.user_data["service_key"]
    question_index = context.user_data.get("question_index", 0)

    if question_index >= len(FORMS[service_key]["fields"]):
        return False

    field_name, _ = FORMS[service_key]["fields"][question_index]
    if field_name != "files":
        return False

    answers = context.user_data.setdefault("answers", {})
    files = answers.setdefault("files", [])

    text = update.message.text.strip() if update.message.text else ""

    # Пользователь завершил загрузку файлов
    if text.upper() == BTN_DONE:
        context.user_data["question_index"] += 1

        if context.user_data["question_index"] >= len(FORMS[service_key]["fields"]):
            service_name = context.user_data["service_name"]
            answers = context.user_data["answers"]

            message = build_summary(service_name, answers, update)

            try:
                await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=message)
                await send_uploaded_files_to_owner(context, answers, service_name)
                save_to_google_sheets(service_name, answers, update)

                await update.message.reply_text(
                    "Спасибо! Ваша заявка отправлена.",
                    reply_markup=main_menu_keyboard()
                )
            except Exception:
                logger.exception("Ошибка финальной отправки заявки")
                await update.message.reply_text(
                    "Не удалось отправить заявку. Проверьте настройки бота и таблицы."
                )

            context.user_data.clear()
            return True

        await ask_current_question(update, context)
        return True

    # Фото
    if update.message.photo:
        photo = update.message.photo[-1]
        files.append({
            "type": "photo",
            "file_id": photo.file_id,
            "file_name": "",
        })

        await update.message.reply_text(
            "Фото добавлено. Можете прислать ещё или написать: ГОТОВО",
            reply_markup=nav_keyboard()
        )
        return True

    # Документ
    if update.message.document:
        doc = update.message.document
        files.append({
            "type": "document",
            "file_id": doc.file_id,
            "file_name": doc.file_name or "",
            "mime_type": doc.mime_type or "",
        })

        await update.message.reply_text(
            "Файл добавлен. Можете прислать ещё или написать: ГОТОВО",
            reply_markup=nav_keyboard()
        )
        return True

    # Любой другой текст
    await update.message.reply_text(
        "Пришлите фото/файл или напишите: ГОТОВО",
        reply_markup=nav_keyboard()
    )
    return True


# =========================================================
# ОСНОВНОЙ ОБРАБОТЧИК
# =========================================================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    text = update.message.text.strip() if update.message.text else ""

    # 1. Главное меню
    if text == BTN_MENU:
        await go_main_menu(update, context)
        return

    # 2. Выбор услуги из меню
    if text in FORMS:
        context.user_data.clear()
        context.user_data["service_key"] = text
        context.user_data["service_name"] = FORMS[text]["service_name"]
        context.user_data["question_index"] = 0
        context.user_data["answers"] = {}
        await ask_current_question(update, context)
        return

    # 3. Если услуга не выбрана
    if "service_key" not in context.user_data:
        await update.message.reply_text(
            "Пожалуйста, выберите услугу кнопкой ниже.",
            reply_markup=main_menu_keyboard()
        )
        return

    # 4. Назад
    if text == BTN_BACK:
        if context.user_data["question_index"] > 0:
            context.user_data["question_index"] -= 1
            service_key = context.user_data["service_key"]
            field_name, _ = FORMS[service_key]["fields"][context.user_data["question_index"]]
            context.user_data.setdefault("answers", {}).pop(field_name, None)

        await ask_current_question(update, context)
        return

    # 5. Специальная обработка шага files
    processed = await process_files_step(update, context)
    if processed:
        return

    # 6. Обычные текстовые вопросы
    service_key = context.user_data["service_key"]
    question_index = context.user_data["question_index"]
    field_name, _ = FORMS[service_key]["fields"][question_index]

    # На обычных шагах принимаем только текст
    if not update.message.text:
        await update.message.reply_text(
            "Пожалуйста, отправьте текстовый ответ.",
            reply_markup=nav_keyboard()
        )
        return

    context.user_data["answers"][field_name] = text
    context.user_data["question_index"] += 1

    # 7. Завершение анкеты
    if context.user_data["question_index"] >= len(FORMS[service_key]["fields"]):
        service_name = context.user_data["service_name"]
        answers = context.user_data["answers"]

        message = build_summary(service_name, answers, update)

        try:
            await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=message)
            await send_uploaded_files_to_owner(context, answers, service_name)
            save_to_google_sheets(service_name, answers, update)

            await update.message.reply_text(
                "Спасибо! Ваша заявка отправлена.",
                reply_markup=main_menu_keyboard()
            )
        except Exception:
            logger.exception("Ошибка финальной отправки заявки")
            await update.message.reply_text(
                "Не удалось отправить заявку. Проверьте настройки бота и таблицы."
            )

        context.user_data.clear()
        return

    await ask_current_question(update, context)


# =========================================================
# ЗАПУСК
# =========================================================

def main() -> None:
    validate_env()

    if GOOGLE_SHEETS_ENABLED:
        ensure_sheet_headers()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
            handle
        )
    )

    logger.info("БОТ ЗАПУЩЕН")
    app.run_polling()


if __name__ == "__main__":
    main()

