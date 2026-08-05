"""
server.py — ПАРСИ в облаке: справка для всех + удалённое управление по ключу.

СГЕНЕРИРОВАНО из parsee-desktop/src/main/mcp-server.js — не редактировать руками
блок ниже отметки "СГЕНЕРИРОВАНО ДАЛЬШЕ", правки потеряются при пересборке
(node parsee-mcp/scripts/generate.js). Верхнюю часть (parsee_cloud_*) — можно.

Два режима на одном адресе, без ключа не различить какой сервер вызвали:
  • без Bearer-ключа — parsee_cloud_* рассказывают, что такое ПАРСИ и как подключиться.
    Данных здесь нет и быть не может: это просто справка.
  • с Bearer-ключом удалённого доступа (выдаёт приложение, окно «Подключить ИИ» →
    «Удалённый доступ») — работают настоящие 28 инструментов parsee_*, каждый пересылает
    вызов на relay.parsee.ru, тот держит связь с приложением на компьютере продавца
    (см. parsee-relay/server.js и parsee-desktop/src/main/remote-relay.js) и выполняет
    его там же — теми же функциями, что и обычный локальный сбор.
"""

import json
import os
from pathlib import Path
from typing import Optional, Literal

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
import httpx

HERE = Path(__file__).parent
SITE = "https://parsee.ru"
LOCAL_URL = "http://127.0.0.1:7317/mcp"
RELAY_URL = os.environ.get("PARSEE_RELAY_URL", "https://relay.parsee.ru:8443")


def _read(name: str, default: str = "") -> str:
    try:
        return (HERE / name).read_text(encoding="utf-8")
    except OSError:
        return default


INSTRUCTIONS = f"""ПАРСИ — приложение для сбора и мониторинга товаров Ozon и Wildberries.

Этот сервер работает в двух режимах на одном адресе:
• БЕЗ ключа — вы не подключены ни к чьему приложению. Доступны только parsee_cloud_* —
  расскажут, что такое ПАРСИ, и как подключиться (parsee_cloud_setup). Инструменты parsee_*
  (без cloud_) в этом режиме ответят ошибкой «ключ не найден» — это ожидаемо, не баг.
• С Bearer-ключом удалённого доступа — вы подключены к конкретному компьютеру продавца.
  Все 28 инструментов parsee_* работают по-настоящему: ищут, собирают, читают данные —
  выполняются на том компьютере, под его сессиями площадок, результат приходит сюда.

Если пользователь спрашивает, что умеет ПАРСИ — parsee_cloud_about и parsee_cloud_tools.
Если хочет подключить — parsee_cloud_setup, там оба способа: локально (127.0.0.1, тот же
компьютер) и удалённо (ключ + этот адрес, с любого устройства).
Не выдумывайте данные о товарах, если ключ не передан — у сервера в этом режиме их нет."""

mcp = FastMCP(name="parsee-mcp", instructions=INSTRUCTIONS)


@mcp.tool
def parsee_cloud_about() -> str:
    """Что такое ПАРСИ и кому нужна: коротко о продукте и о двух способах подключения."""
    return f"""ПАРСИ — приложение для продавцов Ozon и Wildberries.

Умеет:
• собирать карточки товаров: цена и цена с картой, рейтинг, отзывы, наличие,
  схема продаж, характеристики, фото;
• следить за конкурентами и своими карточками, показывая «было → стало»;
• сравнивать свою карточку с чужой парами и считать, у кого дешевле;
• считать СПП — скидку, которую площадка даёт сверх скидки продавца;
• запускаться по расписанию и выгружать всё в Excel.

Собирает всегда с компьютера продавца — под его IP и его сессиями площадок, иначе
маркетплейсы считают сбор роботом. Подключиться к нему можно двумя способами:
локально (сервер на 127.0.0.1, только этот компьютер) или удалённо — через этот
облачный адрес и ключ, с любого устройства. Данные в обоих случаях идут напрямую
с компьютера продавца, второй способ лишь передаёт команды через сервер ПАРСИ.

Приложение: {SITE}"""


