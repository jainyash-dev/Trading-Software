"""Session, host, origin, and OpenAPI checks for the local web API."""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PLATFORM = Path(__file__).resolve().parents[1]
ROOT = PLATFORM.parent
sys.path.insert(0, str(PLATFORM))

from fastapi.testclient import TestClient  # noqa: E402

from gtf_platform.app import create_app  # noqa: E402
from gtf_platform.config import Settings, load_settings  # noqa: E402
from gtf_platform.db import connect  # noqa: E402
from gtf_platform.errors import ApiError, reject_mixed_fixture  # noqa: E402
from gtf_platform.instance import AlreadyRunning, InstanceLock  # noqa: E402
from gtf_platform.jobs import interrupt_stale  # noqa: E402

MARKER = {
    "X-GTF-Request": "1",
    "Origin": "http://127.0.0.1:8765",
    "Sec-Fetch-Site": "same-origin",
}


def settings(tmp: Path, **overrides) -> Settings:
    values = dict(
        bind_host="127.0.0.1",
        bind_port=8765,
        advertised_port=8765,
        public_origins=(),
        platform_db=tmp / "platform.sqlite",
        research_db=None,
        cookie_secure=False,
        data_dir=tmp,
        testing=True,
    )
    values.update(overrides)
    return Settings(**values)


def client(tmp: Path, **overrides) -> TestClient:
    application = create_app(settings(tmp, **overrides))
    return TestClient(application, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000))


