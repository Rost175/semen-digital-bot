from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import gspread
from google.oauth2.service_account import Credentials

# ===== НАСТРОЙКИ =====
import os
import json
import tempfile
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_CHAT_ID = int(os.getenv("OWNER_CHAT_ID", "604010998"))

GOOGLE_SHEETS_ENABLED = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

BTN_BACK = "⬅️ Назад"
BTN_MENU = "🏠 Главное меню"

MAIN_MENU = [
    ["🌐 Создание сайта"],
    ["🛍 Карточки WB / Ozon"],
    ["📷 AI обработка фото"],
    ["🎭 Создать аватар"]
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
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile

GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

def upload_file_to_drive(file_path, file_name):
    scopes = ["https://www.googleapis.com/auth/drive"]

    creds = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE,
        scopes=scopes
    )

    service = build("drive", "v3", credentials=creds)

    file_metadata = {
        "name": file_name,
        "parents": [GOOGLE_DRIVE_FOLDER_ID]
    }

    media = MediaFileUpload(file_path, resumable=True)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    file_id = file.get("id")

    # делаем файл доступным по ссылке
    service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"}
    ).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"

GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

def upload_file_to_drive(file_path, file_name):
    scopes = ["https://www.googleapis.com/auth/drive"]

    creds = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE,
        scopes=scopes
    )

    service = build("drive", "v3", credentials=creds)

    file_metadata = {
        "name": file_name,
        "parents": [GOOGLE_DRIVE_FOLDER_ID]
    }

    media = MediaFileUpload(file_path, resumable=True)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    file_id = file.get("id")

    service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"}
    ).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"

def get_google_credentials():
    if not GOOGLE_CREDENTIALS_JSON:
        raise ValueError("GOOGLE_CREDENTIALS_JSON не задан")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    return Credentials.from_service_account_info(creds_dict, scopes=scopes)


def upload_file_to_drive(file_path, file_name):
    creds = get_google_credentials()
    service = build("drive", "v3", credentials=creds)

    file_metadata = {"name": file_name}
    if GOOGLE_DRIVE_FOLDER_ID:
        file_metadata["parents"] = [GOOGLE_DRIVE_FOLDER_ID]

    media = MediaFileUpload(file_path, resumable=True)

    created = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    file_id = created["id"]

    service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"}
    ).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"

# ===== GOOGLE SHEETS =====
def save_to_google_sheets(service_name: str, answers: dict):
    if not GOOGLE_SHEETS_ENABLED:
        print("Google Sheets отключен")
        return

    try:
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

        files_data = answers.get("files", [])
        files_count = len(files_data)
        files_text = "; ".join([item.get("link", "") for item in files_data if item.get("link")])

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
            files_text,
        ]

        sheet.append_row(row)
        print("Запись в Google Sheets выполнена")

    except Exception as e:
        print(f"Ошибка записи в Google Sheets: {e}")
        
# ===== ВСПОМОГАТЕЛЬНОЕ =====
def nav_keyboard():
    return ReplyKeyboardMarkup(
        [[BTN_BACK, BTN_MENU]],
        resize_keyboard=True
    )


def main_menu_keyboard():
    return ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)


async def ask_current_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service_key = context.user_data["service_key"]
    question_index = context.user_data["question_index"]

    field_name, question_text = FORMS[service_key]["fields"][question_index]
    await update.message.reply_text(question_text, reply_markup=nav_keyboard())


def build_summary(service_name: str, answers: dict) -> str:
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
        "files",
    ]

    lines = [
        "Новая заявка",
        "",
        f"Услуга: {service_name}",
        ""
    ]

    for key in order:
        if key not in answers and key != "files":
            continue

        if key == "files":
            files_count = len(answers.get("files", []))
            lines.append(f"{labels[key]}: {files_count}")
        else:
            lines.append(f"{labels[key]}: {answers.get(key, '')}")

    return "\n".join(lines)

async def send_uploaded_files_to_owner(context: ContextTypes.DEFAULT_TYPE, answers: dict, service_name: str):
    files = answers.get("files", [])

    if not files:
        return

    for item in files:
        try:
            if item["type"] == "photo":
                if item.get("file_id"):
                    await context.bot.send_photo(
                        chat_id=OWNER_CHAT_ID,
                        photo=item["file_id"],
                        caption=f"{service_name}: вложение"
                    )
                if item.get("link"):
                    await context.bot.send_message(
                        chat_id=OWNER_CHAT_ID,
                        text=f"{service_name}: ссылка на фото\n{item['link']}"
                    )

            elif item["type"] == "document":
                if item.get("file_id"):
                    await context.bot.send_document(
                        chat_id=OWNER_CHAT_ID,
                        document=item["file_id"],
                        caption=f"{service_name}: вложение"
                    )
                if item.get("link"):
                    await context.bot.send_message(
                        chat_id=OWNER_CHAT_ID,
                        text=f"{service_name}: ссылка на документ\n{item['link']}"
                    )

        except Exception as e:
            print(f"Ошибка отправки файла владельцу: {e}")

async def go_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Главное меню:", reply_markup=main_menu_keyboard())


