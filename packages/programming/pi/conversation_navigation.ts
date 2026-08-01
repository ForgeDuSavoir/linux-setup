import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { homedir, tmpdir } from "node:os";
import { isAbsolute, join, relative, resolve, sep } from "node:path";
import { pathToFileURL } from "node:url";
import { spawn } from "node:child_process";

const ENTRY_TYPE = "conversation-navigation-element";
const ALLOWED_SCHEMES = new Set(["file", "http", "https", "mailto"]);
const SHORTCUT = "ctrl+alt+l";

type LinkElement = {
	id: string;
	kind: "link";
	uri: string;
	label: string;
	provenance: "read" | "modified" | "cited";
	timestamp: number;
};

type CodeElement = {
	id: string;
	kind: "code";
	content: string;
	language?: string;
	label: string;
	timestamp: number;
};

type ConversationElement = LinkElement | CodeElement;

type StoredElement = { version: 1; element: ConversationElement };

type TextBlock = { type: string; text?: unknown };
type AssistantMessage = { role?: unknown; content?: unknown; timestamp?: unknown };

function isInside(directory: string, target: string): boolean {
	const path = relative(directory, target);
	return path === "" || (!path.startsWith(`..${sep}`) && path !== ".." && !isAbsolute(path));
}

function sanitizeLabel(value: string, maxLength = 120): string {
	const normalized = value.replace(/[\r\n\t]+/g, " ").replace(/\s+/g, " ").trim();
	return normalized.length > maxLength ? `${normalized.slice(0, maxLength - 1)}…` : normalized;
}

function stableId(value: string): string {
	return createHash("sha256").update(value).digest("hex").slice(0, 16);
}

function textFromAssistant(message: AssistantMessage): string {
	if (!Array.isArray(message.content)) return "";
	return message.content
		.filter((block): block is TextBlock => typeof block === "object" && block !== null)
		.filter((block) => block.type === "text" && typeof block.text === "string")
		.map((block) => block.text as string)
		.join("");
}

function timestampOf(message: AssistantMessage): number {
	return typeof message.timestamp === "number" ? message.timestamp : Date.now();
}

function localPathToUri(candidate: string, cwd: string, requireExisting = true): string | undefined {
	const expanded = candidate.startsWith("~/") ? resolve(homedir(), candidate.slice(2)) : candidate;
	const absolute = resolve(cwd, expanded);
	if (!isInside(resolve(cwd), absolute) || (requireExisting && !existsSync(absolute))) return undefined;
	return pathToFileURL(absolute).href;
}

function createLink(uri: string, label: string, provenance: LinkElement["provenance"], timestamp: number): LinkElement | undefined {
	try {
		const parsed = new URL(uri);
		const scheme = parsed.protocol.slice(0, -1).toLowerCase();
		if (!ALLOWED_SCHEMES.has(scheme)) return undefined;
		return {
			id: stableId(`link:${uri}`),
			kind: "link",
			uri,
			label: sanitizeLabel(label || uri),
			provenance,
			timestamp,
		};
	} catch {
		return undefined;
	}
}

