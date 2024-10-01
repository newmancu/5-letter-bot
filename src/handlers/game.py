from functools import cache, cached_property
import random
import re
from telegram import Update
from telegram.ext import ContextTypes
from pydantic import BaseModel, Field

from src.config import get_settings
from src.core.exceptions import NonRussionWordError, WordLenMismatch

from loguru import logger

RU_5LETTER_PATTERN = re.compile(r"[абвгдеёжзийклмнопрстуфхцчшщъыьэюя]{5}$")


@cache
def get_rus_5l_words() -> list[str]:
    with open("config/russian-5-w.utf-8", "r") as inpt:
        res = [r.strip().lower() for r in inpt.readlines()]
    return res


def gen_word() -> str:
    words = get_rus_5l_words()
    return random.choice(words)


class WordGuess(BaseModel):
    word: str
    right_letters: set = Field(default_factory=set)
    right_position: list = Field(default_factory=list)

    @classmethod
    def from_word(cls, word: str, ans_word: str):
        ret = cls(word=word)
        for i, l in enumerate(word):
            rp = False
            if l in ans_word:
                ret.right_letters.add(l)
                if l == ans_word[i]:
                    rp = True
            ret.right_position.append(rp)
        return ret

    @property
    def ok(self) -> bool:
        return all(self.right_position)

    def to_tg_msg(self) -> str:
        res = ""
        for i in range(len(self.word)):
            if self.right_position[i]:
                res += f"<b>{self.word[i]}</b> "
            elif self.word[i] in self.right_letters:
                res += f"<i>{self.word[i]}</i> "
            else:
                res += f"<s>{self.word[i]}</s> "
        return res


class GameSession(BaseModel):
    word: str = Field(default_factory=gen_word)
    word_tries: list[WordGuess] = Field(default_factory=list)

    @cached_property
    def max_tries(self) -> int:
        return get_settings().max_tries

    @property
    def tries(self) -> int:
        return len(self.word_tries)

    @property
    def last_tries(self) -> int:
        return self.max_tries - self.tries

    @property
    def ended(self) -> bool:
        return self.tries >= self.max_tries

    def validate_word(self, word: str):
        l1, l2 = len(word), len(self.word)
        if l1 != l2:
            raise WordLenMismatch(l1, l2)
        if not RU_5LETTER_PATTERN.match(word):
            raise NonRussionWordError()

    def guess_word(self, word: str):
        word = word.lower()
        self.validate_word(word)
        guess_result = WordGuess.from_word(word, self.word)
        self.word_tries.append(guess_result)
        return guess_result


async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    game = GameSession()
    context.user_data["session"] = game
    await update.message.reply_text(
        f"Новая игра создана. У вас есть {game.max_tries} попыток, чтоб"
        f" угадать слово из {len(game.word)} букв. Удачи!"
    )


async def guess_word(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    context.user_data.setdefault("session", GameSession())
    game: GameSession = context.user_data.get("session")
    if game.ended:
        await update.message.reply_text("Предыдущая игра завершилась")
        return await new_game(update, context)

    try:
        word = update.message.text
        guess = game.guess_word(word)
        if guess.ok:
            await update.message.reply_text("Поздравляем! Вы угадали слово!")
            context.user_data.pop("session", None)
        else:
            msg = "Увы, но слово вы не отгадали."
            MODE = "Markdown"
            if game.ended:
                msg += (
                    " У вас больше не осталось попыток. Мы загадали слово"
                    f" `{game.word.upper()}`. Сыграйте еще раз и попробуйте"
                    " угадать новое слово!"
                )
            else:
                MODE = "HTML"
                msg += (
                    f"У вас отслось {game.last_tries} попыток, чтоб угадать"
                    " слово. Результат последней"
                    f" попытки:\n\n{guess.to_tg_msg()}"
                )
            await update.message.reply_text(msg, parse_mode=MODE)

    except WordLenMismatch as e:
        await update.message.reply_text(
            f"Введите слово из {e.expected_len} букв. Попытка не засчитана"
        )

    except NonRussionWordError:
        await update.message.reply_text(
            "Введенное слово не является русским. Попытка не засчитана"
        )

    except BaseException as e:
        logger.error(f"{e} | {str(e)}")
        await update.message.reply_text("Что-то пошло не так")