@mcp.tool
def parsee_cloud_setup(client: str = "any") -> str:
    """Как подключить ПАРСИ к ассистенту — локально (тот же компьютер) или удалённо (с любого устройства). client: claude-code, claude-desktop, kimi, cursor или any."""
    local_cfg = json.dumps(
        {"mcpServers": {"parsee": {"url": LOCAL_URL, "headers": {"Authorization": "Bearer ВАШ_КЛЮЧ"}}}},
        ensure_ascii=False, indent=2,
    )
    remote_cfg = json.dumps(
        {"mcpServers": {"parsee-remote": {"url": "https://parsee-mcp.fastmcp.app/mcp",
                                           "headers": {"Authorization": "Bearer ВАШ_УДАЛЁННЫЙ_КЛЮЧ"}}}},
        ensure_ascii=False, indent=2,
    )
    health_url = LOCAL_URL.replace("/mcp", "/health")
    return f"""Подключение ПАРСИ к ассистенту — два способа.

СПОСОБ 1 · локально (ассистент на том же компьютере, что и приложение)
1. Установите и запустите приложение: {SITE}
2. Возьмите ключ в приложении: окно «Подключить ИИ», строка psk_…
3. Конфигурация:
{local_cfg}
   Проверить, что приложение работает: curl {health_url}

СПОСОБ 2 · удалённо (с любого устройства — телефон, другой компьютер, облако)
1. В приложении: «Подключить ИИ» → «Удалённый доступ» → включить, получить ключ prk_…
2. Тот же адрес, что у этого сервера, но со своим ключом:
{remote_cfg}
   Работает, только пока приложение владельца запущено и удалённый доступ включён.

После подключения любым способом ассистент получит инструкцию и 28 инструментов."""


@mcp.tool
def parsee_cloud_tools(section: str = "all") -> str:
    """Список всех инструментов ПАРСИ. section: search, groups, analytics, settings или all."""
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
    parts.append("Без ключа удалённого доступа эти инструменты (без cloud_) ответят ошибкой — это нормально.")
    return "\n".join(parts)


@mcp.tool
def parsee_cloud_manual() -> str:
    """Полная инструкция, которую сервер отдаёт ассистенту при подключении с ключом."""
    text = _read("llms.txt")
    return text or f"Инструкция недоступна. Смотрите {SITE}"


# ══════════════════════════ СГЕНЕРИРОВАНО ДАЛЬШЕ — не редактировать руками ══════════════════════════

async def _relay_call(tool: str, args: dict) -> dict:
    # get_http_headers() по умолчанию вырезает authorization (защита от случайной утечки) —
    # для прокси это единственный заголовок, который и нужно прокинуть дальше, поэтому просим явно.
    headers = get_http_headers(include={"authorization"})
    auth = headers.get("authorization", "")
    if not auth:
        return {"error": "Нет ключа удалённого доступа. parsee_cloud_setup — как его получить."}
    clean = {k: v for k, v in args.items() if v is not None}
    async with httpx.AsyncClient(timeout=65) as client:
        try:
            r = await client.post(RELAY_URL + "/call", json={"tool": tool, "args": clean},
                                   headers={"Authorization": auth, "Content-Type": "application/json"})
        except httpx.RequestError as e:
            return {"error": f"Нет связи с сервером ПАРСИ: {e}"}
    try:
        return r.json()
    except ValueError:
        return {"error": f"Сервер ответил не JSON (HTTP {r.status_code})"}


@mcp.tool
async def parsee_help() -> dict:
    """Полная инструкция по ПАРСИ — та же, что отдаёт локальный сервер при подключении."""
    return await _relay_call("parsee_help", {})


@mcp.tool
async def parsee_get_region() -> dict:
    """
    Из какого города ПАРСИ смотрит цены. Это важно: у одного товара в Москве и Владивостоке разные
    цена и наличие. Возвращает текущий город и список доступных.
    """
    return await _relay_call("parsee_get_region", {})

@mcp.tool
async def parsee_set_region(city: str) -> dict:
    """
    Меняет город, из которого смотрятся цены на Wildberries и Ozon. На WB это код пункта назначения,
    на Ozon — географическое положение браузера; ассистенту эта разница не важна, достаточно назвать
    город. Уже собранные данные не пересчитываются — после смены запустите проверку заново.
    """
    return await _relay_call("parsee_set_region", {"city": city})

