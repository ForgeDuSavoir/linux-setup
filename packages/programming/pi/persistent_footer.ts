import { keyHint, rawKeyHint } from "@earendil-works/pi-coding-agent";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { truncateToWidth, visibleWidth, wrapTextWithAnsi } from "@earendil-works/pi-tui";
import { basename, isAbsolute, relative, resolve, sep } from "node:path";

interface UsageTotals {
	input: number;
	output: number;
	cacheRead: number;
	cacheWrite: number;
	cost: number;
	latestCacheHitRate?: number;
}

function formatTokens(count: number): string {
	if (count < 1_000) return `${count}`;
	if (count < 10_000) return `${(count / 1_000).toFixed(1)}k`;
	if (count < 1_000_000) return `${Math.round(count / 1_000)}k`;
	if (count < 10_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
	return `${Math.round(count / 1_000_000)}M`;
}

function formatCwd(cwd: string): string {
	const home = process.env.HOME ?? process.env.USERPROFILE;
	if (!home) return cwd;

	const relativeToHome = relative(resolve(home), resolve(cwd));
	const isInsideHome =
		relativeToHome === "" ||
		(relativeToHome !== ".." && !relativeToHome.startsWith(`..${sep}`) && !isAbsolute(relativeToHome));
	return isInsideHome ? (relativeToHome === "" ? "~" : `~${sep}${relativeToHome}`) : cwd;
}

function getUsageTotals(ctx: ExtensionContext): UsageTotals {
	const totals: UsageTotals = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, cost: 0 };

	for (const entry of ctx.sessionManager.getEntries()) {
		const usage =
			entry.type === "message"
				? entry.message.usage
				: entry.type === "branch_summary" || entry.type === "compaction"
					? entry.usage
					: undefined;
		if (!usage) continue;

		totals.input += usage.input;
		totals.output += usage.output;
		totals.cacheRead += usage.cacheRead;
		totals.cacheWrite += usage.cacheWrite;
		totals.cost += usage.cost.total;

		if (entry.type === "message" && entry.message.role === "assistant") {
			const promptTokens = usage.input + usage.cacheRead + usage.cacheWrite;
			totals.latestCacheHitRate = promptTokens > 0 ? (usage.cacheRead / promptTokens) * 100 : undefined;
		}
	}

	return totals;
}

