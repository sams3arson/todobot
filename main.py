from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton,\
        CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tools import creds
from states import State
import settings
import texts
import sqlite3
import re

user_states = dict()
cached_markup = dict()
remind_jobs = dict()
credentials = creds.get(settings.CREDS_FILE)
api_id, api_hash, bot_token = credentials.api_id, credentials.api_hash,\
        credentials.bot_token

db = sqlite3.connect("todobot.db")
cursor = db.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS todos 
                (id integer primary key autoincrement, user_id INTEGER, 
               task TEXT, completed INTEGER)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS reminders
               (id integer primary key autoincrement, user_id INTEGER,
               interval INTEGER)""")
db.commit()

scheduler = AsyncIOScheduler()
app = Client("todo_bot", api_id, api_hash, bot_token)

def filter_state_wrapper(state):
    """Filter wrapper for Pyrogram handler of messages. Pass state 
    from states.State as argument and it will return True if the user is in 
    that state."""
    def filter_inner(filt, client: Client, update: Message):
        if user_states.get(update.from_user.id) == state:
            return True
        return False
    return filter_inner


def filter_callback_wrapper(pattern):
    """Filter wrapper for Pyrogram handler of callback queries. Pass a regex pattern
    as argument and it will return True if data of callback query matches that
    pattern."""
    def filter_inner(filt, client: Client, update: CallbackQuery):
        r = re.match(pattern, update.data)
        if r:
            return True
        return False
    return filter_inner


def start_job_interval(client: Client, user_id: int, interval: int):
    return scheduler.add_job(send_reminder, "interval", minutes=interval,
                             args=(client, user_id))


def start_intervals(client: Client):
    cursor.execute("SELECT user_id, interval FROM reminders")
    intervals_raw = cursor.fetchall()

    for user_id, interval in intervals_raw:
        remind_jobs[user_id] = start_job_interval(client, user_id, interval)


async def send_reminder(client: Client, user_id: int):
    cursor.execute("SELECT * FROM todos WHERE user_id = ? AND completed = 0",
                   (user_id,))
    tasks_raw = cursor.fetchall()

    if not tasks_raw:
        return
    return await client.send_message(user_id, "Не расслабляйтесь, у вас еще "\
            f"{len(tasks_raw)} невыполненных задач!")


@app.on_message(filters.command(["start"]))
async def start(client: Client, message: Message):
    user_id = message.from_user.id
    user_states[user_id] = State.NO_STATE
    return await message.reply("Используйте /help, чтобы получить больше информации.")


@app.on_message(filters.command(["help"]))
async def help(client: Client, message: Message):
    user_id = message.from_user.id
    user_states[user_id] = State.NO_STATE
    return await message.reply(texts.HELP_TEXT)


@app.on_message(filters.command(["add"]))
async def add(client: Client, message: Message):
    user_id = message.from_user.id
    await message.reply("Введите название задачи.")
    user_states[user_id] = State.INPUT_TASK


@app.on_message(filters.command(["current"]))
async def add(client: Client, message: Message):
    user_id = message.from_user.id
    
    cursor.execute("SELECT completed FROM todos WHERE user_id = ?", (user_id,))
    all_tasks = cursor.fetchall()
    compl_tasks = [task for task in all_tasks if task[0] == 1]

    cursor.execute("SELECT interval FROM reminders WHERE user_id = ?", (user_id,))
    intervals_raw = cursor.fetchall()

    if intervals_raw:
        interval_text = f"каждые {intervals_raw[0][0]} минут"
    else:
        interval_text = "отключены"

    return await message.reply(texts.CURRENT_TEXT.format(len(all_tasks),
         len(compl_tasks), len(all_tasks) - len(compl_tasks), interval_text))


@app.on_message(filters.command(["set_reminder"]))
async def set_reminder(client: Client, message: Message):
    user_id = message.from_user.id
    user_states[user_id] = State.INPUT_REMIND_TIME
    return await message.reply("Введите любой интервал получения напоминаний о "\
            "невыполненных задачах в минутах (0, чтобы отключить):")


@app.on_message(filters.command(["complete", "delete"]))
async def choose_task_complete(client: Client, message: Message):
    user_id = message.from_user.id
    command = message.command[0].lower()
    cursor.execute("SELECT id, task FROM todos WHERE user_id = ? AND completed = 0",
                   (user_id,))
    tasks_raw = cursor.fetchall()

    if not tasks_raw:
        return await message.reply("У вас нет невыполненных задач.")

    buttons = list()
    current_row = list()
    for task_id, task_name in tasks_raw:
        if len(current_row) == 2:
            buttons.append(current_row)
            current_row = list()
        current_row.append(InlineKeyboardButton(task_name, callback_data=
                            texts.CALLBACK_QUERIES[command].format(task_id)))
    buttons.append(current_row)

    markup = buttons[0:3]
    if len(buttons) > 3:
        markup.append([InlineKeyboardButton("➡️ На следующую страницу",
                            callback_data="SWITCH_PAGE=3_6")])

    msg = await message.reply(texts.COMMAND_RESPONSE[command],
                              reply_markup=InlineKeyboardMarkup(markup))
    cached_markup[user_id] = (buttons, msg.id)


@app.on_message(filters.command(["list"]))
async def task_list(client: Client, message: Message):
    user_id = message.from_user.id
    cursor.execute("SELECT task FROM todos WHERE "\
            "user_id = ? AND completed = 0", (user_id,))
    tasks_raw = cursor.fetchall()

    if not tasks_raw:
        return await message.reply("У вас нет невыполненных задач.")

    answer = "Невыполненные задачи:\n"
    for (task_name,) in tasks_raw:
        answer += f"- {task_name}\n"

    return await message.reply(answer)


@app.on_message(filters.command(["listall"]))
async def task_list_all(client: Client, message: Message):
    user_id = message.from_user.id
    cursor.execute("SELECT task, completed FROM todos WHERE user_id = ?",
                   (user_id,))
    tasks_raw = cursor.fetchall()

    if not tasks_raw:
        return await message.reply("У вас еще нет каких-либо задач.")

    answer = "Ваши задачи:\n"
    for task_name, is_completed in tasks_raw[-20:]: # using limit of 20 to not get over 4096 tg message limit
        answer += f"- {task_name} ({texts.TASK_STATE[is_completed]})\n"
    return await message.reply(answer)


@app.on_callback_query(filters.create(
                        filter_callback_wrapper(texts.COMPL_TASK_PATTERN)))
async def complete_task(client: Client, callback_query: CallbackQuery):
    callback_data = callback_query.data # data='COMPLETE_TASK=1'
    match = re.search(texts.COMPL_TASK_PATTERN, callback_data)
    task_id = match.group(1)

    cursor.execute("UPDATE todos SET completed = 1 WHERE id = ?", (task_id,))
    cursor.execute("SELECT * FROM todos WHERE id = ? AND completed = 1",
                   (task_id,))
    db.commit()
    res = cursor.fetchall()
    if not res:
        return await callback_query.answer(f"Похоже, этой задачи больше нет в "\
                "вашем списке.")

    return await callback_query.answer("Задача помечена как выполненная.")


@app.on_callback_query(filters.create(
                        filter_callback_wrapper(texts.DEL_TASK_PATTERN)))
async def complete_task(client: Client, callback_query: CallbackQuery):
    callback_data = callback_query.data # data='DELETE_TASK=1'
    match = re.search(texts.DEL_TASK_PATTERN, callback_data)
    task_id = match.group(1)

    cursor.execute("SELECT * FROM todos WHERE id = ?", (task_id,))
    tasks_raw = cursor.fetchall()
    if not tasks_raw:
        return await callback_query.answer("Эта задача уже не существует.")

    cursor.execute("DELETE FROM todos WHERE id = ?", (task_id,))
    db.commit()

    return await callback_query.answer("Задача удалена.")


@app.on_callback_query(filters.create(
                        filter_callback_wrapper(texts.SWITCH_PAGE_PATTERN)))
async def switch_page(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    callback_data = callback_query.data
    if not callback_query.message: # if message is too old and we can't get its object
        return await callback_query.answer("Это сообщение слишком старое, запросите новый список "\
                "и работайте с ним.")
    if isinstance(callback_data, bytes):
        callback_data = callback_data.decode()

    match = re.search(texts.SWITCH_PAGE_PATTERN, callback_data)
    start_ind, end_ind = int(match.group(1)), int(match.group(2))

    saved_buttons = cached_markup.get(user_id)
    if not saved_buttons or saved_buttons[1] != callback_query.message.id:
        return await callback_query.answer("Отправьте команду заново, чтобы "\
                "получить рабочий и актуальный список")
    buttons = saved_buttons[0]

    markup = buttons[start_ind:end_ind]
    arrows = []
    if start_ind > 0:
        arrows.append(InlineKeyboardButton("⬅️ На предыдущую страницу",
                    callback_data=f"SWITCH_PAGE={start_ind - 3}_{end_ind - 3}"))
    if len(buttons) > end_ind:
        arrows.append(InlineKeyboardButton("➡️ На следующую страницу",
                        callback_data=f"SWITCH_PAGE={start_ind + 3}_{end_ind + 3}"))
    markup.append(arrows)
    await callback_query.answer()
    return await callback_query.message.edit_reply_markup(
            InlineKeyboardMarkup(markup))


@app.on_message(filters.create(filter_state_wrapper(State.INPUT_TASK)))
async def task_name(client: Client, message: Message):
    user_id = message.from_user.id

    task_name = message.text
    
    if not task_name:
        return await message.reply("Введите название текстовым сообщением.")
    user_states[user_id] = State.NO_STATE

    cursor.execute("INSERT INTO todos (user_id, task, completed) VALUES (?, ?, 0)", 
                   (user_id, task_name))
    db.commit()
    return await message.reply(f"Задача {task_name} добавлена в ваш список задач.")


@app.on_message(filters.create(filter_state_wrapper(State.INPUT_REMIND_TIME)))
async def reminder_time(client: Client, message: Message):
    user_id = message.from_user.id
    interval = message.text

    if not interval.isdigit():
        return await message.reply("Интервал должен быть целым числом в минутах.")
    interval = int(interval)
    user_states[user_id] = State.NO_STATE

    cursor.execute("SELECT * FROM reminders WHERE user_id = ?", (user_id,))
    reminders_raw = cursor.fetchall()
    if reminders_raw:
        if interval:
            cursor.execute("UPDATE reminders SET interval = ? WHERE user_id = ?",
                           (interval, user_id))
            remind_jobs[user_id].remove()
            remind_jobs[user_id] = start_job_interval(client, user_id, interval)
            await message.reply("Установлен интервал напоминаний в "\
                    f"{interval} минут.")
        else:
            cursor.execute("DELETE FROM reminders WHERE user_id = ?", (user_id,))
            remind_jobs[user_id].remove()
            remind_jobs.pop(user_id)
            await message.reply("Напоминания отключены.")
    else:
        if interval:
            cursor.execute("INSERT INTO reminders (user_id, interval) VALUES "\
                    "(?, ?)", (user_id, interval))
            remind_jobs[user_id] = start_job_interval(client, user_id, interval)
            await message.reply("Установлен интервал напоминаний в "\
                    f"{interval} минут.")
    db.commit()


@app.on_message(filters.private)
async def respond_any_message(client: Client, message: Message):
    return await message.reply(texts.PROVIDE_HELP_TEXT)


start_intervals(app)
scheduler.start()

app.run()