@mcp.tool
async def parsee_create_group(section: Literal["monitor", "compare", "spp"], name: str, items: Optional[list] = None, pairs: Optional[list] = None, fromCabinet: Optional[bool] = None, vendorFilter: Optional[str] = None) -> dict:
    """
    Создаёт группу и сразу наполняет её. section: monitor (следить за карточками), compare (пары
    «моя ↔ конкурент»), spp (скидка постоянного покупателя). Для monitor: items — ссылки или
    артикулы. Для compare: pairs — [{mine, rival}]. Для spp: items — [{url, sent}], где sent — цена,
    переданная площадке; либо fromCabinet: true — тогда артикулы и цены возьмём прямо из кабинета
    WB.
    """
    return await _relay_call("parsee_create_group", {"section": section, "name": name, "items": items, "pairs": pairs, "fromCabinet": fromCabinet, "vendorFilter": vendorFilter})

@mcp.tool
async def parsee_add_to_group(group: str, items: Optional[list] = None, pairs: Optional[list] = None, section: Optional[Literal["monitor", "compare", "spp"]] = None) -> dict:
    """
    Добавляет позиции в существующую группу. Раздел определится по названию группы. Для сравнения
    передавайте pairs: [{mine, rival}], для СПП items: [{url, sent}], для мониторинга items: ссылки
    или артикулы.
    """
    return await _relay_call("parsee_add_to_group", {"group": group, "items": items, "pairs": pairs, "section": section})

@mcp.tool
async def parsee_remove_from_group(group: str, items: list, section: Optional[Literal["monitor", "compare", "spp"]] = None) -> dict:
    """
    Убирает позиции из группы по ссылке или артикулу. Сама группа остаётся.
    """
    return await _relay_call("parsee_remove_from_group", {"group": group, "items": items, "section": section})

@mcp.tool
async def parsee_rename_group(group: str, newName: str, section: Optional[Literal["monitor", "compare", "spp"]] = None) -> dict:
    """
    Меняет название группы. История проверок сохраняется.
    """
    return await _relay_call("parsee_rename_group", {"group": group, "newName": newName, "section": section})

@mcp.tool
async def parsee_delete_group(group: str, confirm: Optional[bool] = None, section: Optional[Literal["monitor", "compare", "spp"]] = None) -> dict:
    """
    Удаляет группу вместе с историей проверок. Необратимо: сначала спросите пользователя, потом
    вызовите с confirm: true.
    """
    return await _relay_call("parsee_delete_group", {"group": group, "confirm": confirm, "section": section})

@mcp.tool
async def parsee_wait(timeoutSec: Optional[int] = None) -> dict:
    """
    Ждёт, пока закончится сбор или проверка, и только потом отвечает. Вызывайте сразу после
    parsee_parse_urls, parsee_parse_category или parsee_run_check — иначе придётся вслепую дёргать
    статус. По умолчанию ждёт 300 секунд; если не успело, скажет, сколько сделано, и можно подождать
    ещё раз.
    """
    return await _relay_call("parsee_wait", {"timeoutSec": timeoutSec})

@mcp.tool
async def parsee_monitor_changes(group: Optional[str] = None, limit: Optional[int] = None) -> dict:
    """
    Что изменилось у отслеживаемых товаров с прошлой проверки: цена (было, стало, процент), наличие,
    схема продаж, рейтинг, новинки. Без группы — по последней проверке.
    """
    return await _relay_call("parsee_monitor_changes", {"group": group, "limit": limit})

@mcp.tool
async def parsee_compare_diff(group: str, limit: Optional[int] = None) -> dict:
    """
    По группе сравнения: моя карточка против конкурента — цена, рейтинг, отзывы, разница в цене и
    кто дешевле. Группа должна быть хотя бы раз собрана.
    """
    return await _relay_call("parsee_compare_diff", {"group": group, "limit": limit})

@mcp.tool
async def parsee_wb_cabinet(action: Optional[Literal["status", "sync"]] = None, search: Optional[str] = None, limit: Optional[int] = None) -> dict:
    """
    Цены, которые продавец передал Wildberries — источник для расчёта СПП. action: status —
    подключён ли кабинет; sync — обновить и показать цены (nmID, артикул продавца, переданная цена,
    цена WB Клуба). Ключ доступа вводит владелец в приложении, ассистенту он не виден.
    """
    return await _relay_call("parsee_wb_cabinet", {"action": action, "search": search, "limit": limit})

@mcp.tool
async def parsee_parse_category(url: str, limit: Optional[int] = None, onlyLinks: Optional[bool] = None) -> dict:
    """
    Разворачивает ссылку на категорию, выдачу поиска, бренд или продавца в список карточек и
    запускает сбор по ним. Так берут рынок целиком, вместо перебора выдачи по одной странице.
    onlyLinks: true — только вернуть ссылки, без сбора.
    """
    return await _relay_call("parsee_parse_category", {"url": url, "limit": limit, "onlyLinks": onlyLinks})

