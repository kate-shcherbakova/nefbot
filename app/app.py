# await: Ключевое слово await используется в асинхронных функциях Python для ожидания выполнения асинхронной операции. Это позволяет боту продолжать обработку других событий и запросов во время ожидания выполнения данной операции.
# update: Объект update представляет собой входящее обновление от Telegram и содержит информацию о событии, например, отправленное сообщение.
# message: Атрибут message объекта update содержит информацию о сообщении, которое вызвало данное обновление.
# reply_text(): Метод reply_text() используется для отправки текстового ответа пользователю. Он принимает один обязательный аргумент — текстовое сообщение, которое бот хочет отправить.
# update.message.text: Это часть аргумента reply_text(). update.message.text представляет текстовое содержимое исходного сообщения, которое пользователь отправил.

import mysql.connector
import logging

from telegram import __version__ as TG_VER
from collections import defaultdict

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.ext import CallbackContext

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This app is not compatible with your current PTB version {TG_VER}."
    )

# Create a global database connection object
db_connection = None


def connect_to_db():
    global db_connection
    try:
        db_connection = mysql.connector.connect(
            host="nef_db",
            port=3306,
            user="nef_user",
            password="nef_pass",
            database="nef_db",  # Set the default database
            charset="utf8mb4"  # In order to except Ukrainian characters
        )
        logger.info("Connection to the nef_db established")
    except mysql.connector.Error as err:
        logger.info(f"Error with connection to the nef_db: {err}")


def create_tables():
    if db_connection is None:
        logger.info("Database connection not established")
        return

    try:
        cursor = db_connection.cursor()

        # Create categories table
        create_categories_table = """
        CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            name_ua VARCHAR(255) NOT NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        """

        # ---
        # create_categories_table = """
        # DROP TABLE questions; DROP TABLE categories;
        # """
        # ---

        cursor.execute(create_categories_table)
        cursor.close();
        db_connection.commit()

        # Create questions table
        create_questions_table = """
        CREATE TABLE IF NOT EXISTS questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            question_text TEXT NOT NULL,
            answer TEXT NOT NULL,
            category_id INT,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        """
        cursor = db_connection.cursor()
        cursor.execute(create_questions_table)
        cursor.close();
        db_connection.commit()

        logger.info("Tables created successfully!")

    except mysql.connector.Error as err:
        logger.info(f"Database Error: {err}")
    finally:
        if cursor:
            cursor.close()


def populate_database():
    if db_connection is None:
        logger.info("Database connection not established")
        return

    try:
        cursor = db_connection.cursor()

        # Populate categories
        categories = [
            ("University", "Університет"),
            ("Administrative", "Адміністративні питання"),
            ("Leisure", "Відпочинок"),
        ]

        category_insert_query = """
            INSERT INTO categories (name, name_ua) 
            VALUES (%s, %s) 
            ON DUPLICATE KEY UPDATE name=name, name_ua=name_ua
        """
        cursor.executemany(category_insert_query, categories)
        db_connection.commit()

        # Get category IDs
        category_id_mapping = {}
        cursor.execute("SELECT id, name FROM categories")
        categories_rows = cursor.fetchall()
        for category_id, category_name in categories_rows:
            category_id_mapping[category_name] = category_id

        # Populate questions and answers
        questions_and_answers = [
            ("Як українському студенту вступити до французького університету?", "Не так вже й просто.", "University"),
            ("Як українцю отримати APS?", "Зверніться до префектури.", "Administrative"),
            ("Як українцю отримати виплати?", "Зверніться до OFII.", "Administrative"),
            ("Що таке TP?", "Це практичне заняття.", "University"),
            ("Що можна робити зі студентським квитком?", "Вільно відвідувати музеї.", "Leisure"),
            ("Як студент може поїхати у відпустку?", "Зверніться до depart 18:25.", "Leisure"),
        ]

        question_insert_query = """
            INSERT INTO questions (question_text, answer, category_id)
            SELECT %s, %s, %s
            FROM dual
            WHERE NOT EXISTS (
                SELECT 1 FROM questions
                WHERE question_text = %s AND category_id = %s
            )
        """

        for question_text, answer, category_name in questions_and_answers:
            category_id = category_id_mapping.get(category_name)
            if category_id:
                cursor.execute(question_insert_query, (question_text, answer, category_id, question_text, category_id))
                db_connection.commit()

        logger.info("Database populated successfully")

    except mysql.connector.Error as err:
        logger.info(f"Database Error: {err}")
    finally:
        if cursor:
            cursor.close()


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("No no no es /start command")
    user = update.effective_user

    # Send a welcome message to the user
    await update.message.reply_text(
        rf"Привіт {user.full_name}! 😜"
        + "\n"
        + "\nЯ бот від організації \"Наше студентство у Франції\". Є питання, але немає відповіді? Можливо, ти знайдеш її тут."
        + "\nЯк я працюю:"
        + "\n1. Натисни кнопку \"*Категорії питань*\", щоб обрати тему, яка тебе цікавить."
        + "\n2. Вибери питання з обраної категорії та отримай відповідь."
        + "\n"
        + "\nЯкщо у тебе є технічні проблеми, запитання або побажання, натисни кнопку \"*Зворотній зв'язок*\", щоб надіслати повідомлення технічному відділу."
        + "\n"
        + "\n🇺🇦"
        , parse_mode='Markdown')

    # Call the function to show the main menu
    await show_main_menu(user)