class Security(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.client = client(self.tmp)

    def tearDown(self) -> None:
        self.client.close()
        self._tmp.cleanup()

    def test_bootstrap_sets_an_httponly_cookie_and_hides_it_from_json(self) -> None:
        response = self.client.post("/api/v1/session/bootstrap", headers=MARKER)
        self.assertEqual(response.status_code, 200)
        body = response.text
        cookie = response.headers["set-cookie"]
        token = cookie.split(";", 1)[0].split("=", 1)[1]
        self.assertNotIn(token, body)
        lowered = cookie.lower()
        self.assertIn("httponly", lowered)
        self.assertIn("samesite=strict", lowered)
        self.assertNotIn("secure", lowered)
        self.assertNotIn("token=", body)
        self.assertEqual(response.json()["data"]["auth"], "cookie")
        self.assertFalse(response.json()["meta"]["fixture"])

    def test_health_requires_a_session_and_then_reports_unavailable_scan(self) -> None:
        denied = self.client.get("/api/v1/health", headers=MARKER)
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(denied.json()["error"]["code"], "UNAUTHENTICATED")
        self.client.post("/api/v1/session/bootstrap", headers=MARKER)
        health = self.client.get("/api/v1/health", headers=MARKER)
        self.assertEqual(health.status_code, 200)
        data = health.json()["data"]
        self.assertEqual(data["last_scan"], None)
        self.assertEqual(data["last_scan_state"], "UNAVAILABLE")
        self.assertEqual(data["outcome"], "WARNING")
        self.assertNotEqual(data["outcome"], "OK")

    def test_cross_site_evil_origin_and_missing_marker_are_refused(self) -> None:
        cross = dict(MARKER)
        cross["Sec-Fetch-Site"] = "cross-site"
        self.assertEqual(self.client.post("/api/v1/session/bootstrap", headers=cross).status_code, 403)
        evil = dict(MARKER)
        evil["Origin"] = "http://evil.example"
        refused = self.client.post("/api/v1/session/bootstrap", headers=evil)
        self.assertEqual(refused.status_code, 403)
        self.assertEqual(refused.json()["error"]["code"], "ORIGIN_REJECTED")
        bare = {"Origin": MARKER["Origin"], "Sec-Fetch-Site": "same-origin"}
        missing = self.client.post("/api/v1/session/bootstrap", headers=bare)
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(missing.json()["error"]["code"], "CSRF_REJECTED")

    def test_wrong_host_is_refused(self) -> None:
        headers = dict(MARKER)
        headers["Host"] = "evil.example"
        response = self.client.post("/api/v1/session/bootstrap", headers=headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "HOST_REJECTED")

    def test_logout_ends_the_session(self) -> None:
        self.client.post("/api/v1/session/bootstrap", headers=MARKER)
        self.assertEqual(self.client.get("/api/v1/session", headers=MARKER).status_code, 200)
        logged_out = self.client.post("/api/v1/session/logout", headers=MARKER)
        self.assertEqual(logged_out.status_code, 200)
        self.assertFalse(logged_out.json()["data"]["authenticated"])
        self.assertEqual(self.client.get("/api/v1/health", headers=MARKER).status_code, 401)

    def test_forged_cookie_and_non_cookie_identity_are_rejected(self) -> None:
        forged = client(self.tmp)
        forged.cookies.set("gtf_session", "not-a-real-token")
        denied = forged.get("/api/v1/health", headers=MARKER)
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(denied.json()["error"]["code"], "UNAUTHENTICATED")
        self.assertNotIn("not-a-real-token", denied.text)
        forged.close()

        bare = client(self.tmp)
        query = bare.get("/api/v1/health", headers=MARKER, params={"gtf_session": "query-token"})
        self.assertEqual(query.status_code, 401)
        bearer_headers = dict(MARKER)
        bearer_headers["Authorization"] = "Bearer body-token"
        bearer = bare.get("/api/v1/health", headers=bearer_headers)
        self.assertEqual(bearer.status_code, 401)
        body = bare.post(
            "/api/v1/session/bootstrap",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"token": "body-token", "session": "body-session"},
        )
        self.assertEqual(body.status_code, 200, body.text)
        self.assertNotIn("body-token", body.text)
        self.assertNotIn("body-session", body.text)
        bare.close()

    def test_rebootstrap_revokes_prior_sessions(self) -> None:
        first = self.client.post("/api/v1/session/bootstrap", headers=MARKER)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["data"]["session_recovery"], "REBOOTSTRAP")
        old = self.client.cookies.get("gtf_session")
        self.assertEqual(self.client.app.state.sessions.active_count(), 1)
        second = self.client.post("/api/v1/session/bootstrap", headers=MARKER)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self.client.app.state.sessions.active_count(), 1)
        self.assertTrue(self.client.app.state.sessions.valid(self.client.cookies.get("gtf_session")))
        self.assertFalse(self.client.app.state.sessions.valid(old))

    def test_internal_error_body_does_not_leak_exception_text(self) -> None:
        quiet = TestClient(
            self.client.app,
            base_url="http://127.0.0.1:8765",
            client=("127.0.0.1", 50000),
            raise_server_exceptions=False,
        )
        quiet.cookies.update(self.client.cookies)
        quiet.post("/api/v1/session/bootstrap", headers=MARKER)

        def boom():
            raise RuntimeError("secret-stack-trace-value")

        quiet.app.add_api_route("/api/v1/__p1_boom", boom, methods=["GET"])
        failed = quiet.get("/api/v1/__p1_boom", headers=MARKER)
        self.assertEqual(failed.status_code, 500, failed.text)
        payload = failed.json()
        self.assertEqual(payload["error"]["code"], "INTERNAL")
        self.assertNotIn("secret-stack-trace-value", failed.text)
        self.assertIn("error_id", payload["error"]["details"])
        quiet.close()

    def test_meta_does_not_claim_orders_or_implemented_fills(self) -> None:
        self.client.post("/api/v1/session/bootstrap", headers=MARKER)
        meta = self.client.get("/api/v1/meta", headers=MARKER).json()["data"]
        self.assertFalse(meta["orders_placed"])
        self.assertIn("fills", meta["routes_not_implemented"])
        self.assertIn("assistant", meta["routes_not_implemented"])
        self.assertIn("paper", meta["routes_not_implemented"])
        self.assertNotIn("journal", meta["routes_not_implemented"])
        self.assertEqual(meta["eligibility"], "research-pipeline")

    def test_fixture_payload_cannot_cite_a_dataset(self) -> None:
        with self.assertRaises(ApiError):
            reject_mixed_fixture({"meta": {"fixture": True}, "data": {"dataset_id": "abc"}})
        reject_mixed_fixture({"meta": {"fixture": True}, "data": {}})
        response = self.client.post(
            "/api/v1/session/bootstrap",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"meta": {"fixture": True}, "data": {"dataset_id": "real-dataset"}},
        )
        self.assertEqual(response.status_code, 422)

    def test_openapi_uses_the_cookie_and_omits_unimplemented_writes(self) -> None:
        schema = self.client.app.openapi()
        paths = set(schema["paths"])
        self.assertIn("/api/v1/health", paths)
        self.assertIn("/api/v1/session/bootstrap", paths)
        self.assertNotIn("/api/v1/fills", paths)
        self.assertIn("/api/v1/journal", paths)
        scheme = schema["components"]["securitySchemes"]["cookieSession"]
        self.assertEqual(scheme["in"], "cookie")
        self.assertEqual(scheme["name"], "gtf_session")
        blob = json.dumps(schema)
        self.assertNotIn('"scheme": "bearer"', blob.lower())
        self.assertNotIn('"type": "http"', blob.lower())
        self.assertNotIn("0.0.0.0", blob)
        for path, methods in schema["paths"].items():
            for method, operation in methods.items():
                if method not in {"get", "post", "put", "patch", "delete"}:
                    continue
                for parameter in operation.get("parameters") or []:
                    if parameter.get("in") == "query":
                        self.assertNotIn(
                            parameter.get("name"),
                            {"token", "access_token", "gtf_session", "session"},
                            path,
                        )
        checked = PLATFORM / "gtf_platform" / "openapi.json"
        if checked.is_file():
            self.assertEqual(json.loads(checked.read_text(encoding="utf-8")), schema)


