"""Rebind the FIXTURE scan to the dataset id the running server computes (P2 run-1 lesson).

The server includes repository calendar files in its dataset identity, so the id computed by
setup_fixture_env.py can differ. The UI correctly marks such candles STALE. This script reads the
server's id through the API and updates only the fixture scan row in the temporary database.
Usage: python3 rebind_dataset.py <env_dir> <cfg_json_path>
"""
import http.cookiejar
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

env = Path(sys.argv[1])
cfg_path = Path(sys.argv[2])
cfg = json.loads(cfg_path.read_text())
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
base = "http://127.0.0.1:8899"
headers = {"X-GTF-Request": "1", "Origin": base}
opener.open(urllib.request.Request(base + "/api/v1/session/bootstrap", data=b"", method="POST", headers=headers))
datasets = json.loads(opener.open(urllib.request.Request(base + "/api/v1/datasets", headers=headers)).read())["data"]["datasets"]
server_id = datasets[0]["dataset_id"]
conn = sqlite3.connect(env / "platform.sqlite")
row = conn.execute("SELECT envelope_json FROM scan_result WHERE scan_key = ?", (cfg["scan_key"],)).fetchone()
envelope = json.loads(row[0])
envelope["dataset_id"] = server_id
conn.execute("UPDATE scan_result SET dataset_id = ?, envelope_json = ? WHERE scan_key = ?", (server_id, json.dumps(envelope), cfg["scan_key"]))
conn.commit()
conn.close()
cfg["setup_dataset_id"] = cfg["dataset_id"]
cfg["dataset_id"] = server_id
cfg_path.write_text(json.dumps(cfg))
print(json.dumps({"setup_dataset_id": cfg["setup_dataset_id"], "server_dataset_id": server_id}))