export default function (pi: ExtensionAPI) {
	let helpVisible = false;

	const setFooter = (ctx: ExtensionContext) => {
		if (ctx.mode !== "tui") return;

		const directory = basename(ctx.cwd) || ctx.cwd;
		const session = pi.getSessionName() ?? "sans nom";

		ctx.ui.setFooter((tui, theme, footerData) => {
			const unsubscribe = footerData.onBranchChange(() => tui.requestRender());

			return {
				dispose: unsubscribe,
				invalidate() {},
				render(width: number): string[] {
					const status = [
						theme.fg("accent", "Dossier :"),
						` ${directory}`,
						theme.fg("dim", " │ "),
						theme.fg("accent", "Session :"),
						` ${session}`,
						theme.fg("dim", " │ "),
						theme.fg("accent", "Ctrl+O"),
						theme.fg("muted", helpVisible ? " masquer l’aide" : " afficher l’aide"),
					].join("");

					let location = formatCwd(ctx.cwd);
					const branch = footerData.getGitBranch();
					if (branch) location += ` (${branch})`;

					const totals = getUsageTotals(ctx);
					const stats: string[] = [];
					if (totals.input) stats.push(`↑${formatTokens(totals.input)}`);
					if (totals.output) stats.push(`↓${formatTokens(totals.output)}`);
					if (totals.cacheRead) stats.push(`R${formatTokens(totals.cacheRead)}`);
					if (totals.cacheWrite) stats.push(`W${formatTokens(totals.cacheWrite)}`);
					if (totals.latestCacheHitRate !== undefined) stats.push(`CH${totals.latestCacheHitRate.toFixed(1)}%`);
					if (totals.cost) stats.push(`$${totals.cost.toFixed(3)}`);

					const contextUsage = ctx.getContextUsage();
					const contextWindow = contextUsage?.contextWindow ?? ctx.model?.contextWindow ?? 0;
					const context = contextUsage?.percent === null || contextUsage === undefined
						? `?/${formatTokens(contextWindow)}`
						: `${contextUsage.percent.toFixed(1)}%/${formatTokens(contextWindow)}`;
					stats.push(context);

					const model = ctx.model;
					const thinking = model?.reasoning
						? ` • ${pi.getThinkingLevel() === "off" ? "thinking off" : pi.getThinkingLevel()}`
						: "";
					const modelName = model ? `${model.id}${thinking}` : "no-model";
					const provider = footerData.getAvailableProviderCount() > 1 && model ? `(${model.provider}) ` : "";
					const left = theme.fg("dim", stats.join(" "));
					const right = theme.fg("dim", `${provider}${modelName}`);
					const spacing = " ".repeat(Math.max(2, width - visibleWidth(left) - visibleWidth(right)));

					const lines = [
						truncateToWidth(status, width),
						truncateToWidth(theme.fg("dim", location), width),
						truncateToWidth(left + spacing + right, width),
					];

					const extensionStatuses = [...footerData.getExtensionStatuses().values()]
						.map((text) => text.replace(/[\r\n\t]/g, " ").replace(/ +/g, " ").trim())
						.filter(Boolean);
					if (extensionStatuses.length > 0) {
						lines.push(truncateToWidth(extensionStatuses.join(" "), width));
					}

					if (!helpVisible) return lines;

					const help = [
						keyHint("app.interrupt", "interrompre"),
						keyHint("app.clear", "effacer"),
						rawKeyHint("Ctrl+C deux fois", "quitter"),
						keyHint("app.exit", "quitter si l’éditeur est vide"),
						keyHint("app.suspend", "suspendre"),
						keyHint("tui.editor.deleteToLineEnd", "supprimer jusqu’à la fin"),
						keyHint("app.thinking.cycle", "changer le niveau de réflexion"),
						rawKeyHint("Ctrl+P / Ctrl+Shift+P", "changer de modèle"),
						keyHint("app.model.select", "choisir un modèle"),
						rawKeyHint("Ctrl+Alt+L", "ouvrir un lien ou copier un extrait"),
						keyHint("app.tools.expand", "développer les sorties d’outils"),
						keyHint("app.thinking.toggle", "développer la réflexion"),
						keyHint("app.editor.external", "ouvrir l’éditeur externe"),
						rawKeyHint("/", "commandes"),
						rawKeyHint("!", "commande Bash"),
						rawKeyHint("!!", "commande Bash hors contexte"),
						keyHint("app.message.followUp", "ajouter un suivi"),
						keyHint("app.message.dequeue", "modifier les messages en attente"),
						keyHint("app.clipboard.pasteImage", "coller une image"),
						rawKeyHint("déposer un fichier", "joindre un fichier"),
					].join("\n");

					return [...lines, theme.fg("accent", "Aide"), ...wrapTextWithAnsi(help, width)];
				},
			};
		});
	};

	pi.registerShortcut("ctrl+o", {
		description: "Afficher ou masquer l’aide dans le pied de page",
		handler: (ctx) => {
			helpVisible = !helpVisible;
			setFooter(ctx);
		},
	});

	pi.on("session_start", (_event, ctx) => setFooter(ctx));
	pi.on("session_info_changed", (_event, ctx) => setFooter(ctx));
	pi.on("model_select", (_event, ctx) => setFooter(ctx));
	pi.on("thinking_level_select", (_event, ctx) => setFooter(ctx));
	pi.on("session_shutdown", (_event, ctx) => ctx.ui.setFooter(undefined));
}
