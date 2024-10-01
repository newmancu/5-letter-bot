from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.config import get_settings
from src.handlers.game import get_rus_5l_words, guess_word, new_game
from src.handlers.main import hello
from loguru import logger


def create_app():
    get_rus_5l_words()
    logger.info("[Bot] Word dict loaded!")

    app = (
        ApplicationBuilder()
        .token(get_settings().token)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(CommandHandler("new_game", new_game))
    app.add_handler(
        MessageHandler(
            ~(filters.COMMAND | filters.UpdateType.EDITED_MESSAGE), guess_word
        )
    )
    logger.info("[Bot] App created")
    return app


def run():
    app = create_app()
    app.run_polling()