function extractCode(text: string, timestamp: number): CodeElement[] {
	const blocks: CodeElement[] = [];
	const fence = /(^|\n)(`{3,})([^\n]*)\n([\s\S]*?)^\2`*[ \t]*(?=\n|$)/gm;
	let match: RegExpExecArray | null;
	let index = 0;
	while ((match = fence.exec(text)) !== null) {
		const language = match[3].trim().split(/\s+/, 1)[0] || undefined;
		const content = match[4];
		const firstLine = content.split("\n", 1)[0] ?? "";
		const lineCount = content === "" ? 0 : content.split("\n").length - (content.endsWith("\n") ? 1 : 0);
		blocks.push({
			id: stableId(`code:${timestamp}:${index}:${content}`),
			kind: "code",
			content,
			language,
			label: sanitizeLabel(`${language ?? "texte"} · ${lineCount} ligne${lineCount === 1 ? "" : "s"} · ${firstLine || "(vide)"}`),
			timestamp,
		});
		index++;
	}
	return blocks;
}

function extractCitedLinks(text: string, cwd: string, timestamp: number): LinkElement[] {
	const links = new Map<string, LinkElement>();
	const add = (uri: string, label = uri) => {
		const link = createLink(uri, label, "cited", timestamp);
		if (link) links.set(link.uri, link);
	};

	for (const match of text.matchAll(/\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)/g)) add(match[1]);
	for (const match of text.matchAll(/\b(?:https?|mailto):[^\s<>()\[\]{}]+/gi)) {
		add(match[0].replace(/[.,;:!?]+$/, ""));
	}
	for (const match of text.matchAll(/`([^`\n]+)`/g)) {
		const uri = localPathToUri(match[1], cwd);
		if (uri) add(uri, match[1]);
	}
	for (const match of text.matchAll(/\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]/g)) {
		const path = match[1].endsWith(".md") ? match[1] : `${match[1]}.md`;
		const uri = localPathToUri(path, cwd);
		if (uri) add(uri, match[2] ?? match[1]);
	}
	return [...links.values()];
}

function extractUris(value: unknown): string[] {
	if (typeof value === "string") {
		return [...value.matchAll(/\b(?:https?|mailto):[^\s<>()\[\]{}]+/gi)].map((match) => match[0].replace(/[.,;:!?]+$/, ""));
	}
	if (Array.isArray(value)) return value.flatMap(extractUris);
	if (typeof value === "object" && value !== null) return Object.values(value).flatMap(extractUris);
	return [];
}

function toolPathElement(
	path: unknown,
	cwd: string,
	provenance: LinkElement["provenance"],
	timestamp: number,
): LinkElement | undefined {
	if (typeof path !== "string" || path.length === 0) return undefined;
	const uri = localPathToUri(path.replace(/^@/, ""), cwd, false);
	return uri ? createLink(uri, path, provenance, timestamp) : undefined;
}

function latestAssistantTimestamp(ctx: ExtensionContext): number {
	const entries = ctx.sessionManager.getBranch();
	for (let index = entries.length - 1; index >= 0; index--) {
		const entry = entries[index];
		if (entry.type !== "message") continue;
		const message = entry.message as AssistantMessage;
		if (message.role === "assistant") return timestampOf(message);
	}
	return Date.now();
}

export default function (pi: ExtensionAPI) {
	const elements = new Map<string, ConversationElement>();
	let restored = false;

	const add = (element: ConversationElement, ctx?: ExtensionContext, persist = true) => {
		if (element.kind === "link") {
			const existing = [...elements.values()].find(
				(item): item is LinkElement => item.kind === "link" && item.uri === element.uri,
			);
			if (existing && existing.timestamp >= element.timestamp) return;
			if (existing) elements.delete(existing.id);
		}
		if (elements.has(element.id)) return;
		elements.set(element.id, element);
		if (persist && ctx?.sessionManager.isPersisted()) {
			pi.appendEntry(ENTRY_TYPE, { version: 1, element } satisfies StoredElement);
		}
	};

	const restore = (ctx: ExtensionContext) => {
		if (restored) return;
		restored = true;
		const branch = ctx.sessionManager.getBranch();
		const storedElements: ConversationElement[] = [];
		for (const entry of branch) {
			if (entry.type !== "custom" || entry.customType !== ENTRY_TYPE) continue;
			const stored = entry.data as Partial<StoredElement> | undefined;
			if (stored?.version === 1 && stored.element && typeof stored.element === "object") {
				storedElements.push(stored.element as ConversationElement);
			}
		}
		for (const entry of branch) {
			if (entry.type !== "message") continue;
			const message = entry.message as AssistantMessage;
			if (message.role !== "assistant") continue;
			const timestamp = timestampOf(message);
			const text = textFromAssistant(message);
			for (const element of extractCitedLinks(text, ctx.cwd, timestamp)) add(element, undefined, false);
			for (const element of extractCode(text, timestamp)) add(element, undefined, false);

			if (!Array.isArray(message.content)) continue;
			for (const block of message.content as Array<{ type?: unknown; name?: unknown; arguments?: unknown }>) {
				if (block.type !== "toolCall" || typeof block.name !== "string") continue;
				const args = block.arguments as { path?: unknown } | undefined;
				const provenance = block.name === "read" ? "read" : block.name === "edit" || block.name === "write" ? "modified" : undefined;
				if (!provenance) continue;
				const element = toolPathElement(args?.path, ctx.cwd, provenance, timestamp);
				if (element) add(element, undefined, false);
			}
		}
		for (const element of storedElements) {
			if (!elements.has(element.id)) add(element, undefined, false);
		}
	};

	pi.on("session_start", (_event, ctx) => {
		restored = false;
		elements.clear();
		restore(ctx);
	});

	pi.on("tool_call", (event, ctx) => {
		const timestamp = latestAssistantTimestamp(ctx);
		const provenance = event.toolName === "read" ? "read" : event.toolName === "edit" || event.toolName === "write" ? "modified" : undefined;
		if (provenance) {
			const path = (event.input as { path?: unknown }).path;
			const element = toolPathElement(path, ctx.cwd, provenance, timestamp);
			if (element) add(element, ctx);
		}
		for (const uri of extractUris(event.input)) {
			const element = createLink(uri, uri, "cited", timestamp);
			if (element) add(element, ctx);
		}
	});

	pi.on("message_end", (event, ctx) => {
		const message = event.message as AssistantMessage;
		if (message.role !== "assistant") return;
		const timestamp = timestampOf(message);
		const text = textFromAssistant(message);
		for (const element of extractCitedLinks(text, ctx.cwd, timestamp)) add(element, ctx);
		for (const element of extractCode(text, timestamp)) add(element, ctx);
	});

	pi.registerShortcut(SHORTCUT, {
		description: "Ouvrir un lien de conversation ou copier un extrait de code",
		handler: async (ctx) => {
			if (ctx.mode !== "tui") return;
			restore(ctx);
			if (elements.size === 0) {
				ctx.ui.notify("Aucun lien ou extrait de code dans cette conversation.", "info");
				return;
			}

			const directory = await mkdtemp(join(tmpdir(), "pi-conversation-navigation-"));
			const manifest = join(directory, "manifest.json");
			await writeFile(manifest, JSON.stringify({ version: 1, elements: [...elements.values()] }), { mode: 0o600 });
			const child = spawn("pi-conversation-select", [manifest], {
				cwd: ctx.cwd,
				detached: true,
				stdio: "ignore",
			});
			child.on("error", async (error) => {
				await rm(directory, { recursive: true, force: true });
				ctx.ui.notify(`Impossible d’ouvrir Rofi : ${error.message}`, "error");
			});
			child.unref();
		},
	});
}
