import type { ExtensionAPI, ExtensionContext, Theme } from "@earendil-works/pi-coding-agent";
import { Key, matchesKey, truncateToWidth, type Component, type TUI } from "@earendil-works/pi-tui";
import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { isAbsolute, relative, resolve, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
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

export type ConversationElement = LinkElement | CodeElement;
export type ConversationCategory = "code" | "link" | "file";

// Transient types used by the TUI. They deliberately remain separate from
// ConversationElement so the persisted version 1 format does not change.
export type ConversationDisplayElement =
	| Readonly<LinkElement & { number: number; category: Extract<ConversationCategory, "file" | "link"> }>
	| Readonly<CodeElement & { number: number; category: Extract<ConversationCategory, "code"> }>;

export type ConversationGroup = Readonly<{
	timestamp: number;
	elements: readonly ConversationDisplayElement[];
}>;

type ElementLineRange = Readonly<{ start: number; end: number }>;

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

function displayCategory(element: ConversationElement): ConversationDisplayElement["category"] {
	if (element.kind === "code") return "code";
	return new URL(element.uri).protocol === "file:" ? "file" : "link";
}

export function groupConversationElements(elements: Iterable<ConversationElement>): readonly ConversationGroup[] {
	const grouped = new Map<number, ConversationElement[]>();
	for (const element of elements) {
		const group = grouped.get(element.timestamp);
		if (group) group.push(element);
		else grouped.set(element.timestamp, [element]);
	}

	const sortedGroups = [...grouped.entries()].sort(([leftTimestamp], [rightTimestamp]) => rightTimestamp - leftTimestamp);
	let number = 1;
	return Object.freeze(
		sortedGroups.map(([timestamp, groupElements]) =>
			Object.freeze({
				timestamp,
				elements: Object.freeze(
					groupElements.map((element) =>
						Object.freeze({
							...element,
							number: number++,
							category: displayCategory(element),
						}) as ConversationDisplayElement,
					),
				),
			}),
		),
	);
}

export function listSelectableIds(groups: readonly ConversationGroup[]): readonly string[] {
	return Object.freeze(groups.flatMap((group) => group.elements.map((element) => element.id)));
}

export function selectableIdForNumber(
	groups: readonly ConversationGroup[],
	numberQuery: string,
): string | undefined {
	if (!/^[1-9]\d*$/u.test(numberQuery)) return undefined;
	const number = Number(numberQuery);
	if (!Number.isSafeInteger(number)) return undefined;
	for (const group of groups) {
		const element = group.elements.find((candidate) => candidate.number === number);
		if (element) return element.id;
	}
	return undefined;
}

export function filterConversationGroupsByType(
	groups: readonly ConversationGroup[],
	activeCategories: ReadonlySet<ConversationCategory>,
): readonly ConversationGroup[] {
	if (activeCategories.size === 0) return groups;
	return Object.freeze(
		groups.flatMap((group) => {
			const elements = group.elements.filter((element) => activeCategories.has(element.category));
			return elements.length > 0
				? [Object.freeze({ timestamp: group.timestamp, elements: Object.freeze(elements) })]
				: [];
		}),
	);
}

function printableSearchInput(data: string): string | undefined {
	if (data === "" || data.startsWith("\u001b") || /[\u0000-\u001f\u007f]/u.test(data)) return undefined;
	return data;
}

function formatMessageTimestamp(timestamp: number): string {
	const date = new Date(timestamp);
	if (!Number.isFinite(date.getTime())) return "message inconnu";
	return date.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }).replace(",", " —");
}

function fileDisplayParts(element: Extract<ConversationDisplayElement, { kind: "link" }>): { name: string; path: string } {
	try {
		const path = fileURLToPath(element.uri);
		const name = path.split(sep).filter(Boolean).at(-1) ?? element.label;
		return { name, path };
	} catch {
		return { name: element.label, path: element.uri };
	}
}

