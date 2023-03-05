from typing import NamedTuple, Iterable
from os import environ, path
from pathlib import Path
from configparser import ConfigParser


CONFIG_BOTSECTION = "BOT"
VARIABLES = ("API_ID", "API_HASH", "BOT_TOKEN")


class Credentials(NamedTuple):
    api_id: int
    api_hash: str
    bot_token: str


class InvalidCredentials(Exception):
    pass


def get(filename: Path | None = None) -> Credentials:
    api_id, api_hash, bot_token = [environ.get(var_name) for var_name in
                                   VARIABLES]
    if not all((api_id, api_hash, bot_token)):
        if filename and path.exists(filename):
            api_id, api_hash, bot_token = read_config(filename)
        else:
            raise InvalidCredentials("env variables are not set, and config"\
                    " file doesn't exist")
    if api_id.isdigit():
        api_id = int(api_id)
    else:
        raise InvalidCredentials("api_id is not an integer")
    return Credentials(api_id=api_id, api_hash=api_hash, bot_token=bot_token)


def read_config(filename: Path) -> list[str]:
    parser = ConfigParser()
    parser.read(filename)

    if CONFIG_BOTSECTION not in parser:
        raise InvalidCredentials(f"config file is not valid: {CONFIG_BOTSECTION}"\
                "section not found")

    try:
        result = [str(parser[CONFIG_BOTSECTION][var_name.lower()]) for var_name
                  in VARIABLES]
    except KeyError:
        raise InvalidCredentials("config file is not valid: not all credentials"\
                " are found")

    return result

