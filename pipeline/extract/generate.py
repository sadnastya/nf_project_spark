import argparse
import calendar
import csv
import json
import time
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import settings

SEED = 20240101
EPOCH_YEAR = 2020  # нумерация id транзакций ведётся от января 2020 года (как serial в БД)

# (регион в нотации X5, город, относительная «населённость»)
REGIONS = [
    ("Москва", "Москва", 12.0), ("Санкт-Петербург", "Санкт-Петербург", 5.5),
    ("Московская область", "Подольск", 4.0), ("Краснодарский край", "Сочи", 2.0),
    ("Краснодарский край", "Краснодар", 2.5), ("Свердловская область", "Екатеринбург", 3.0),
    ("Новосибирская область", "Новосибирск", 2.8), ("Республика Татарстан", "Казань", 2.6),
    ("Нижегородская область", "Нижний Новгород", 2.3), ("Самарская область", "Самара", 2.2),
    ("Ростовская область", "Ростов-на-Дону", 2.4), ("Челябинская область", "Челябинск", 2.1),
    ("Башкортостан", "Уфа", 2.0), ("Пермский край", "Пермь", 1.8),
    ("Воронежская область", "Воронеж", 1.8), ("Волгоградская область", "Волгоград", 1.7),
    ("Красноярский край", "Красноярск", 1.7), ("Саратовская область", "Саратов", 1.4),
    ("Тюменская область", "Тюмень", 1.2), ("Омская область", "Омск", 1.4),
    ("Приморский край", "Владивосток", 1.0), ("Хабаровский край", "Хабаровск", 0.9),
    ("Калининградская область", "Калининград", 0.9), ("Ярославская область", "Ярославль", 0.9),
    ("Тульская область", "Тула", 0.9), ("Курская область", "Курск", 0.7),
    ("Ульяновская область", "Ульяновск", 0.8), ("Оренбургская область", "Оренбург", 0.8),
    ("Ставропольский край", "Ставрополь", 0.8), ("Архангельская область", "Архангельск", 0.6),
    ("Кемеровская область", "Кемерово", 0.9), ("Брянская область", "Брянск", 0.6),
]
STREETS = ["Ленина", "Советская", "Мира", "Гагарина", "Пушкинская", "Молодёжная", "Садовая",
           "Лесная", "Школьная", "Набережная", "Победы", "Кирова", "Московская", "Заводская",
           "Центральная", "Октябрьская", "Комсомольская", "Первомайская", "Строителей", "Солнечная"]
MALE_NAMES = ["Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Алексей", "Артём", "Илья",
              "Кирилл", "Михаил", "Никита", "Матвей", "Роман", "Егор", "Иван", "Павел", "Олег"]
FEMALE_NAMES = ["Анастасия", "Мария", "Анна", "Виктория", "Екатерина", "Наталья", "Марина",
                "Полина", "Дарья", "Елена", "Ольга", "Татьяна", "Ксения", "Алиса", "Софья"]
SURNAMES = ["Иванов", "Смирнов", "Кузнецов", "Попов", "Васильев", "Петров", "Соколов",
            "Михайлов", "Новиков", "Фёдоров", "Морозов", "Волков", "Алексеев", "Лебедев",
            "Семёнов", "Егоров", "Павлов", "Козлов", "Степанов", "Николаев", "Орлов"]

# Юрлица ритейлеров (по ним формируются терминалы магазинов)
MAGNIT_LE = ("АО \"Тандер\"", "magnit.ru")
PYATEROCHKA_LE = ("ООО \"Агроторг\"", "5ka.ru")
PEREKRESTOK_LE = ("АО \"ТД Перекрёсток\"", "perekrestok.ru")
# Прочие мерчанты: (название, домен, кол-во терминалов в банке, mu логнормальной суммы, online)
OTHER_MERCHANTS = [
    ("ООО \"Лента\"", "lenta.com", 220, 7.0, False),
    ("ООО \"ВкусВилл\"", "vkusvill.ru", 160, 6.4, False),
    ("ООО \"Ашан\"", "auchan.ru", 140, 7.3, False),
    ("ООО \"Дикси Юг\"", "dixy.ru", 120, 6.0, False),
    ("ООО \"Фикс Прайс\"", "fix-price.com", 140, 5.6, False),
    ("ООО \"Спортмастер\"", "sportmaster.ru", 60, 8.2, False),
    ("ООО \"МВМ\"", "mvideo.ru", 50, 9.0, False),
    ("ООО \"ДНС Ритейл\"", "dns-shop.ru", 60, 8.8, False),
    ("АО \"Аптечная сеть 36,6\"", "366.ru", 90, 6.6, False),
    ("ООО \"Шоколадница\"", "shoko.ru", 70, 6.5, False),
    ("ООО \"Теремок\"", "teremok.ru", 60, 6.2, False),
    ("ООО \"Леруа Мерлен Восток\"", "leroymerlin.ru", 40, 8.5, False),
    ("ООО \"Интернет Решения\"", "ozon.ru", 6, 7.4, True),
    ("ООО \"Вайлдберриз\"", "wildberries.ru", 6, 7.2, True),
    ("ООО \"Яндекс.Такси\"", "taxi.yandex.ru", 4, 6.3, True),
]