function linkDisplayLabel(element: Extract<ConversationDisplayElement, { kind: "link" }>): string {
	if (element.label && element.label !== element.uri) return element.label;
	try {
		const parsed = new URL(element.uri);
		if (parsed.protocol === "mailto:") return decodeURIComponent(parsed.pathname);
		const path = parsed.pathname === "/" ? "" : decodeURI(parsed.pathname);
		return `${parsed.host}${path}${parsed.search}${parsed.hash}` || element.uri;
	} catch {
		return element.label || element.uri;
	}
}

export function conversationSearchCorpus(element: ConversationDisplayElement): string {
	if (element.kind === "code") return `${element.language ?? "texte"}\n${element.content}`;
	if (element.category === "file") {
		const file = fileDisplayParts(element);
		return `${file.name}\n${file.path}`;
	}
	return `${linkDisplayLabel(element)}\n${element.uri}`;
}

export function filterConversationGroupsByText(
	groups: readonly ConversationGroup[],
	query: string,
): readonly ConversationGroup[] {
	if (query === "") return groups;
	const normalizedQuery = query.toLocaleLowerCase();
	return Object.freeze(
		groups.flatMap((group) => {
			const elements = group.elements.filter((element) =>
				conversationSearchCorpus(element).toLocaleLowerCase().includes(normalizedQuery),
			);
			return elements.length > 0
				? [Object.freeze({ timestamp: group.timestamp, elements: Object.freeze(elements) })]
				: [];
		}),
	);
}

export function filterConversationGroupsByTypeAndText(
	groups: readonly ConversationGroup[],
	activeCategories: ReadonlySet<ConversationCategory>,
	textQuery: string,
): readonly ConversationGroup[] {
	return filterConversationGroupsByText(filterConversationGroupsByType(groups, activeCategories), textQuery);
}

