import { useEffect, useState } from "react";

import { api, NotificationStatus } from "../api";

export default function SettingsPage() {
  const [status, setStatus] = useState<NotificationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    api.notificationStatus().then(setStatus).catch((e) => setError(e.message));
  }, []);

  const sendTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      await api.sendTestNotification();
      setTestResult("Sent - check your phone.");
    } catch (e) {
      setTestResult(`Failed: ${(e as Error).message}`);
    } finally {
      setTesting(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <h1>Settings</h1>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="settings-layout">
        <section className="panel">
          <h2>
            Phone notifications{" "}
            {status && (
              <span className={`status-dot ${status.enabled ? "on" : "off"}`}>
                {status.enabled ? "enabled" : "disabled"}
              </span>
            )}
          </h2>
          {status?.enabled ? (
            <>
              <p>
                Reminders are pushed through{" "}
                <a href={status.url} target="_blank" rel="noreferrer">
                  ntfy
                </a>{" "}
                to the topic below. You get one ping when a task comes within its
                reminder window and another (high priority) on the due date, between
                8:00 and 21:00 ({status.timezone}).
              </p>
              <dl className="kv">
                <dt>Server</dt>
                <dd>{status.url}</dd>
                <dt>Topic</dt>
                <dd>
                  <code>{status.topic}</code>
                </dd>
              </dl>
              <h3>Get them on your iPhone</h3>
              <ol className="setup-steps">
                <li>Install the free “ntfy” app from the App Store.</li>
                <li>
                  Tap + and subscribe to the topic <code>{status.topic}</code>
                  {status.url !== "https://ntfy.sh" && (
                    <> on server <code>{status.url}</code></>
                  )}
                  .
                </li>
                <li>Hit the test button below - you should get a ping.</li>
              </ol>
              <button className="btn primary" onClick={sendTest} disabled={testing}>
                {testing ? "Sending…" : "Send test notification"}
              </button>
              {testResult && <p className="test-result">{testResult}</p>}
              <p className="muted">
                The topic name works like a password - anyone who knows it can see
                these reminders, so keep it random and private.
              </p>
            </>
          ) : (
            <p>
              Not configured. Set <code>NTFY_TOPIC</code> (and optionally{" "}
              <code>NTFY_URL</code>) on the backend to enable phone reminders, then
              subscribe to that topic in the ntfy app.
            </p>
          )}
        </section>

        <section className="panel">
          <h2>Add Tend to your home screen</h2>
          <p>
            Open this site in Safari on your iPhone, tap the share button, then
            “Add to Home Screen”. Tend launches full-screen like a native app.
          </p>
        </section>
      </div>
    </>
  );
}
