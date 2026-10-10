import argparse
import gzip
import hashlib
import json
import tempfile
import time
from pathlib import Path

from hdfs import InsecureClient

from pipeline import settings
from pipeline.extract.generate import batch_dir

CHUNK = 4 * 2**20
SPOOL_MAX = 256 * 2**20
HTTP_TIMEOUT = (10, 300)  # (connect, read) секунд


def hdfs_client() -> InsecureClient:
    return InsecureClient(settings.WEBHDFS_URL, user=settings.HDFS_USER, timeout=HTTP_TIMEOUT)


def upload_gzip(client: InsecureClient, local: Path, hdfs_path: str, level: int = 6) -> dict:
    tmp = hdfs_path + "._COPYING_"
    md5, raw_bytes, lines = hashlib.md5(), 0, 0
    with open(local, "rb") as src, tempfile.SpooledTemporaryFile(max_size=SPOOL_MAX) as buf:
        # mtime=0 — одинаковый вход даёт побайтно одинаковый .gz
        with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=level, mtime=0) as gz:
            while chunk := src.read(CHUNK):
                md5.update(chunk)
                raw_bytes += len(chunk)
                lines += chunk.count(b"\n")
                gz.write(chunk)
        buf.seek(0)
        client.write(tmp, data=buf, overwrite=True)
    client.rename(tmp, hdfs_path)
    gz_bytes = client.status(hdfs_path)["length"]
    return {"raw_bytes": raw_bytes, "gz_bytes": gz_bytes, "rows": max(lines - 1, 0),
            "md5": md5.hexdigest(), "ratio": round(raw_bytes / gz_bytes, 2) if gz_bytes else None}


def load_batch(batch: str, landing: str = None) -> dict:
    landing = Path(landing or settings.LANDING_DIR)
    client = hdfs_client()
    t0 = time.time()
    files = []
    for source in settings.SOURCES:
        src_dir = batch_dir(landing, source, batch)
        csvs = sorted(src_dir.glob("*.csv"))
        if not csvs:
            raise FileNotFoundError(f"нет файлов для загрузки в {src_dir}")
        for csv_path in csvs:
            table = csv_path.stem
            part_dir = f"{settings.RAW_ROOT}/{source}/{table}/batch={batch}"
            client.delete(part_dir, recursive=True)
            client.makedirs(part_dir)
            stats = upload_gzip(client, csv_path, f"{part_dir}/{table}.csv.gz")
            files.append({"source": source, "table": table, "hdfs_path": f"{part_dir}/{table}.csv.gz", **stats})
            print(f"[load] {source}.{table}: {stats['raw_bytes'] / 2**20:.1f} MiB -> "
                  f"{stats['gz_bytes'] / 2**20:.1f} MiB (x{stats['ratio']}), {stats['rows']} строк")

    raw_total = sum(f["raw_bytes"] for f in files)
    gz_total = sum(f["gz_bytes"] for f in files)
    manifest = {"batch": batch, "codec": "gzip", "files": files, "raw_bytes": raw_total,
                "gz_bytes": gz_total, "ratio": round(raw_total / gz_total, 2),
                "seconds": round(time.time() - t0, 1)}
    client.write(f"{settings.META_ROOT}/batch={batch}/load_manifest.json",
                 json.dumps(manifest, ensure_ascii=False, indent=1), overwrite=True, encoding="utf-8")
    print(f"[load] batch {batch}: {raw_total / 2**20:.1f} MiB -> {gz_total / 2**20:.1f} MiB "
          f"(x{manifest['ratio']}) за {manifest['seconds']} c")
    return {k: v for k, v in manifest.items() if k != "files"}


def read_json(path: str):
    with hdfs_client().read(path, encoding="utf-8") as r:
        return json.load(r)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--batch", required=True)
    p.add_argument("--landing", default=None)
    a = p.parse_args()
    load_batch(a.batch, a.landing)
