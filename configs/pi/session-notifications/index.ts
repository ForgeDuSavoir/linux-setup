/** Desktop completion through Agora's existing server/policy, never terminal OSC. */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { homedir } from "node:os";
import { join } from "node:path";

type Outcome = "completed" | "aborted" | "error";
type Activity = { context: string; outcome: Outcome };
const validContext = (value: string) => value === "global" || value === "neutral"
  || /^session:[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(value);

export default function (pi: ExtensionAPI) {
  const helper = join(homedir(), ".local/bin/agora-notify");
  let pending: Activity | undefined;

  // No process/timer in the factory: resource discovery must be side-effect free.
  pi.on("agent_start", async () => {
    if (pending) return; // Retries/queued continuations belong to the same activity.
    const activity: Activity = { context: "global", outcome: "completed" };
    pending = activity;
    try {
      const result = await pi.exec(helper, ["capture"], { timeout: 2000 });
      const value = result.stdout.trim();
      if (pending === activity && result.code === 0 && !result.killed && validContext(value)) {
        activity.context = value;
      }
    } catch {
      // Missing/unconfirmed/invalid context is global, never a completion-time lookup.
    }
  });

  pi.on("agent_before_settle", async (event) => {
    if (pending) pending.outcome = event.outcome;
    // Observation only: never append entries or request continuation.
  });

  pi.on("agent_settled", async (event) => {
    const activity = pending;
    pending = undefined; // Clear before awaiting: no duplicate send/replay on failure.
    if (!activity || event.aborted || activity.outcome === "aborted") return;
    const error = activity.outcome === "error";
    try {
      const result = await pi.exec(helper, [
        "send", "--context", activity.context, "-a", "Pi", "-t", "5000",
        error ? "Pi — traitement en erreur" : "Pi — tâche terminée",
        error ? "Le traitement s’est arrêté sur une erreur. Consulte le terminal."
          : "Pi a terminé son traitement et attend une nouvelle instruction.",
      ], { timeout: 3000 });
      if (result.code !== 0 || result.killed) {
        console.error("Pi completion notification unavailable; no retry.");
      }
    } catch {
      console.error("Pi completion notification unavailable; no retry.");
    }
  });

  pi.on("session_shutdown", async () => {
    pending = undefined; // Reload, fork/resume/new or exit must not notify/replay old work.
  });
}