class InstanceAndJobs(unittest.TestCase):
    def test_second_lock_reports_the_port_only(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            first = InstanceLock(directory)
            first.acquire()
            first.write_port(8765)
            (directory / "not-a-session.txt").write_text("secret-value", encoding="utf-8")
            second = InstanceLock(directory)
            with self.assertRaises(AlreadyRunning) as caught:
                second.acquire()
            self.assertEqual(caught.exception.port, 8765)
            self.assertNotIn("secret-value", str(caught.exception))
            first.release()

    def test_stale_running_job_becomes_interrupted(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            connection = connect(Path(raw) / "platform.sqlite")
            now = datetime(2026, 11, 9, tzinfo=timezone.utc)
            old = (now - timedelta(minutes=5)).isoformat()
            fresh = now.isoformat()
            connection.execute(
                "INSERT INTO job (job_id, kind, state, idempotency_key, heartbeat, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("old", "SCAN", "RUNNING", None, old, old),
            )
            connection.execute(
                "INSERT INTO job (job_id, kind, state, idempotency_key, heartbeat, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("fresh", "SCAN", "RUNNING", None, fresh, fresh),
            )
            connection.execute(
                "INSERT INTO job (job_id, kind, state, idempotency_key, heartbeat, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("done", "SCAN", "SUCCEEDED_COMPLETE", None, old, old),
            )
            connection.commit()
            changed = interrupt_stale(connection, now, timedelta(seconds=30))
            self.assertEqual(changed, 1)
            states = {row["job_id"]: row["state"] for row in connection.execute("SELECT job_id, state FROM job")}
            self.assertEqual(states["old"], "INTERRUPTED")
            self.assertEqual(states["fresh"], "RUNNING")
            self.assertEqual(states["done"], "SUCCEEDED_COMPLETE")

    def test_bind_host_must_be_loopback(self) -> None:
        import os

        previous = os.environ.get("GTF_BIND_HOST")
        os.environ["GTF_BIND_HOST"] = "0.0.0.0"
        try:
            with self.assertRaises(ValueError):
                load_settings()
        finally:
            if previous is None:
                os.environ.pop("GTF_BIND_HOST", None)
            else:
                os.environ["GTF_BIND_HOST"] = previous

    def test_research_imports_stay_inside_the_adapter(self) -> None:
        forbidden = (
            "derive_status",
            "eligible_after_overlay",
            "journal_event",
            "journal_add",
            "place_order",
            "kiteconnect",
            "nse.research.qualification",
            "nse.research.scanner",
            "import scanner",
        )
        allowed_modules = {
            "pipeline",
            "inputs",
            "marketdata",
            "universe",
            "instruments",
            "corporate_actions",
            "run_manifest",
            "models",
            "risk",
            "explain",
            "deps",
            "store",
            "backtest",
            "scanner",
            "reports",
        }
        journal_calls = ("journal_event", "journal_add")
        for path in (PLATFORM / "gtf_platform").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(PLATFORM / "gtf_platform").as_posix()
            for word in forbidden:
                if word in journal_calls and rel == "integration/desk.py":
                    continue
                self.assertNotIn(word, text, rel)
            if "nse.research" in text or "nse.zone" in text:
                self.assertTrue(rel.startswith("integration/"), rel)
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("from nse.research import "):
                    imported = stripped.split(" import ", 1)[1].split("#", 1)[0]
                    names = [part.strip().split(" as ")[0] for part in imported.split(",")]
                    for name in names:
                        self.assertIn(name, allowed_modules, "%s: %s" % (rel, stripped))
                elif stripped.startswith("from nse.research."):
                    module = stripped.split()[1].split(".", 2)[2].split(" import")[0].split(".")[0]
                    self.assertIn(module, allowed_modules, "%s: %s" % (rel, stripped))
                elif stripped.startswith("import nse") or stripped.startswith("from nse"):
                    self.fail("%s: %s" % (rel, stripped))

    def test_root_project_dependencies_stay_empty(self) -> None:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", text)


if __name__ == "__main__":
    unittest.main()
