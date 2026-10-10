from decimal import Decimal

from pipeline import settings
from pipeline.load.hdfs_loader import read_json

MAX_REJECT_SHARE = 0.005      # не более 0.5% отбракованных транзакций
MIN_STORE_LINK_SHARE = 0.5    # хотя бы половина терминалов банков должна связаться с магазином


class DataQualityError(Exception):
    pass


def _meta(batch, name):
    return read_json(f"{settings.META_ROOT}/batch={batch}/{name}")


def check_core(batch: str) -> dict:
    manifest = _meta(batch, "load_manifest.json")
    m = _meta(batch, "core_metrics.json")
    errors = []

    loaded = {f["source"]: f["rows"] for f in manifest["files"] if f["table"] == "transactions"}
    for bank in settings.BANKS:
        if loaded.get(bank) != m["raw_rows"].get(bank):
            errors.append(f"{bank}: в raw загружено {loaded.get(bank)} строк, Spark прочитал {m['raw_rows'].get(bank)}")

    raw_total = sum(m["raw_rows"].values())
    dup_total = sum(m["duplicates"].values())
    rej_total = sum(m["rejected"].values())
    if m["fact_rows"] + dup_total + rej_total != raw_total:
        errors.append(f"баланс строк не сходится: fact {m['fact_rows']} + dup {dup_total} + "
                      f"rejected {rej_total} != raw {raw_total}")
    reject_share = rej_total / raw_total if raw_total else 1
    if reject_share > MAX_REJECT_SHARE:
        errors.append(f"доля брака {reject_share:.4%} > {MAX_REJECT_SHARE:.2%}: {m['rejected']}")
    if m["fact_rows"] == 0:
        errors.append("факт пуст")
    link_share = m["terminals_linked_to_store"] / m["dims"]["dim_terminal"]
    if link_share < MIN_STORE_LINK_SHARE:
        errors.append(f"с магазинами связано лишь {link_share:.1%} терминалов")

    report = {"batch": batch, "raw_rows": raw_total, "fact_rows": m["fact_rows"], "duplicates": dup_total,
              "rejected": m["rejected"], "reject_share": round(reject_share, 6),
              "store_link_share": round(link_share, 4), "errors": errors}
    print("[dq core]", report)
    if errors:
        raise DataQualityError("; ".join(errors))
    return report


def check_marts(batch: str) -> dict:
    m = _meta(batch, "marts_metrics.json")
    errors = []
    if m["fact_purchases"] != m["mart_purchases"]:
        errors.append(f"кол-во покупок: факт {m['fact_purchases']} != витрина {m['mart_purchases']}")
    if Decimal(m["fact_turnover"]) != Decimal(m["mart_turnover"]):
        errors.append(f"оборот: факт {m['fact_turnover']} != витрина {m['mart_turnover']}")
    errors += [f"витрина {k} пуста" for k, v in m["rows"].items() if v == 0]
    print("[dq marts]", m, errors)
    if errors:
        raise DataQualityError("; ".join(errors))
    return m
