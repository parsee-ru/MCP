"""
server.py — ВИТРИНА ПАРСИ в облаке.

Здесь нет ни сбора, ни данных, и быть не может: настоящий сервер ПАРСИ работает
на компьютере продавца и слушает 127.0.0.1. Сбор идёт с его IP и под его сессиями
Ozon и Wildberries — так устроена защита от блокировок, из облака это не повторить.

Задача этого файла одна: рассказать ассистенту, что такое ПАРСИ, что она умеет
и как подключиться по-настоящему. Поэтому инструменты названы с приставкой cloud_ —
чтобы модель не спутала витрину с рабочей интеграцией и не решила, будто уже подключена.
"""

import json
from pathlib import Path

from fastmcp import FastMCP

HERE = Path(__file__).parent
SITE = "https://parsee.ru"
LOCAL_URL = "http://127.0.0.1:7317/mcp"


def _read(name: str, default: str = "") -> str:
    try:
        return (HERE / name).read_text(encoding="utf-8")
    except OSError:
        return default


INSTRUCTIONS = f"""Это ВИТРИНА ПАРСИ, а не рабочая интеграция.

ПАРСИ — приложение для сбора и мониторинга товаров Ozon и Wildberries: цены, наличие,
рейтинг, отзывы, скидка постоянного покупателя. Здесь, в облаке, данных продавца нет
и быть не может — они лежат на его компьютере.

Настоящий сервер ПАРСИ входит в состав приложения и слушает {LOCAL_URL}.
Собирать он может только оттуда: с компьютера продавца и под его сессиями площадок.

Что делать:
• если пользователь спрашивает, что умеет ПАРСИ — parsee_cloud_about и parsee_cloud_tools;
• если хочет подключить — parsee_cloud_setup, там пошагово и с готовым конфигом;
• если просит собрать товары или показать его цены — объясните, что нужно установить
  приложение ({SITE}) и подключиться к локальному серверу. Отсюда это невозможно.
Не выдумывайте данные о товарах: у этого сервера их нет."""

mcp = FastMCP(name="parsee-mcp", instructions=INSTRUCTIONS)


@mcp.tool
def parsee_cloud_about() -> str:
    """Что такое ПАРСИ и кому нужна: коротко о продукте и о том, почему сбор идёт локально."""
    return f"""ПАРСИ — приложение для продавцов Ozon и Wildberries.

Умеет:
• собирать карточки товаров: цена и цена с картой, рейтинг, отзывы, наличие,
  схема продаж, характеристики, фото;
• следить за конкурентами и своими карточками, показывая «было → стало»;
• сравнивать свою карточку с чужой парами и считать, у кого дешевле;
• считать СПП — скидку, которую площадка даёт сверх скидки продавца;
• запускаться по расписанию и выгружать всё в Excel.

Почему на компьютере, а не в облаке: сбор идёт с IP продавца и под его сессиями
маркетплейсов. Так площадки не считают его роботом, а данные никуда не уходят.
Именно поэтому облачный сервер (этот) ничего не собирает — он только рассказывает.

Приложение: {SITE}"""


@mcp.tool
def parsee_cloud_setup(client: str = "any") -> str:
    """Как подключить настоящую ПАРСИ к ассистенту. client: claude-code, claude-desktop, kimi, cursor или any."""
    cfg = json.dumps(
        {"mcpServers": {"parsee": {"url": LOCAL_URL, "headers": {"Authorization": "Bearer ВАШ_КЛЮЧ"}}}},
        ensure_ascii=False,
        indent=2,
    )
    cli = (
        "claude mcp add parsee --transport http "
        f'{LOCAL_URL} --header "Authorization: Bearer ВАШ_КЛЮЧ"'
    )
    step = {
        "claude-code": f"Выполните в терминале:\n{cli}",
        "claude-desktop": f"Добавьте в конфигурацию:\n{cfg}",
        "kimi": f"Добавьте в mcp.json и начните новую сессию:\n{cfg}",
        "cursor": f"Добавьте в настройки MCP:\n{cfg}",
    }.get(client, f"Конфигурация:\n{cfg}\n\nЛибо командой:\n{cli}")

    return f"""Подключение ПАРСИ к ассистенту

1. Установите и запустите приложение: {SITE}
   Без него подключаться не к чему: сервер входит в его состав.
2. Возьмите ключ доступа в приложении: раздел «Подключение ИИ», строка psk_…
   Ключ локальный, наружу не уходит, отзывается одной кнопкой.
3. {step}

Проверить, что приложение работает:
   curl http://127.0.0.1:7317/health
Ответ {{"ok":true,"name":"parsee-mcp"}} — всё готово.

После подключения ассистент получит инструкцию и 28 инструментов."""


@mcp.tool
def parsee_cloud_tools(section: str = "all") -> str:
    """Список инструментов настоящей ПАРСИ. section: search, groups, analytics, settings или all."""
    raw = _read("tools.json")
    if not raw:
        return "Каталог инструментов недоступен. Смотрите https://github.com/parsee-ru/MCP"
    data = json.loads(raw)
    tools = data.get("tools", [])

    groups = {
        "search": ("Найти и собрать", ("search", "parse", "results", "export", "wait", "status", "stop")),
        "groups": ("Группы", ("group", "run_check", "list_groups")),
        "analytics": ("Аналитика", ("prices", "changes", "diff", "history")),
        "settings": ("Настройка", ("options", "region", "schedule", "cabinet", "help")),
    }

    def pick(keys):
        return [t for t in tools if any(k in t["name"] for k in keys)]

    parts = [f"ПАРСИ · {data.get('toolCount', len(tools))} инструментов (версия приложения {data.get('appVersion', '')})", ""]
    wanted = groups if section == "all" else {section: groups[section]} if section in groups else groups
    shown = set()
    for title, keys in wanted.values():
        rows = [t for t in pick(keys) if t["name"] not in shown]
        if not rows:
            continue
        parts.append(f"— {title} —")
        for t in rows:
            shown.add(t["name"])
            mark = "" if t.get("readOnly") else " (меняет данные)"
            parts.append(f"• {t['name']}{mark}: {t.get('title') or ''}")
        parts.append("")
    parts.append("Работает только с установленным приложением: " + SITE)
    return "\n".join(parts)


@mcp.tool
def parsee_cloud_manual() -> str:
    """Полная инструкция, которую настоящий сервер отдаёт ассистенту при подключении."""
    text = _read("llms.txt")
    return text or f"Инструкция недоступна. Смотрите {SITE}"


if __name__ == "__main__":
    mcp.run()