export function filterConversationGroupsView(
	groups: readonly ConversationGroup[],
	activeCategories: ReadonlySet<ConversationCategory>,
	textQuery: string,
): readonly ConversationGroup[] {
	return filterConversationGroupsByTypeAndText(groups, activeCategories, textQuery);
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
		if (/[\s`"'<>]/.test(uri)) return undefined;
		const parsed = new URL(uri);
		const scheme = parsed.protocol.slice(0, -1).toLowerCase();
		if (!ALLOWED_SCHEMES.has(scheme)) return undefined;
		if ((scheme === "http" || scheme === "https") && parsed.hostname === "") return undefined;
		if (scheme === "mailto" && (!parsed.pathname.includes("@") || parsed.pathname.startsWith("@") || parsed.pathname.endsWith("@"))) {
			return undefined;
		}
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
	for (const match of text.matchAll(/\b(?:https?|mailto):[^\s`"'<>()[\]{}]+/gi)) {
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
		return [...value.matchAll(/\b(?:https?|mailto):[^\s`"'<>()[\]{}]+/gi)].map((match) => match[0].replace(/[.,;:!?]+$/, ""));
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

export class ConversationNavigator implements Component {
	private readonly tui: TUI;
	private readonly theme: Theme;
	private readonly done: (result: string | null) => void;
	private readonly allGroups: readonly ConversationGroup[];
	private groups: readonly ConversationGroup[];
	private selectableIds: readonly string[];
	private selectedIndex: number;
	private viewportTop = 0;
	private cachedWidth: number | undefined;
	private cachedHeight: number | undefined;
	private cachedLines: string[] | undefined;
	private readonly elementLineRanges = new Map<string, ElementLineRange>();
	private readonly typeFilters: Record<ConversationCategory, boolean> = {
		code: false,
		link: false,
		file: false,
	};
	private numberFilterOpen = false;
	private numberQuery = "";
	private numberTargetUnavailable = false;
	private searchMode = false;
	private textQuery = "";
	private completed = false;

	constructor(
		tui: TUI,
		theme: Theme,
		groups: readonly ConversationGroup[],
		done: (result: string | null) => void,
	) {
		this.tui = tui;
		this.theme = theme;
		this.done = done;
		this.allGroups = Object.freeze([...groups]);
		this.groups = this.allGroups;
		this.selectableIds = listSelectableIds(this.groups);
		this.selectedIndex = this.selectableIds.length > 0 ? 0 : -1;
	}

	get selectedId(): string | undefined {
		return this.selectedIndex >= 0 ? this.selectableIds[this.selectedIndex] : undefined;
	}

	get isNumberFilterOpen(): boolean {
		return this.numberFilterOpen;
	}

	get numberFilterQuery(): string {
		return this.numberQuery;
	}

	get isNumberTargetUnavailable(): boolean {
		return this.numberTargetUnavailable;
	}

	get isSearchMode(): boolean {
		return this.searchMode;
	}

	get searchQuery(): string {
		return this.textQuery;
	}

	isTypeFilterActive(category: ConversationCategory): boolean {
		return this.typeFilters[category];
	}

	lineRangeOf(id: string): ElementLineRange | undefined {
		return this.elementLineRanges.get(id);
	}

	handleInput(data: string): void {
		if (matchesKey(data, Key.ctrlAlt("l"))) {
			this.complete(null);
			return;
		}
		if (matchesKey(data, Key.escape)) {
			if (this.searchMode) {
				this.searchMode = false;
				this.invalidate();
			} else {
				this.complete(null);
			}
			return;
		}
		if (matchesKey(data, Key.enter)) {
			if (this.selectedId) this.complete(this.selectedId);
			return;
		}
		if (!this.searchMode && matchesKey(data, "i")) {
			this.searchMode = true;
			this.clearNumberSelection();
			this.applyFilters(true);
			return;
		}
		if (this.searchMode) {
			if (matchesKey(data, Key.backspace)) {
				this.textQuery = this.textQuery.slice(0, -1);
				this.clearNumberSelection();
				this.applyFilters(true);
				return;
			}
			const text = printableSearchInput(data);
			if (text !== undefined) {
				this.textQuery += text;
				this.clearNumberSelection();
				this.applyFilters(true);
				return;
			}
		}
		const digit = "0123456789".split("").find((candidate) => matchesKey(data, candidate));
		if (digit !== undefined) {
			this.numberFilterOpen = true;
			this.numberQuery += digit;
			this.applyNumberSelection();
			return;
		}
		if (this.numberFilterOpen && matchesKey(data, Key.backspace)) {
			this.numberQuery = this.numberQuery.slice(0, -1);
			this.applyNumberSelection();
			return;
		}
		const typeShortcut: ReadonlyArray<readonly [string, ConversationCategory]> = [
			["c", "code"],
			["u", "link"],
			["f", "file"],
		];
		const typeFilter = typeShortcut.find(([key]) => matchesKey(data, key))?.[1];
		if (typeFilter) {
			this.typeFilters[typeFilter] = !this.typeFilters[typeFilter];
			this.clearNumberSelection();
			this.applyFilters(true);
			return;
		}
		const moveUp = matchesKey(data, Key.up) || matchesKey(data, "k");
		const moveDown = matchesKey(data, Key.down) || matchesKey(data, "j");
		const moveLeft = matchesKey(data, Key.left) || matchesKey(data, "h");
		const moveRight = matchesKey(data, Key.right) || matchesKey(data, "l");
		if (!moveUp && !moveDown && !moveLeft && !moveRight) return;

		const numberSelectionCleared = this.clearNumberSelection();
		if (this.selectableIds.length === 0) {
			if (numberSelectionCleared) this.invalidate();
			return;
		}
		let nextIndex = this.selectedIndex;
		if (moveUp) nextIndex = Math.max(0, this.selectedIndex - 1);
		else if (moveDown) nextIndex = Math.min(this.selectableIds.length - 1, this.selectedIndex + 1);
		else if (moveLeft) nextIndex = this.firstElementIndexInRelativeGroup(-1);
		else if (moveRight) nextIndex = this.firstElementIndexInRelativeGroup(1);

		if (nextIndex !== this.selectedIndex || numberSelectionCleared) {
			this.selectedIndex = nextIndex;
			this.invalidate();
		}
	}

	private complete(result: string | null): void {
		if (this.completed) return;
		this.completed = true;
		this.done(result);
	}

	private clearNumberSelection(): boolean {
		const changed = this.numberFilterOpen || this.numberQuery !== "" || this.numberTargetUnavailable;
		this.numberFilterOpen = false;
		this.numberQuery = "";
		this.numberTargetUnavailable = false;
		return changed;
	}

	private applyNumberSelection(): void {
		this.numberTargetUnavailable = false;
		if (this.numberQuery === "") {
			this.invalidate();
			return;
		}
		const targetId = selectableIdForNumber(this.groups, this.numberQuery);
		if (!targetId) {
			this.numberTargetUnavailable = true;
			this.invalidate();
			return;
		}
		const targetIndex = this.selectableIds.indexOf(targetId);
		if (targetIndex >= 0) this.selectedIndex = targetIndex;
		this.invalidate();
	}

	private applyFilters(resetSelection = false): void {
		const selectedId = resetSelection ? undefined : this.selectedId;
		const activeCategories = new Set(
			(Object.entries(this.typeFilters) as Array<[ConversationCategory, boolean]>)
				.filter(([, active]) => active)
				.map(([category]) => category),
		);
		this.groups = filterConversationGroupsView(this.allGroups, activeCategories, this.textQuery);
		this.selectableIds = listSelectableIds(this.groups);
		const preservedIndex = selectedId ? this.selectableIds.indexOf(selectedId) : -1;
		this.selectedIndex = preservedIndex >= 0 ? preservedIndex : this.selectableIds.length > 0 ? 0 : -1;
		this.invalidate();
	}

	private firstElementIndexInRelativeGroup(offset: -1 | 1): number {
		const selectedId = this.selectedId;
		if (!selectedId) return this.selectedIndex;
		const groupIndex = this.groups.findIndex((group) => group.elements.some((element) => element.id === selectedId));
		const targetGroup = this.groups[groupIndex + offset];
		const targetId = targetGroup?.elements[0]?.id;
		if (!targetId) return this.selectedIndex;
		const targetIndex = this.selectableIds.indexOf(targetId);
		return targetIndex >= 0 ? targetIndex : this.selectedIndex;
	}

	render(width: number): string[] {
		if (width <= 0) return [];
		const hasBorder = width >= 3;
		const contentWidth = hasBorder ? width - 2 : width;
		const contentHeight = this.viewportHeight(hasBorder);
		if (this.cachedWidth === width && this.cachedHeight === contentHeight && this.cachedLines) return this.cachedLines;

		const typeFilterIndicator = (key: string, label: string, category: ConversationCategory) => {
			const indicator = `${this.typeFilters[category] ? "●" : "○"} ${key} ${label}`;
			return this.typeFilters[category] ? this.theme.fg("accent", this.theme.bold(indicator)) : this.theme.fg("dim", indicator);
		};
		const controlLines = [
			`${this.theme.bold("Filtres :")} ${typeFilterIndicator("C", "code", "code")}  ${typeFilterIndicator("U", "liens", "link")}  ${typeFilterIndicator("F", "fichiers", "file")}`,
		];
		if (this.numberFilterOpen) {
			const unavailable = this.numberTargetUnavailable ? this.theme.fg("warning", " (indisponible)") : "";
			controlLines.push(
				`${this.theme.bold("Numéro :")} ${this.theme.fg("accent", this.numberQuery)}${this.theme.fg("accent", "▏")}${unavailable}`,
			);
		}
		if (this.searchMode || this.textQuery !== "") {
			controlLines.push(
				`${this.theme.bold("Recherche :")} ${this.theme.fg("accent", this.textQuery)}${this.searchMode ? this.theme.fg("accent", "▏") : ""}`,
			);
		}
		const listViewportHeight = Math.max(0, contentHeight - controlLines.length);
		const lines: string[] = [];
		this.elementLineRanges.clear();
		for (const [groupIndex, group] of this.groups.entries()) {
			if (groupIndex > 0) lines.push("");
			const label = formatMessageTimestamp(group.timestamp);
			lines.push(this.theme.fg("dim", `── ${label} ──`));

			for (const element of group.elements) {
				const start = lines.length;
				if (element.kind === "code") {
					const number = this.theme.fg("accent", `${element.number}.`);
					lines.push(`  ${number} ${this.theme.bold(element.language ?? "texte")}`);
					const contentLines = element.content.split("\n");
					if (contentLines.at(-1) === "") contentLines.pop();
					if (contentLines.length === 0) {
						lines.push(this.theme.fg("dim", "     (vide)"));
					} else {
						for (const contentLine of contentLines) lines.push(`     ${contentLine || " "}`);
					}
				} else if (element.category === "file") {
					const file = fileDisplayParts(element);
					const number = this.theme.fg("accent", `${element.number}.`);
					lines.push(`  ${number} ${this.theme.bold(file.name)}`);
					lines.push(this.theme.fg("dim", `     ${file.path}`));
				} else {
					const number = this.theme.fg("accent", `${element.number}.`);
					lines.push(`  ${number} ${this.theme.bold(linkDisplayLabel(element))}`);
					lines.push(this.theme.fg("dim", `     ${element.uri}`));
				}
				this.elementLineRanges.set(element.id, Object.freeze({ start, end: lines.length }));
			}
		}
		if (this.groups.length === 0) {
			lines.push(this.theme.fg("dim", "Aucune entrée ne correspond aux filtres actifs."));
		}

		void this.selectedIndex;
		void this.viewportTop;
		void this.done;
		const fittedLines = (lines.length > 0 ? lines : [""]).map((line) => truncateToWidth(line, contentWidth, "…"));
		const selectedRange = this.selectedId ? this.elementLineRanges.get(this.selectedId) : undefined;
		if (selectedRange && typeof this.theme.bg === "function") {
			for (let index = selectedRange.start; index < selectedRange.end; index++) {
				const line = fittedLines[index];
				if (line !== undefined) fittedLines[index] = this.theme.bg("selectedBg", truncateToWidth(line, contentWidth, "", true));
			}
		}
		this.updateViewport(fittedLines.length, listViewportHeight);
		const visibleLines = fittedLines.slice(this.viewportTop, this.viewportTop + listViewportHeight);
		const contentLines = [...controlLines, ...visibleLines];
		this.cachedWidth = width;
		this.cachedHeight = contentHeight;
		if (hasBorder) {
			const horizontal = "─".repeat(contentWidth);
			this.cachedLines = [
				this.theme.fg("border", `╭${horizontal}╮`),
				...contentLines.map(
					(line) =>
						`${this.theme.fg("border", "│")}${truncateToWidth(line, contentWidth, "", true)}${this.theme.fg("border", "│")}`,
				),
				this.theme.fg("border", `╰${horizontal}╯`),
			];
		} else {
			this.cachedLines = contentLines.map((line) => truncateToWidth(line, contentWidth, "…"));
		}
		return this.cachedLines;
	}

	private viewportHeight(hasBorder: boolean): number {
		const rows = this.tui.terminal?.rows;
		if (typeof rows !== "number" || !Number.isFinite(rows)) return Number.MAX_SAFE_INTEGER;
		const maximumHeight = Math.max(1, Math.floor(rows * 0.8));
		return Math.max(1, maximumHeight - (hasBorder ? 2 : 0));
	}

	private updateViewport(lineCount: number, viewportHeight: number): void {
		const range = this.selectedId ? this.elementLineRanges.get(this.selectedId) : undefined;
		if (range && range.end - range.start > viewportHeight) {
			this.viewportTop = range.start;
		} else if (range) {
			if (range.start < this.viewportTop) this.viewportTop = range.start;
			else if (range.end > this.viewportTop + viewportHeight) this.viewportTop = range.end - viewportHeight;
		}
		const maximumTop = Math.max(0, lineCount - viewportHeight);
		this.viewportTop = Math.max(0, Math.min(this.viewportTop, maximumTop));
	}

	invalidate(): void {
		this.cachedWidth = undefined;
		this.cachedHeight = undefined;
		this.cachedLines = undefined;
		this.elementLineRanges.clear();
		this.tui.requestRender();
	}
}

export async function selectConversationElement(
	ctx: ExtensionContext,
	elements: Iterable<ConversationElement>,
): Promise<string | null> {
	const groups = groupConversationElements(elements);
	if (groups.length === 0) {
		ctx.ui.notify("Aucun lien ou extrait de code dans cette conversation.", "info");
		return null;
	}
	return ctx.ui.custom<string | null>(
		(tui, theme, _keybindings, done) => new ConversationNavigator(tui, theme, groups, done),
		{
			overlay: true,
			overlayOptions: { anchor: "center", width: "80%", maxHeight: "80%", margin: 1 },
		},
	);
}

export function openConversationLink(uri: string, spawnCommand: typeof spawn = spawn): Promise<void> {
	return new Promise((resolveOpen, rejectOpen) => {
		const child = spawnCommand("xdg-open", [uri], {
			detached: true,
			stdio: "ignore",
			shell: false,
		});
		child.once("error", rejectOpen);
		child.once("spawn", () => {
			child.unref();
			resolveOpen();
		});
	});
}

export function copyConversationCode(content: string, spawnCommand: typeof spawn = spawn): Promise<void> {
	return new Promise((resolveCopy, rejectCopy) => {
		let completed = false;
		const resolveOnce = () => {
			if (completed) return;
			completed = true;
			resolveCopy();
		};
		const rejectOnce = (error: Error) => {
			if (completed) return;
			completed = true;
			rejectCopy(error);
		};

		const child = spawnCommand("wl-copy", [], {
			stdio: ["pipe", "ignore", "ignore"],
			shell: false,
		});
		child.once("error", rejectOnce);
		child.once("close", (code, signal) => {
			if (code === 0) resolveOnce();
			else rejectOnce(new Error(`wl-copy s’est terminé avec ${code === null ? `le signal ${signal ?? "inconnu"}` : `le code ${code}`}.`));
		});

		if (!child.stdin) {
			rejectOnce(new Error("Impossible d’écrire le contenu sur l’entrée standard de wl-copy."));
			return;
		}
		child.stdin.once("error", rejectOnce);
		child.stdin.end(Buffer.from(content, "utf8"));
	});
}

export async function executeConversationElement(
	ctx: ExtensionContext,
	element: ConversationElement,
	actions: {
		openLink: (uri: string) => Promise<void>;
		copyCode: (content: string) => Promise<void>;
	} = { openLink: openConversationLink, copyCode: copyConversationCode },
): Promise<boolean> {
	try {
		if (element.kind === "link") await actions.openLink(element.uri);
		else await actions.copyCode(element.content);
		return true;
	} catch (error) {
		const detail = error instanceof Error ? error.message : String(error);
		const message = element.kind === "link" ? `Impossible d’ouvrir le lien : ${detail}` : `Impossible de copier l’extrait : ${detail}`;
		ctx.ui.notify(message, "error");
		return false;
	}
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
			if (element.kind === "link") {
				const validated = createLink(element.uri, element.label, element.provenance, element.timestamp);
				if (validated && !elements.has(validated.id)) add(validated, undefined, false);
			} else if (!elements.has(element.id)) {
				add(element, undefined, false);
			}
		}
	};

	const rebuildFromActiveBranch = (ctx: ExtensionContext) => {
		restored = false;
		elements.clear();
		restore(ctx);
	};

	pi.on("session_start", (_event, ctx) => {
		rebuildFromActiveBranch(ctx);
	});

	pi.on("session_tree", (_event, ctx) => {
		rebuildFromActiveBranch(ctx);
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
			const selectedId = await selectConversationElement(ctx, elements.values());
			if (!selectedId) return;

			const selectedElement = elements.get(selectedId);
			if (!selectedElement) {
				ctx.ui.notify("L’élément sélectionné n’existe plus dans cette conversation.", "error");
				return;
			}
			await executeConversationElement(ctx, selectedElement);
		},
	});
}
