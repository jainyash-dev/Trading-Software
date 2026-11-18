import { useEffect, useState } from "react";
import { Button, Page, Panel, ProvenanceBadge, Segmented, SelectInput, StatusBadge, Switch, TextInput, type Provenance } from "../../design/components";
import { presentStatus } from "../../design/status";
import { useAppState } from "../../state/store";

const CANDIDATE = ["ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING", "MANUAL_REVIEW", "DATA_INSUFFICIENT", "REJECTED", "BLOCKED"];
const GATES = ["PASS", "FAIL", "MANUAL", "DATA_INSUFFICIENT", "BLOCKED", "NOT_EVALUATED"];
const ZONES = ["FRESH", "TESTED", "INVALIDATED", "UNKNOWN"];
const PROVENANCE: Provenance[] = ["CERTIFIED", "PROVISIONAL", "EXPLORATORY", "FIXTURE", "STALE", "UNAVAILABLE", "NOT_IMPLEMENTED", "BLOCKED", "PARTIAL", "LIVE"];

/** P10-10 Settings. Owner inputs only; no secret, credential or broker field is collected. */
export function SettingsPage() {
  const app = useAppState();
  const [capital, setCapital] = useState("");
  const [pct, setPct] = useState("");
  const [stage, setStage] = useState("");
  const [scheduler, setScheduler] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [backupMessage, setBackupMessage] = useState<string | null>(null);
  const [backupDir, setBackupDir] = useState("");
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const connected = app.connection === "connected";
  useEffect(() => {
    if (app.connection !== "connected") return;
    setLoadState("loading");
    void app.request<Record<string, unknown>>("/api/v1/settings").then((result) => {
      // P10 review I-5: never offer Save over values that were not read; it would write nulls.
      if (!result.ok) {
        setLoadState("error");
        setLoadError(`${result.error.code}: ${result.error.message}`);
        return;
      }
      setLoadState("ready");
      setLoadError(null);
      const data = result.envelope.data;
      setCapital(data.capital == null ? "" : String(data.capital));
      setPct(data.rpt_pct == null ? "" : String(data.rpt_pct));
      setStage(data.risk_stage == null ? "" : String(data.risk_stage));
      setScheduler(data.scheduler_enabled === true);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app.connection]);

  return (
    <Page eyebrow="System" title="Settings" description="Capital and risk are owner inputs. The scheduler does not download files. No broker password is collected.">
      <div className="grid items-start gap-4 xl:grid-cols-2">
        <Panel title="Appearance" subtitle="Display preferences are stored in this browser only.">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-[12.5px]">Theme</span>
            <Segmented
              label="Theme"
              value={app.theme}
              options={[
                { value: "dark", label: "Dark" },
                { value: "light", label: "Light" },
              ]}
              onChange={app.setTheme}
            />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-[12.5px]">Navigation</span>
            <Switch label="Collapsed sidebar" checked={app.collapsed} onChange={app.setCollapsed} />
          </div>
        </Panel>

        <Panel title="Risk inputs" subtitle="Used by the risk module for quantity. Saving does not change a gate.">
          <div className="grid grid-cols-2 gap-2">
            <TextInput label="Capital" inputMode="decimal" value={capital} onChange={(event) => setCapital(event.target.value)} />
            <TextInput label="Risk percent" inputMode="decimal" value={pct} onChange={(event) => setPct(event.target.value)} />
            <SelectInput label="Risk stage" value={stage} onChange={(event) => setStage(event.target.value)}>
              <option value="">Not set (risk stays manual)</option>
              <option value="LEARNING">LEARNING</option>
              <option value="INTERMEDIATE">INTERMEDIATE</option>
              <option value="PROFESSIONAL">PROFESSIONAL</option>
            </SelectInput>
          </div>
          <label className="flex items-center gap-2 text-[12.5px]">
            <input type="checkbox" className="accent-[var(--gtf-accent)]" checked={scheduler} onChange={(event) => setScheduler(event.target.checked)} />
            Post-close scan when the file is already on disk
          </label>
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="primary"
              disabled={!connected || loadState !== "ready"}
              onClick={() =>
                void app
                  .request("/api/v1/settings", {
                    method: "PATCH",
                    body: {
                      capital: capital === "" ? null : Number(capital),
                      rpt_pct: pct === "" ? null : Number(pct),
                      risk_stage: stage === "" ? null : stage,
                      scheduler_enabled: scheduler,
                    },
                  })
                  .then((result) => setMessage(result.ok ? "Saved. A gate was not changed." : result.error.message))
              }
            >
              Save
            </Button>
            {message ? <p className="text-[12px]">{message}</p> : null}
          </div>
          {loadState === "error" ? (
            <p className="text-[12px] text-[var(--gtf-fail)]" role="status">
              Settings could not be read ({loadError}). Save is disabled so stored values are not overwritten.
            </p>
          ) : null}
        </Panel>

        <Panel title="Backup and restore check" subtitle="Consistent SQLite copies into a new directory. Live databases are never replaced from this screen.">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              disabled={!connected}
              onClick={() =>
                void app.request<{ directory?: string; files?: string[]; live_files_unchanged?: boolean }>("/api/v1/backup", { method: "POST", body: {} }).then((result) => {
                  if (!result.ok) {
                    setBackupMessage(result.error.message);
                    return;
                  }
                  const data = result.envelope.data;
                  setBackupDir(data.directory || "");
                  setBackupMessage(`Backup copied to ${data.directory}. Files: ${(data.files || []).join(", ") || "none"}. Live databases were not replaced.`);
                })
              }
            >
              Create backup
            </Button>
            <Button
              type="button"
              disabled={!backupDir}
              onClick={() =>
                void app.request<{ restored_to?: string }>("/api/v1/restore-check", { method: "POST", body: { directory: backupDir } }).then((result) => {
                  if (!result.ok) setBackupMessage(result.error.message);
                  else setBackupMessage(`Restore check wrote a copy to ${result.envelope.data.restored_to}. Live databases were not replaced.`);
                })
              }
            >
              Check restore in a new directory
            </Button>
          </div>
          {backupMessage ? <p className="break-all text-[12px]">{backupMessage}</p> : null}
          <p className="text-[11.5px] text-muted">The historical bhavcopy archive is not included in this backup.</p>
        </Panel>

        <Panel title="Not configurable here">
          <ul className="space-y-1 text-[12.5px] text-ink-2">
            <li>Broker credentials: not collected. No broker integration exists (D10, D17).</li>
            <li>Language-model provider: none enabled (AI-002, owner-deferred).</li>
            <li>Owner caps: 10 trades per IST month and 10 open positions are fixed rules, not settings.</li>
            <li>Data directory and fetch policy: set at launch, not from the browser.</li>
          </ul>
        </Panel>
      </div>

      <Panel title="Status vocabulary" subtitle="Specimens of every status label used in the application. Colour is never the only signal: each label carries text and a glyph.">
        <div className="space-y-3">
          <Specimens title="Candidate status" codes={CANDIDATE} />
          <Specimens title="Gate outcome" codes={GATES} />
          <Specimens title="Zone freshness" codes={ZONES} />
          <div>
            <p className="eyebrow mb-1.5">Data provenance</p>
            <div className="flex flex-wrap gap-1.5">
              {PROVENANCE.map((kind) => (
                <ProvenanceBadge key={kind} kind={kind} />
              ))}
            </div>
          </div>
          <div>
            <p className="eyebrow mb-1.5">Unknown code (never a pass)</p>
            <span title={presentStatus("NOT_A_REAL_STATUS").label}>
              <StatusBadge code="NOT_A_REAL_STATUS" />
            </span>
          </div>
        </div>
      </Panel>
    </Page>
  );
}

function Specimens(props: { title: string; codes: string[] }) {
  return (
    <div>
      <p className="eyebrow mb-1.5">{props.title}</p>
      <div className="flex flex-wrap gap-1.5">
        {props.codes.map((code) => (
          <StatusBadge key={code} code={code} />
        ))}
      </div>
    </div>
  );
}