async def show_main_menu(user):
    # Create an inline keyboard with buttons for "Категорії питань" and "Зворотній зв'язок"
    keyboard = [[
        InlineKeyboardButton("Категорії питань", callback_data="show_categories"),
        InlineKeyboardButton("Зворотній зв'язок", callback_data="help")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the main menu with the inline keyboard
    await user.send_message(
        "Вибери дію:",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user

    if update.callback_query:  # Check if the update is a callback query
        # Edit the message with the help text
        await update.callback_query.message.edit_text(
            "Ця команда призначена для надання допомоги користувачам. 📝"
        )

        # Ask the user to write their problem
        await update.callback_query.message.reply_text("Будь ласка, опиши свою проблему, питання або пропозицію:")

        # Update user data to indicate waiting for help response
        context.user_data["waiting_for_help_response"] = True
    else:
        # Handle the case where /help command is manually typed
        await update.message.reply_text(
            "Ця команда призначена для надання допомоги користувачам. Технічний відділ обов'язково опрацює твій запит."
        )

        # Ask the user to write their problem
        await update.message.reply_text("Будь ласка, опиши свою проблему, питання або пропозицію:")

        # Update user data to indicate waiting for help response
        context.user_data["waiting_for_help_response"] = True


async def handle_help_response(update: Update, context: CallbackContext) -> None:
    if context.user_data.get("waiting_for_help_response"):
        user_text = update.message.text
        user_id = 383320439

        # Send the user's text to @kate_shch
        await context.bot.send_message(user_id,
                                       f"Проблема від користувача {update.effective_user.full_name}"
                                       + "\n"
                                       + "\nТекст повідомлення:"
                                       + f"\n{user_text}"
                                       )
        # + f"\n\n{update.effective_user}:"

        # Display a thank-you message to the user
        await update.message.reply_text(
            "Дякую за відгук! ☺"
            "\nТвоє повідомлення було відправлено технічному відділу."
            "\nМи намагатимемося надати тобі допомогу якнайшвидше."
        )

        # Display the main menu with "Категорії питань" and "Зворотній зв'язок" buttons
        # keyboard = [
        #     [InlineKeyboardButton("Категорії питань", callback_data="show_categories")],
        #     [InlineKeyboardButton("Зворотній зв'язок", callback_data="help")]
        # ]
        # reply_markup = InlineKeyboardMarkup(keyboard)
        # await update.message.reply_text("Вибери дію:", reply_markup=reply_markup)

        # Call the function to show the main menu
        await show_main_menu(update.effective_user)

        # Reset the waiting_for_help_response flag
        context.user_data["waiting_for_help_response"] = False


async def show_categories(update: Update, context: CallbackContext) -> None:
    logger.info("No no no es /show_categories command")
    query = update.callback_query
    # await query.answer()  # Acknowledge the button press

    try:
        cursor = db_connection.cursor()

        # Fetch category names and their Ukrainian translations from the database
        cursor.execute("SELECT name, name_ua FROM categories")
        categories_rows = cursor.fetchall()
        category_data = [(row[0], row[1]) for row in categories_rows]

        # Create inline keyboard buttons for each category
        keyboard = [
            [InlineKeyboardButton(name_ua, callback_data=f"category_{name}")]
            for name, name_ua in category_data
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.message.edit_text("Оберіть категорію:", reply_markup=reply_markup)
        await query.message.edit_reply_markup(reply_markup)


    except mysql.connector.Error as err:
        logger.info(f"Database Error: {err}")

    finally:
        if cursor:
            cursor.close()


async def show_questions(update: Update, context: CallbackContext) -> None:
    logger.info("No no no es /show_questions command")
    query = update.callback_query
    # await query.answer()  # Acknowledge the button press

    # Extract the category name from the callback data
    category_name = query.data.replace("category_", "")

    try:
        cursor = db_connection.cursor()

        # Query the database to get questions and answers for the selected category
        cursor.execute("""
            SELECT questions.id, questions.question_text, questions.answer
            FROM questions
            INNER JOIN categories ON questions.category_id = categories.id
            WHERE categories.name = %s
        """, (category_name,))
        questions_and_answers_rows = cursor.fetchall()

        # Create inline keyboard buttons for each question
        keyboard = []
        for question_id, question, answer in questions_and_answers_rows:
            # Create a button for each question using question_id and answer_id
            callback_data = f"answer_{question_id}"
            keyboard.append([InlineKeyboardButton(question, callback_data=callback_data)])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_reply_markup(reply_markup)

    except mysql.connector.Error as err:
        logger.info(f"Database Error: {err}")

    finally:
        if cursor:
            cursor.close()


async def answer_question(update: Update, context: CallbackContext) -> None:
    logger.info("No no no es /answer_question command")
    query = update.callback_query
    question_id = query.data.replace("answer_", "")

    try:
        cursor = db_connection.cursor()

        # Query the database to get the question and answer by their IDs
        cursor.execute("SELECT question_text, answer FROM questions WHERE id = %s", (question_id,))
        question_text, answer = cursor.fetchone()

        # Send the question and answer as a reply to the user's click
        await query.message.reply_text(f"Питання: \n{question_text}"
                                       + "\n"
                                       + f"\nВідповідь: \n{answer}"
                                       )

        # Call the function to show the main menu
        await show_main_menu(update.effective_user)

    except mysql.connector.Error as err:
        logger.info(f"Database Error: {err}")

    finally:
        if cursor:
            cursor.close()


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("6334101248:AAH_0Rf7oNVFcyl3PKcHyLB62IQROHJURSk").build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(CallbackQueryHandler(show_categories, pattern='show_categories'))
    application.add_handler(CallbackQueryHandler(show_questions, pattern=r'category_'))
    application.add_handler(CallbackQueryHandler(answer_question, pattern='answer_'))
    application.add_handler(CallbackQueryHandler(help_command, pattern='help'))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_help_response))
    # on non command i.e message
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    connect_to_db()
    create_tables()
    populate_database()
    main()

    # # Keep the connection open
    # while True:
    #     pass