# «Хвост» малого бизнеса: сгенерированные мерчанты (кафе, аптеки, ...): (вид, mu суммы)
SMALL_KINDS = [("Кафе", 6.3), ("Кофейня", 5.6), ("Пекарня", 5.5), ("Аптека", 6.5), ("Цветы", 7.2),
               ("Зоомагазин", 6.8), ("Оптика", 8.3), ("Хозтовары", 6.9), ("Книжный", 6.7),
               ("Автомойка", 7.1), ("Салон красоты", 7.6), ("Фитнес-клуб", 8.0)]
SMALL_NAMES = ["Берёзка", "Уют", "Ромашка", "Восход", "Север", "Родник", "Лидер", "Каскад", "Радуга",
               "Меридиан", "Гармония", "Сфера", "Вектор", "Престиж", "Магистраль", "Олимп"]

# Масштаб справочников (клиенты, счета, магазины, терминалы, мерчанты); транзакции — TX_PER_MONTH
SCALE = settings.DATA_SCALE


def _scaled(n: int) -> int:
    return max(1, int(round(n * SCALE)))


SEASON = {1: 0.85, 2: 0.85, 3: 0.95, 4: 0.95, 5: 1.0, 6: 1.0,
          7: 1.0, 8: 1.05, 9: 1.0, 10: 1.0, 11: 1.05, 12: 1.3}
BANK_SHARE = {"bank1": 1.0, "bank2": 0.8}
HOUR_WEIGHTS = np.array([0.2, 0.1, 0.05, 0.05, 0.05, 0.1, 0.4, 1.0, 2.0, 2.5, 3.0, 3.5,
                         4.5, 4.5, 4.0, 3.8, 4.0, 5.0, 6.0, 6.0, 5.0, 3.5, 2.0, 0.8])
WEEKDAY_WEIGHTS = np.array([0.95, 0.95, 1.0, 1.0, 1.1, 1.2, 1.05])  # пн..вс


def _digits(rng, n, length):
    return ["".join(map(str, row)) for row in rng.integers(0, 10, size=(n, length))]


def _read_seed(name, sep):
    path = settings.SEED_DIR / name
    return pd.read_csv(path, sep=sep) if path.exists() else None


def _magnit_region(region: str, rng) -> str:
    region = region.replace("область", "обл.")
    if region.endswith("край") and rng.random() < 0.2:
        region = region.replace("край", "кray")  # 'r', 'a', 'y' — латиница
    return region