# ===== КОМАНДЫ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Здравствуйте! Я помогу оформить заявку.",
        reply_markup=main_menu_keyboard()
    )


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(OWNER_CHAT_ID, "Тестовое сообщение от бота.")
        await update.message.reply_text("Тест отправлен.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка отправки: {e}")


# ===== ОСНОВНОЙ ОБРАБОТЧИК =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    print("PHOTO:", bool(update.message.photo))
    print("DOC:", bool(update.message.document))
    
        # обработка загрузки файлов/фото
    if "service_key" in context.user_data:
        service_key = context.user_data["service_key"]
        question_index = context.user_data.get("question_index", 0)

        if question_index < len(FORMS[service_key]["fields"]):
            field_name, _ = FORMS[service_key]["fields"][question_index]

            if field_name == "files":
                if "answers" not in context.user_data:
                    context.user_data["answers"] = {}

                if "files" not in context.user_data["answers"]:
                    context.user_data["answers"]["files"] = []

                if update.message.photo:
                    photo = update.message.photo[-1]
                    telegram_file = await context.bot.get_file(photo.file_id)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                        temp_path = tmp.name

                    await telegram_file.download_to_drive(temp_path)
                    drive_link = upload_file_to_drive(temp_path, f"{photo.file_id}.jpg")
                    os.remove(temp_path)

                    context.user_data["answers"]["files"].append({
                        "type": "photo",
                        "file_id": photo.file_id,
                        "link": drive_link
                    })

                    await update.message.reply_text("Фото загружено в Drive ✅")
                    return


                if update.message.document:
                    doc = update.message.document
                    telegram_file = await context.bot.get_file(doc.file_id)

                    suffix = ""
                    if doc.file_name and "." in doc.file_name:
                        suffix = "." + doc.file_name.split(".")[-1]

                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        temp_path = tmp.name

                    await telegram_file.download_to_drive(temp_path)
                    drive_link = upload_file_to_drive(temp_path, doc.file_name or f"{doc.file_id}")
                    os.remove(temp_path)

                    context.user_data["answers"]["files"].append({
                        "type": "document",
                        "file_id": doc.file_id,
                        "link": drive_link
                    })

                    await update.message.reply_text("Файл загружен в Drive ✅")
                    return

                if text and text.strip().upper() == "ГОТОВО":
                    # даже если файлов нет, поле files уже существует как []
                    context.user_data["question_index"] += 1

                    if context.user_data["question_index"] >= len(FORMS[service_key]["fields"]):
                        service_name = context.user_data["service_name"]
                        answers = context.user_data["answers"]

                        message = build_summary(service_name, answers)

                        try:
                            await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=message)
                            await send_uploaded_files_to_owner(context, answers, service_name)
                            save_to_google_sheets(service_name, answers)

                            await update.message.reply_text(
                                "Спасибо! Ваша заявка отправлена.",
                                reply_markup=main_menu_keyboard()
                            )
                        except Exception as e:
                            await update.message.reply_text(f"Не удалось отправить заявку: {e}")

                        context.user_data.clear()
                        return

                    await ask_current_question(update, context)
                    return
    # Главное меню
    if text == BTN_MENU:
        await go_main_menu(update, context)
        return

    # Старт новой анкеты
    if text in FORMS:
        context.user_data.clear()
        context.user_data["service_key"] = text
        context.user_data["service_name"] = FORMS[text]["service_name"]
        context.user_data["question_index"] = 0
        context.user_data["answers"] = {}
        await ask_current_question(update, context)
        return

    # Если анкета ещё не выбрана
    if "service_key" not in context.user_data:
        await update.message.reply_text(
            "Пожалуйста, выберите услугу кнопкой ниже.",
            reply_markup=main_menu_keyboard()
        )
        return

    # Назад
    if text == BTN_BACK:
        if context.user_data["question_index"] > 0:
            context.user_data["question_index"] -= 1
            service_key = context.user_data["service_key"]
            field_name, _ = FORMS[service_key]["fields"][context.user_data["question_index"]]
            context.user_data["answers"].pop(field_name, None)
        await ask_current_question(update, context)
        return

    # Сохраняем текущий ответ
    service_key = context.user_data["service_key"]
    question_index = context.user_data["question_index"]
    field_name, _ = FORMS[service_key]["fields"][question_index]

    context.user_data["answers"][field_name] = text

    # Переходим к следующему вопросу
    context.user_data["question_index"] += 1

    # Если вопросы закончились
    if context.user_data["question_index"] >= len(FORMS[service_key]["fields"]):
        service_name = context.user_data["service_name"]
        answers = context.user_data["answers"]

        message = build_summary(service_name, answers)

        try:
            await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=message)
            save_to_google_sheets(service_name, answers)
            await update.message.reply_text(
                "Спасибо! Ваша заявка отправлена.",
                reply_markup=main_menu_keyboard()
            )
        except Exception as e:
            await update.message.reply_text(f"Не удалось отправить заявку: {e}")

        context.user_data.clear()
        return

    # Иначе спрашиваем следующий вопрос
    await ask_current_question(update, context)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("test", test))
app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, handle))

print("БОТ ЗАПУЩЕН")
app.run_polling()