@mcp.tool
async def parsee_get_results(limit: Optional[int] = None, offset: Optional[int] = None, search: Optional[str] = None, full: Optional[bool] = None) -> dict:
    """
    Отдаёт данные последнего сбора: цена, старая цена, цена с картой, рейтинг, число отзывов,
    наличие, бренд, категория, ссылка. Это и есть результат parsee_parse_urls — именно по нему
    делают выводы, а не по выдаче поиска. По умолчанию 50 карточек; листайте через offset, ищите
    через search, full: true отдаёт карточку целиком (характеристики, описание, фото).
    """
    return await _relay_call("parsee_get_results", {"limit": limit, "offset": offset, "search": search, "full": full})

@mcp.tool
async def parsee_get_schedule(group: Optional[str] = None) -> dict:
    """
    Показывает, когда группы запускаются сами: по дням недели в заданное время или каждые N часов.
    Без параметра — все расписания (сбор, мониторинг, СПП).
    """
    return await _relay_call("parsee_get_schedule", {"group": group})

@mcp.tool
async def parsee_set_schedule(group: str, mode: Optional[Literal["week", "every"]] = None, days: Optional[list] = None, times: Optional[list] = None, everyHours: Optional[int] = None, from_: Optional[str] = None, to: Optional[str] = None, enabled: Optional[bool] = None) -> dict:
    """
    Ставит автоматический запуск группы. Два режима. По дням недели: mode="week", days=[1..7]
    (1=Пн), times=["09:00","18:00"]. Каждые N часов: mode="every", everyHours=6, при желании окно
    from/to (например с 08:00 до 22:00; окно может идти через полночь). Время — по Москве. Чтобы
    выключить, передайте enabled=false. Работает для групп сбора, мониторинга и СПП — раздел
    определяется по названию группы.
    """
    return await _relay_call("parsee_set_schedule", {"group": group, "mode": mode, "days": days, "times": times, "everyHours": everyHours, "from": from_, "to": to, "enabled": enabled})

@mcp.tool
async def parsee_export(format: Optional[Literal["excel", "csv", "json", "zip"]] = None) -> dict:
    """
    Сохраняет собранные карточки файлом в папку «Загрузки». Форматы: excel (таблица), csv, json, zip
    (архив с фото и файлами). Excel оформлен: цены и проценты числами, ссылки кликаются. Работает по
    последнему сбору; если карточек нет — сначала parsee_parse_urls.
    """
    return await _relay_call("parsee_export", {"format": format})

@mcp.tool
async def parsee_stop() -> dict:
    """
    Останавливает идущий сбор. Уже собранные карточки сохраняются — их можно выгрузить. Если ничего
    не выполняется, честно об этом сообщит.
    """
    return await _relay_call("parsee_stop", {})

@mcp.tool
async def parsee_status() -> dict:
    """
    Что сейчас происходит в приложении: версия, вход в аккаунт и тариф, вход на Ozon и Wildberries,
    идёт ли сбор и на каком он шаге, сколько карточек уже собрано. Стоит вызывать перед долгими
    действиями: если сбор уже идёт, второй запускать не нужно.
    """
    return await _relay_call("parsee_status", {})

@mcp.tool
async def parsee_get_options() -> dict:
    """
    Какие данные собирает ПАРСИ: фото (и их качество), видео, отзывы и их количество, вопросы,
    характеристики, описание, данные продавца, карта доставки, упаковка в ZIP, лимит товаров из
    категории, режим скорости. Возвращает текущие значения и список допустимых режимов.
    """
    return await _relay_call("parsee_get_options", {})