@lru_cache(maxsize=1)
def build_world():
    rng = np.random.default_rng(SEED)
    region_w = np.array([r[2] for r in REGIONS]) / sum(r[2] for r in REGIONS)

    # ---------- X5 ----------
    x5_types = _read_seed("x5_data/store_types.csv", ",")
    if x5_types is None:
        x5_types = pd.DataFrame({"id": [1, 2, 3, 4], "type": ["Пятерочка", "Пятёрочка Макси",
                                                             "Перекресток", "Перекресток-экспресс"]})
    x5_term_types = pd.DataFrame({"id": [1, 2], "type": ["Касса", "Самообслуживание"]})
    n_x5 = _scaled(1600)
    x5_type_w = np.array([0.66, 0.06, 0.18, 0.10])[: len(x5_types)]
    x5_store_type = rng.choice(x5_types["id"].to_numpy(), n_x5, p=x5_type_w / x5_type_w.sum())
    reg_idx = rng.choice(len(REGIONS), n_x5, p=region_w)
    x5_stores = pd.DataFrame({
        "id": np.arange(1, n_x5 + 1),
        "region": [REGIONS[i][0] for i in reg_idx],
        "city": [REGIONS[i][1] for i in reg_idx],
        "address": [f"ул. {s} {h}" for s, h in zip(rng.choice(STREETS, n_x5), rng.integers(1, 200, n_x5))],
        "store_type": x5_store_type,
    })
    x5_type_name = dict(zip(x5_types["id"], x5_types["type"]))

    # ---------- Магнит ----------
    m_types = _read_seed("magnit_data/stores_type.csv", ";")
    if m_types is None:
        m_types = pd.DataFrame({"id": range(1, 7), "type": ["Магнит Семейный", "Магнит Экстра",
                                "Магнит Аптека", "Магнит Косметик", "Магнит Сити", "Магнит Go"]})
    n_m = _scaled(1900)
    m_type_w = np.array([0.18, 0.06, 0.12, 0.2, 0.34, 0.1])[: len(m_types)]
    reg_idx = rng.choice(len(REGIONS), n_m, p=region_w)
    m_stores = pd.DataFrame({
        "id": np.arange(1, n_m + 1),
        "full_address": [
            f"{_magnit_region(REGIONS[i][0], rng)}, г. {REGIONS[i][1]}, ул. {s}, д. {h}"
            for i, s, h in zip(reg_idx, rng.choice(STREETS, n_m), rng.integers(1, 200, n_m))],
        "store_type": rng.choice(m_types["id"].to_numpy(), n_m, p=m_type_w / m_type_w.sum()),
    })
    m_type_name = dict(zip(m_types["id"], m_types["type"]))

    # ---------- терминалы магазинов + привязка к банку-эквайеру ----------
    # retail_terms: (retailer, store_id, is_self_service, legal_entity, amount_mu, popularity)
    retail = []
    for sid, st in zip(x5_stores["id"], x5_stores["store_type"]):
        big = x5_type_name[st] in ("Пятёрочка Макси", "Перекресток")
        n_t = int(rng.integers(4, 11) if big else rng.integers(2, 6))
        le = PEREKRESTOK_LE if "Перекр" in x5_type_name[st] else PYATEROCHKA_LE
        mu = 7.0 if big else 6.4
        store_pop = rng.lognormal(0, 0.5)
        for _ in range(n_t):
            retail.append(("x5", sid, rng.random() < 0.3, le, mu, store_pop))
    for sid, st in zip(m_stores["id"], m_stores["store_type"]):
        tname = m_type_name[st]
        n_t = int(rng.integers(4, 9) if tname in ("Магнит Семейный", "Магнит Экстра") else rng.integers(1, 5))
        mu = {"Магнит Семейный": 6.9, "Магнит Экстра": 7.0, "Магнит Аптека": 6.5,
              "Магнит Косметик": 6.6}.get(tname, 6.2)
        store_pop = rng.lognormal(0, 0.5)
        for _ in range(n_t):
            retail.append(("magnit", sid, rng.random() < 0.25, MAGNIT_LE, mu, store_pop))

    store_bank = {}  # магазин целиком обслуживается одним эквайером
    for r in retail:
        key = (r[0], r[1])
        if key not in store_bank:
            store_bank[key] = "bank1" if rng.random() < 0.55 else "bank2"

    banks = {}
    for bank_no, bank in enumerate(settings.BANKS, start=1):
        brng = np.random.default_rng([SEED, bank_no])
        # малый бизнес у каждого банка свой: (название, домен, терминалов, mu, online)
        small = []
        for i in range(_scaled(120 if bank == "bank1" else 90)):
            kind, mu = SMALL_KINDS[brng.integers(len(SMALL_KINDS))]
            small.append((f"ООО \"{kind} {SMALL_NAMES[brng.integers(len(SMALL_NAMES))]}-{bank_no}{i:04d}\"",
                          f"m{bank_no}{i:04d}.example", int(brng.integers(2, 12)), mu, False))
        # мерчанты: ритейлеры + прочие, у каждого банка свой порядок id
        merchants = ([MAGNIT_LE, PYATEROCHKA_LE, PEREKRESTOK_LE] + [(m[0], m[1]) for m in OTHER_MERCHANTS]
                     + [(m[0], m[1]) for m in small])
        order = brng.permutation(len(merchants))
        merchants = [merchants[i] for i in order]
        m_id = {m[0]: i + 1 for i, m in enumerate(merchants)}
        n_mer = len(merchants)
        merch_df = pd.DataFrame({
            "id": np.arange(1, n_mer + 1),
            "name": [m[0] for m in merchants],
            "inn": _digits(brng, n_mer, 10), "kpp": _digits(brng, n_mer, 9),
            "ogrn": _digits(brng, n_mer, 13), "okpo": _digits(brng, n_mer, 8),
            "address": [f"{REGIONS[i][1]}, ул. {s}, д. {h}" for i, s, h in zip(
                brng.integers(0, 5, n_mer), brng.choice(STREETS, n_mer), brng.integers(1, 99, n_mer))],
            "phone": [f"+7 (495) {a:03d}-{b:02d}-{c:02d}" for a, b, c in zip(
                brng.integers(100, 999, n_mer), brng.integers(10, 99, n_mer), brng.integers(10, 99, n_mer))],
            "email": [f"info@{m[1]}" for m in merchants],
            "created_at": pd.to_datetime("2015-01-01") + pd.to_timedelta(brng.integers(0, 2500, n_mer), "D"),
        })

        # терминалы банка
        t_merchant, t_type, t_mu, t_pop, t_status = [], [], [], [], []
        retail_tid = []  # для каждой записи retail: tid в этом банке или None
        for r in retail:
            if store_bank[(r[0], r[1])] != bank:
                retail_tid.append(None)
                continue
            t_merchant.append(m_id[r[3][0]])
            if bank == "bank1":
                t_type.append(1)                      # offline
            else:
                t_type.append(2 if r[2] else 1)       # self-service / desk
            t_mu.append(r[4] - (0.4 if r[2] else 0.0))
            t_pop.append(r[5] * (0.7 if r[2] else 1.0))
            t_status.append(1)
            retail_tid.append(len(t_merchant))
        for name, _dom, n_t, mu, online in OTHER_MERCHANTS + small:
            n_t = int(_scaled(n_t) * (1.0 if bank == "bank1" else 0.8)) or 1
            for _ in range(n_t):
                t_merchant.append(m_id[name])
                t_type.append((2 if bank == "bank1" else 3) if online else 1)
                t_mu.append(mu)
                t_pop.append(brng.lognormal(0, 0.6) * (25.0 if online else 1.0))
                t_status.append(1)
        n_term = len(t_merchant)
        t_status = np.array(t_status)
        t_status[brng.random(n_term) < 0.03] = 2  # inactive / выведен из эксплуатации
        t_pop = np.array(t_pop)
        t_pop[t_status == 2] *= 0.02
        term_df = pd.DataFrame({
            "id": np.arange(1, n_term + 1),
            ("merchant_id" if bank == "bank1" else "seller_id"): t_merchant,
            "type": t_type,
            "created_at": pd.to_datetime("2019-01-01") + pd.to_timedelta(brng.integers(0, 1800, n_term), "D"),
        })
        if bank == "bank1":
            term_df.insert(3, "status", t_status)

        # клиенты и счета
        n_cl = _scaled(120_000 if bank == "bank1" else 90_000)
        gender = np.where(brng.random(n_cl) < 0.47, "M", "F")
        first = np.where(gender == "M", brng.choice(MALE_NAMES, n_cl), brng.choice(FEMALE_NAMES, n_cl))
        surname = brng.choice(SURNAMES, n_cl)
        surname = np.where(gender == "F", np.char.add(surname, "а"), surname)
        cl_ids = np.arange(1, n_cl + 1)
        clients = pd.DataFrame({
            "id": cl_ids, "name": first, "surname": surname,
            "date_of_birth": (pd.to_datetime("1950-01-01")
                              + pd.to_timedelta(brng.integers(0, 365 * 56, n_cl), "D")).strftime("%Y-%m-%d"),
            "gender": gender,
            "phone_number": 79000000000 + brng.integers(0, 999_999_999, n_cl),
            "email": [f"client{bank_no}_{i}@mail.example" for i in cl_ids],
        })
        acc_per_client = brng.choice([1, 2, 3], n_cl, p=[0.55, 0.33, 0.12])
        acc_client = np.repeat(cl_ids, acc_per_client)
        n_acc = len(acc_client)
        acc_status = brng.choice([1, 2, 3] if bank == "bank1" else [1, 2, 3, 4], n_acc,
                                 p=[0.9, 0.05, 0.05] if bank == "bank1" else [0.88, 0.03, 0.06, 0.03])
        accounts = pd.DataFrame({
            "id": np.arange(1, n_acc + 1), "client_id": acc_client,
            "type": brng.choice([1, 2], n_acc, p=[0.3, 0.7]), "status": acc_status,
            "balance": np.round(brng.lognormal(10, 1.3, n_acc), 2), "currency": "RUB",
        })
        acc_pop = brng.lognormal(0, 1.0, n_acc)
        acc_pop[acc_status != 1] *= 0.01

        dicts = {
            "account_type": pd.DataFrame({"id": [1, 2], "type": ["credit", "debit"]}),
            "account_status": (pd.DataFrame({"id": [1, 2, 3], "status": ["active", "inactive", "closed"]})
                               if bank == "bank1" else
                               pd.DataFrame({"id": [1, 2, 3, 4], "status": ["open", "pending", "closed", "frozen"]})),
            "terminal_type": (pd.DataFrame({"id": [1, 2], "type": ["offline", "online"]}) if bank == "bank1"
                              else pd.DataFrame({"id": [1, 2, 3], "type": ["desk", "self-service", "online"]})),
            "transaction_status": (pd.DataFrame({"id": [1, 2, 3], "status": ["successful", "pending", "rejected"]})
                                   if bank == "bank1" else
                                   pd.DataFrame({"id": [1, 2, 3], "status": ["success", "processing", "failed"]})),
            "currency": pd.DataFrame({"id": ["RUB"], "full_name": ["Russian Ruble"]}),
        }
        if bank == "bank1":
            dicts["terminal_status"] = pd.DataFrame({"id": [1, 2], "status": ["active", "inactive"]})
        tables = {"clients": clients, "accounts": accounts,
                  ("merchants" if bank == "bank1" else "sellers"): merch_df, "terminals": term_df, **dicts}
        banks[bank] = {
            "tables": tables,
            "term_ids": term_df["id"].to_numpy(), "term_p": t_pop / t_pop.sum(), "term_mu": np.array(t_mu),
            "acc_ids": accounts["id"].to_numpy(), "acc_p": acc_pop / acc_pop.sum(),
            "retail_tid": retail_tid,
        }

    # справочники терминалов ритейлеров с TID эквайера
    x5_rows, m_rows = [], []
    for i, r in enumerate(retail):
        bank = store_bank[(r[0], r[1])]
        tid = banks[bank]["retail_tid"][i]
        if r[0] == "x5":
            x5_rows.append((len(x5_rows) + 1, r[1], 2 if r[2] else 1, bank, tid))
        else:
            m_rows.append((len(m_rows) + 1, r[1], "самообслуживание" if r[2] else "касса", bank, tid))
    retail_tables = {
        "x5": {"stores": x5_stores, "store_types": x5_types, "terminal_types": x5_term_types,
               "terminals": pd.DataFrame(x5_rows, columns=["id", "store_id", "terminal_type",
                                                           "acquirer_bank", "acquirer_terminal_id"])},
        "magnit": {"stores": m_stores, "stores_type": m_types,
                   "terminals": pd.DataFrame(m_rows, columns=["id", "address", "terminal_type",
                                                              "acquirer_bank", "acquirer_terminal_id"])},
    }
    return banks, retail_tables


