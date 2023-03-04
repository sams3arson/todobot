HELP_TEXT="Привет! Это To-Do бот, в котором можно добавлять и выполнять свои задачи, "\
"а также устанавливать напоминания об их выполнении.\n\nДоступные команды:\n"\
"/add - добавить задачу\n/complete - завершить задачу\n/delete - удалить задачу\n"\
"/list - просмотреть список невыполненных задач\n/listall - все задачи\n\nПродуктивной работы!"
TASK_STATE = {0: "не выполнено", 1: "выполнено"}
COMPL_TASK_PATTERN=r"COMPLETE_TASK=(\d+)"
DEL_TASK_PATTERN=r"DELETE_TASK=(\d+)"
SWITCH_PAGE_PATTERN=r"SWITCH_PAGE=(\d+)_(\d+)"
COMMAND_RESPONSE={"complete": "Выберите задачи, которые хотите пометить как выполненные:",
                  "delete": "Выберите задачи, которые хотите удалить:"}
CALLBACK_QUERIES={"complete": "COMPLETE_TASK={}", "delete": "DELETE_TASK={}"}