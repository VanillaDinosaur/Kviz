import aiosqlite
import asyncio
import logging
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F
from base import update_quiz_index, get_quiz_index, create_table, get_quiz_score, get_quiz_best_score


# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Замените "YOUR_BOT_TOKEN" на токен, который вы получили от BotFather
API_TOKEN = '7126482209:AAGjyD2rgyF9R4D_xbLD2RODqAt3R2LzN0Q'

# Объект бота
bot = Bot(token=API_TOKEN)
# Диспетчер
dp = Dispatcher()

# Зададим имя базы данных
DB_NAME = 'quiz_bot.db'

# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))

# Хэндлер на команду /quiz
@dp.message(F.text=="Начать игру")
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):

    await message.answer(f"Давайте начнем квиз!")
    await new_quiz(message)

async def new_quiz(message):
    user_id = message.from_user.id
    current_question_index = 0
    user_score = 0
    best_user_score = await get_quiz_best_score(user_id)
    await update_quiz_index(user_id, current_question_index, user_score, best_user_score)
    await get_question(message, user_id)

def generate_options_keyboard(answer_options, right_answer):
    builder = InlineKeyboardBuilder()
    for option in answer_options:
        builder.add(types.InlineKeyboardButton(
            text=option,
            # зашифровал выбранный пользователем вариант ответа в дату, в будущем буду из неё вытаскивать
            callback_data=f"1{option[0]}" if option == right_answer else f"2{option[0]}")
        )


    builder.adjust(1)
    return builder.as_markup()

async def new_quiz(message):
    user_id = message.from_user.id
    best_user_score = await get_quiz_best_score(user_id)
    current_question_index = 0
    user_score = 0
    await update_quiz_index(user_id, current_question_index, user_score, best_user_score)
    await get_question(message, user_id)

#загружаем вопросы и ответы
df_orders = pd.read_excel('quesions.xlsx')

@dp.callback_query(F.data[0] == "1")
async def right_answer(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    # А вот и вытаскивание варианта ответа из даты
    current_question_index = await get_quiz_index(callback.from_user.id)
    answer_number = callback.data[1:] 
    options = df_orders['options'].loc[df_orders.index[current_question_index]]
    opts = tuple(options.split('/'))
    await callback.message.answer(f"{opts[int(answer_number[0])-1]}")

    await callback.message.answer("Верно!")
    user_score = await get_quiz_score(callback.from_user.id)
    best_user_score = await get_quiz_best_score(callback.from_user.id)
    # Обновление номера текущего вопроса в базе данных
    current_question_index += 1
    user_score += 1
    await update_quiz_index(callback.from_user.id, current_question_index, user_score, best_user_score)


    if current_question_index < df_orders['question'].size:
        await get_question(callback.message, callback.from_user.id)
    else:
        if best_user_score is None:
            await update_quiz_index(callback.from_user.id, current_question_index, user_score, user_score)
            best_user_score = await get_quiz_best_score(callback.from_user.id)
        if int(best_user_score) < user_score:
            await update_quiz_index(callback.from_user.id, current_question_index, user_score, user_score)
            await callback.message.answer(f"Это был последний вопрос. Квиз завершен! Твой счёт равен: {user_score}. Это твой новый рекорд!") 
        else:
            await callback.message.answer(f"Это был последний вопрос. Квиз завершен! Твой счёт равен: {user_score}. Твой лучший счёт был: {best_user_score}") 
            
        


@dp.callback_query(F.data[0] == "2")
async def wrong_answer(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

    # Получение текущего вопроса из словаря состояний пользователя
    current_question_index = await get_quiz_index(callback.from_user.id)
    user_score = await get_quiz_score(callback.from_user.id)
    best_user_score = await get_quiz_best_score(callback.from_user.id)
    correct_option = df_orders['correct_option'].loc[df_orders.index[current_question_index]]

    answer_number = callback.data[1:] 
    options = df_orders['options'].loc[df_orders.index[current_question_index]]
    opts = tuple(options.split('/'))
    await callback.message.answer(f"{opts[int(answer_number[0])-1]}")
    await callback.message.answer(f"Неправильно. Правильный ответ: {opts[correct_option]}")
    #await callback.message.answer(f"Неправильно. Правильный ответ: {quiz_data[current_question_index]['options'][correct_option]}")
    
    # Обновление номера текущего вопроса в базе данных
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index, user_score, best_user_score)


    if current_question_index < df_orders['question'].size:
        await get_question(callback.message, callback.from_user.id)
    else:
        if best_user_score is None:
            await update_quiz_index(callback.from_user.id, current_question_index, user_score, user_score)
            best_user_score = await get_quiz_best_score(callback.from_user.id)
        if int(best_user_score) < user_score:
            await update_quiz_index(callback.from_user.id, current_question_index, user_score, user_score)
            await callback.message.answer(f"Это был последний вопрос. Квиз завершен! Твой счёт равен: {user_score}. Это твой новый рекорд!") 
        else:
            await callback.message.answer(f"Это был последний вопрос. Квиз завершен! Твой счёт равен: {user_score}. Твой лучший счёт был: {best_user_score}")   


async def get_question(message, user_id):

    # Получение текущего вопроса из словаря состояний пользователя
    current_question_index = await get_quiz_index(user_id)
    options = df_orders['options'].loc[df_orders.index[current_question_index]]
    correct_index = df_orders['correct_option'].loc[df_orders.index[current_question_index]]
    opts = tuple(options.split('/'))
    kb = generate_options_keyboard(opts, opts[correct_index])
    await message.answer(f"{df_orders['question'].loc[df_orders.index[current_question_index]]}", reply_markup=kb)

# Запуск процесса поллинга новых апдейтов
async def main():

    # Запускаем создание таблицы базы данных
    await create_table()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())