def month_tx_count(bank: str, year: int, month: int, tx_per_month: int) -> int:
    return int(tx_per_month * SEASON[month] * BANK_SHARE[bank])


def first_tx_id(bank, year, month, tx_per_month):
    total = 0
    y, m = EPOCH_YEAR, 1
    while (y, m) < (year, month):
        total += month_tx_count(bank, y, m, tx_per_month)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return total + 1


def generate_transactions(bank: str, year: int, month: int, tx_per_month: int) -> pd.DataFrame:
    banks, _ = build_world()
    b = banks[bank]
    rng = np.random.default_rng([SEED, year * 100 + month, settings.BANKS.index(bank)])
    n = month_tx_count(bank, year, month, tx_per_month)

    days_in_month = calendar.monthrange(year, month)[1]
    day_w = np.array([WEEKDAY_WEIGHTS[date(year, month, d + 1).weekday()] for d in range(days_in_month)])
    day = rng.choice(days_in_month, n, p=day_w / day_w.sum())
    hour = rng.choice(24, n, p=HOUR_WEIGHTS / HOUR_WEIGHTS.sum())
    sec = rng.integers(0, 3600, n)
    ts = (np.datetime64(f"{year:04d}-{month:02d}-01T00:00:00", "s")
          + (day * 86400 + hour * 3600 + sec).astype("timedelta64[s]"))
    ts.sort()

    term_idx = rng.choice(len(b["term_ids"]), n, p=b["term_p"])
    acc = rng.choice(b["acc_ids"], n, p=b["acc_p"])
    mu = b["term_mu"][term_idx] + (0.1 if month == 12 else 0.0)
    amount = np.round(np.clip(np.exp(mu + 0.8 * rng.standard_normal(n)), 10, 500_000), 2)
    status = rng.choice([1, 2, 3], n, p=[0.93, 0.02, 0.05])
    refund = rng.random(n) < 0.01
    amount[refund] *= -1
    status[refund] = 1

    start = first_tx_id(bank, year, month, tx_per_month)
    df = pd.DataFrame({
        "id": np.arange(start, start + n),
        "terminal_id": b["term_ids"][term_idx],
        "account_id": acc,
        "transaction_date": pd.Series(np.datetime_as_string(ts, unit="s")).str.replace("T", " ", regex=False),
        "amount": amount,
        "currency": "RUB",
        "status": status,
    })
    if bank == "bank2":  # Greenplum-выгрузка отдаёт даты в формате dd.mm.yyyy hh:mi:ss
        s = df["transaction_date"]
        df["transaction_date"] = s.str[8:10] + "." + s.str[5:7] + "." + s.str[0:4] + s.str[10:]

    # ---- «грязные» строки ----
    k = max(1, n // 10_000)  # 0.01% каждого вида
    df.loc[rng.choice(n, k, replace=False), "amount"] = np.nan
    df.loc[rng.choice(n, k, replace=False), "terminal_id"] = b["term_ids"].max() + rng.integers(1000, 9000, k)
    df.loc[rng.choice(n, k, replace=False), "transaction_date"] = "0000-00-00 99:99:99"
    dups = df.iloc[rng.choice(n, 2 * k, replace=False)]
    return pd.concat([df, dups]).sort_values("id", kind="stable")


def _write(df: pd.DataFrame, path: Path, source: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    sep = settings.SOURCES[source]["sep"]
    decimal = "," if source == "bank2" else "."
    tmp = path.with_suffix(".tmp")
    df.to_csv(tmp, sep=sep, index=False, float_format="%.2f", decimal=decimal,
              quoting=csv.QUOTE_MINIMAL, date_format="%Y-%m-%d")
    tmp.rename(path)


def batch_dir(landing: Path, source: str, batch: str) -> Path:
    return landing / source / f"batch={batch}"


def extract_batch(batch: str, landing: Path = None, tx_per_month: int = None, force: bool = False) -> dict:
    """Выгружает все источники за месяц batch=YYYY-MM. Возвращает сводку по файлам."""
    landing = Path(landing or settings.LANDING_DIR)
    tx_per_month = tx_per_month or settings.TX_PER_MONTH
    year, month = map(int, batch.split("-"))
    marker = landing / f"_EXTRACTED_{batch}"
    if marker.exists() and not force:
        print(f"[extract] batch {batch} уже выгружен ({marker}), пропуск")
        return json.loads(marker.read_text())

    t0 = time.time()
    banks, retail = build_world()
    files = {}
    for bank in settings.BANKS:
        for name, df in banks[bank]["tables"].items():
            path = batch_dir(landing, bank, batch) / f"{name}.csv"
            _write(df, path, bank)
            files[str(path)] = path.stat().st_size
        tx = generate_transactions(bank, year, month, tx_per_month)
        path = batch_dir(landing, bank, batch) / "transactions.csv"
        _write(tx, path, bank)
        files[str(path)] = path.stat().st_size
    for source, tables in retail.items():
        for name, df in tables.items():
            path = batch_dir(landing, source, batch) / f"{name}.csv"
            _write(df, path, source)
            files[str(path)] = path.stat().st_size

    summary = {"batch": batch, "files": files, "total_bytes": sum(files.values()),
               "seconds": round(time.time() - t0, 1)}
    marker.write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"[extract] batch {batch}: {len(files)} файлов, {summary['total_bytes'] / 2**20:.1f} MiB "
          f"за {summary['seconds']} c")
    return summary


def _months(start: str, count: int):
    y, m = map(int, start.split("-"))
    for _ in range(count):
        yield f"{y:04d}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--month", help="один batch YYYY-MM")
    p.add_argument("--start", default="2024-01", help="первый месяц диапазона")
    p.add_argument("--months", type=int, default=12, help="кол-во месяцев")
    p.add_argument("--landing", default=None)
    p.add_argument("--tx-per-month", type=int, default=None)
    p.add_argument("--force", action="store_true")
    a = p.parse_args()
    for b in ([a.month] if a.month else _months(a.start, a.months)):
        extract_batch(b, a.landing, a.tx_per_month, a.force)