@mcp.tool
async def parsee_set_options(images: Optional[bool] = None, imageQuality: Optional[Literal["orig", "std", "small"]] = None, imageMode: Optional[Literal["all", "cover"]] = None, video: Optional[bool] = None, stripMetadata: Optional[bool] = None, reviews: Optional[bool] = None, reviewsLimit: Optional[int] = None, reviewsWithText: Optional[bool] = None, questions: Optional[bool] = None, questionsLimit: Optional[int] = None, characteristics: Optional[bool] = None, description: Optional[bool] = None, sellerData: Optional[bool] = None, deliveryMap: Optional[bool] = None, zip: Optional[bool] = None, categoryLimit: Optional[int] = None, mode: Optional[Literal["fast", "opt", "safe"]] = None) -> dict:
    """
    Меняет настройки перед сбором. Передавайте только то, что нужно изменить, остальное останется
    как было. Например: {"images": false, "reviews": true, "reviewsLimit": 200, "mode": "safe"}.
    Режим скорости: fast (быстрее, выше риск блокировки), opt (по умолчанию), safe (медленнее,
    бережнее). Отключение фото и отзывов заметно ускоряет сбор.
    """
    return await _relay_call("parsee_set_options", {"images": images, "imageQuality": imageQuality, "imageMode": imageMode, "video": video, "stripMetadata": stripMetadata, "reviews": reviews, "reviewsLimit": reviewsLimit, "reviewsWithText": reviewsWithText, "questions": questions, "questionsLimit": questionsLimit, "characteristics": characteristics, "description": description, "sellerData": sellerData, "deliveryMap": deliveryMap, "zip": zip, "categoryLimit": categoryLimit, "mode": mode})

@mcp.tool
async def parsee_list_groups(section: Optional[Literal["all", "monitor", "compare", "spp"]] = None) -> dict:
    """
    Группы пользователя в ПАРСИ: мониторинг цен, сравнение с конкурентами и СПП. Возвращает
    название, раздел, число товаров и время последней проверки. С этого стоит начинать: дальше по
    названию группы работают остальные инструменты.
    """
    return await _relay_call("parsee_list_groups", {"section": section})

@mcp.tool
async def parsee_get_prices(group: str, limit: Optional[int] = None) -> dict:
    """
    Текущие цены, наличие и рейтинг товаров группы по последней проверке. Показывает и цену на
    витрине, и цену с картой/кошельком. Данные уже собраны, ответ мгновенный.
    """
    return await _relay_call("parsee_get_prices", {"group": group, "limit": limit})

@mcp.tool
async def parsee_spp_changes(group: Optional[str] = None) -> dict:
    """
    Где сдвинулась скидка постоянного покупателя: было, стало, разница в процентных пунктах. СПП =
    (цена, переданная площадке − цена на витрине) / переданная × 100. Используй, когда спрашивают
    «где просела скидка» или «что изменилось по СПП».
    """
    return await _relay_call("parsee_spp_changes", {"group": group})

@mcp.tool
async def parsee_price_history(item: str, days: Optional[int] = None) -> dict:
    """
    Как менялась цена товара за период по сохранённым проверкам. Товар задаётся ссылкой или
    артикулом.
    """
    return await _relay_call("parsee_price_history", {"item": item, "days": days})

@mcp.tool
async def parsee_browser_search(query: str, marketplace: Literal["wb", "ozon"], limit: Optional[int] = None) -> dict:
    """
    Ищет товары на Ozon или Wildberries через встроенный браузер и возвращает СПИСОК КАРТОЧЕК СО
    ССЫЛКАМИ — то, что видно в выдаче. Данных о товаре здесь нет: ни точной цены, ни рейтинга, ни
    отзывов, ни наличия. Это способ найти товары, а не изучить их: получив ссылки, запустите
    parsee_parse_urls — он и даст цены, рейтинг, отзывы и наличие. Выводы о рынке по одной выдаче
    делать нельзя. Вызывать строго по одному запросу за раз: браузер один на всех. Конкретные
    запросы («аэрогриль 8 литров») работают, общие («аэрогриль») почти всегда пустые.
    """
    return await _relay_call("parsee_browser_search", {"query": query, "marketplace": marketplace, "limit": limit})

@mcp.tool
async def parsee_parse_urls(urls: list) -> dict:
    """
    Запускает сбор карточек по списку ссылок или артикулов: название, цены, рейтинг, отзывы, фото.
    Идёт на компьютере пользователя с обычными паузами, занимает время — вернёт «задача запущена»,
    результат смотри через parsee_list_groups и parsee_get_prices.
    """
    return await _relay_call("parsee_parse_urls", {"urls": urls})

@mcp.tool
async def parsee_run_check(group: str, kind: Literal["monitor", "spp"]) -> dict:
    """
    Запускает проверку группы: мониторинг цен или СПП. Занимает время, вернёт «задача запущена».
    """
    return await _relay_call("parsee_run_check", {"group": group, "kind": kind})


if __name__ == "__main__":
    mcp.run()
