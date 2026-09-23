import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { Writable } from "node:stream";
import test from "node:test";
import { visibleWidth } from "@earendil-works/pi-tui";
import conversationNavigationExtension, {
	ConversationNavigator,
	copyConversationCode,
	executeConversationElement,
	selectableIdForNumber,
	filterConversationGroupsByText,
	filterConversationGroupsByType,
	filterConversationGroupsView,
	groupConversationElements,
	listSelectableIds,
	openConversationLink,
	selectConversationElement,
	type ConversationCategory,
	type ConversationElement,
} from "./conversation_navigation.ts";

function code(id: string, timestamp: number, content = `contenu ${id}`, language = "text"): ConversationElement {
	return {
		id,
		kind: "code",
		content,
		language,
		label: id,
		timestamp,
	};
}

function link(id: string, timestamp: number, uri: string, label = id): ConversationElement {
	return {
		id,
		kind: "link",
		uri,
		label,
		provenance: "cited",
		timestamp,
	};
}

test("regroupe par timestamp et trie les groupes du plus récent au plus ancien", () => {
	const groups = groupConversationElements([
		code("ancien-a", 100),
		link("recent", 300, "https://example.com/recent"),
		code("ancien-b", 100),
		link("intermediaire", 200, "https://example.com/intermediaire"),
	]);

	assert.deepEqual(
		groups.map((group) => group.timestamp),
		[300, 200, 100],
	);
	assert.deepEqual(
		groups.map((group) => group.elements.map((element) => element.id)),
		[["recent"], ["intermediaire"], ["ancien-a", "ancien-b"]],
	);
});

test("attribue une numérotation continue dans l’ordre final d’affichage", () => {
	const groups = groupConversationElements([
		code("ancien-a", 100),
		code("recent", 300),
		code("ancien-b", 100),
	]);
	const elements = groups.flatMap((group) => group.elements);

	assert.deepEqual(
		elements.map((element) => element.id),
		["recent", "ancien-a", "ancien-b"],
	);
	assert.deepEqual(
		elements.map((element) => element.number),
		[1, 2, 3],
	);
	assert.deepEqual(listSelectableIds(groups), ["recent", "ancien-a", "ancien-b"]);
});

test("retrouve un numéro exact sans transformer les groupes", () => {
	const groups = groupConversationElements([
		...Array.from({ length: 4 }, (_, index) => code(`recent-${index + 1}`, 300)),
		...Array.from({ length: 4 }, (_, index) => code(`intermediaire-${index + 1}`, 200)),
		...Array.from({ length: 5 }, (_, index) => code(`ancien-${index + 1}`, 100)),
	]);
	const snapshot = groups.map((group) => ({
		timestamp: group.timestamp,
		elements: group.elements.map((element) => [element.id, element.number]),
	}));

	assert.equal(selectableIdForNumber(groups, "1"), "recent-1");
	assert.equal(selectableIdForNumber(groups, "13"), "ancien-5");
	assert.equal(selectableIdForNumber(groups, "2"), "recent-2");
	assert.equal(selectableIdForNumber(groups, "0"), undefined);
	assert.equal(selectableIdForNumber(groups, "14"), undefined);
	assert.deepEqual(
		groups.map((group) => ({
			timestamp: group.timestamp,
			elements: group.elements.map((element) => [element.id, element.number]),
		})),
		snapshot,
	);
});

test("classe les fichiers séparément des autres liens et des extraits", () => {
	const groups = groupConversationElements([
		link("fichier", 100, "file:///tmp/exemple.md"),
		link("lien", 100, "https://example.com"),
		code("extrait", 100),
	]);

	assert.deepEqual(
		groups[0]?.elements.map((element) => element.category),
		["file", "link", "code"],
	);
});

test("filtre séparément les types et leurs unions", () => {
	const groups = groupConversationElements([
		link("fichier", 100, "file:///tmp/exemple.md"),
		link("lien", 100, "https://example.com"),
		code("extrait", 100),
	]);
	const idsFor = (...categories: ConversationCategory[]) =>
		filterConversationGroupsByType(groups, new Set(categories)).flatMap((group) =>
			group.elements.map((element) => element.id),
		);

	const unfiltered = filterConversationGroupsByType(groups, new Set<ConversationCategory>());
	assert.equal(unfiltered, groups);
	assert.deepEqual(
		unfiltered.flatMap((group) => group.elements.map((element) => [element.id, element.number])),
		[["fichier", 1], ["lien", 2], ["extrait", 3]],
	);
	assert.deepEqual(idsFor("file"), ["fichier"]);
	assert.deepEqual(idsFor("link"), ["lien"]);
	assert.deepEqual(idsFor("code"), ["extrait"]);
	assert.deepEqual(idsFor("file", "code"), ["fichier", "extrait"]);
	assert.deepEqual(idsFor("file", "link"), ["fichier", "lien"]);
	assert.deepEqual(idsFor("code", "link"), ["lien", "extrait"]);
	assert.deepEqual(idsFor("file", "code", "link"), ["fichier", "lien", "extrait"]);
});

test("recherche sans casse dans toutes les données complètes des éléments", () => {
	const groups = groupConversationElements([
		link("fichier", 100, "file:///tmp/Dossier/Rapport-Final.md"),
		link("lien", 100, "https://example.com/Guide?Section=Auth", "Documentation API"),
		code("extrait", 100, "const jeton = true;\nSecondeLigne", "TypeScript"),
	]);
	const idsFor = (query: string) =>
		filterConversationGroupsByText(groups, query).flatMap((group) => group.elements.map((element) => element.id));

	assert.deepEqual(idsFor("RAPPORT-FINAL"), ["fichier"]);
	assert.deepEqual(idsFor("/TMP/DOSSIER"), ["fichier"]);
	assert.deepEqual(idsFor("documentation api"), ["lien"]);
	assert.deepEqual(idsFor("SECTION=AUTH"), ["lien"]);
	assert.deepEqual(idsFor("typescript"), ["extrait"]);
	assert.deepEqual(idsFor("SECONDELIGNE"), ["extrait"]);
});

test("combine recherche et filtre de type dans la vue", () => {
	const groups = groupConversationElements([
		link("fichier-guide", 100, "file:///tmp/Guide-Code.md"),
		link("lien-guide", 100, "https://example.com/guide", "Guide Web"),
		code("extrait-guide", 100, "const guide = true;", "TypeScript"),
		link("autre-fichier", 100, "file:///tmp/autre.md"),
	]);
	const idsFor = (category: ConversationCategory, query: string) =>
		filterConversationGroupsView(groups, new Set([category]), query).flatMap((group) =>
			group.elements.map((element) => element.id),
		);

	assert.deepEqual(idsFor("file", "GUIDE"), ["fichier-guide"]);
	assert.deepEqual(idsFor("link", "guide"), ["lien-guide"]);
	assert.deepEqual(idsFor("code", "guide"), ["extrait-guide"]);
	assert.deepEqual(idsFor("file", "Web"), []);
});

test("bascule indépendamment C, U et F puis restaure la vue complète", () => {
	const groups = groupConversationElements([
		link("fichier", 100, "file:///tmp/exemple.md"),
		link("lien", 100, "https://example.com"),
		code("extrait", 100),
	]);
	const completed: Array<string | null> = [];
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, (result) => completed.push(result));
	const visibleIds = () => {
		navigator.render(100);
		return ["fichier", "lien", "extrait"].filter((id) => navigator.lineRangeOf(id));
	};

	navigator.handleInput("c");
	assert.equal(navigator.isTypeFilterActive("code"), true);
	assert.deepEqual(visibleIds(), ["extrait"]);
	navigator.handleInput("f");
	assert.equal(navigator.isTypeFilterActive("file"), true);
	assert.deepEqual(visibleIds(), ["fichier", "extrait"]);
	navigator.handleInput("c");
	assert.equal(navigator.isTypeFilterActive("code"), false);
	assert.deepEqual(visibleIds(), ["fichier"]);
	navigator.handleInput("u");
	assert.equal(navigator.isTypeFilterActive("link"), true);
	assert.deepEqual(visibleIds(), ["fichier", "lien"]);
	navigator.handleInput("f");
	assert.deepEqual(visibleIds(), ["lien"]);
	navigator.handleInput("u");
	assert.equal(navigator.isTypeFilterActive("link"), false);
	assert.deepEqual(visibleIds(), ["fichier", "lien", "extrait"]);
	assert.deepEqual(completed, []);
});

test("sélectionne initialement le premier élément du groupe le plus récent", () => {
	const groups = groupConversationElements([code("ancien", 100), code("recent", 300)]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;

	const navigator = new ConversationNavigator(tui, theme, groups, () => {});
	assert.equal(navigator.selectedId, "recent");

	const emptyNavigator = new ConversationNavigator(tui, theme, [], () => {});
	assert.equal(emptyNavigator.selectedId, undefined);
});

test("sélectionne un numéro exact sans modifier la vue", () => {
	const groups = groupConversationElements(
		Array.from({ length: 13 }, (_, index) => code(`element-${index + 1}`, 100)),
	);
	const completed: Array<string | null> = [];
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, (result) => completed.push(result));

	assert.ok(navigator.render(100).every((line) => !line.includes("Numéro :")));
	navigator.handleInput("1");
	assert.equal(navigator.isNumberFilterOpen, true);
	assert.equal(navigator.numberFilterQuery, "1");
	const firstSelectionLines = navigator.render(100);
	assert.ok(firstSelectionLines.some((line) => line.includes("Numéro : 1")));
	for (let number = 1; number <= 13; number++) assert.ok(navigator.lineRangeOf(`element-${number}`));

	navigator.handleInput("3");
	assert.equal(navigator.numberFilterQuery, "13");
	assert.equal(navigator.selectedId, "element-13");
	navigator.render(100);
	assert.ok(navigator.lineRangeOf("element-13"));
	assert.ok(navigator.lineRangeOf("element-1"));

	navigator.handleInput("\u007f");
	assert.equal(navigator.numberFilterQuery, "1");
	assert.equal(navigator.selectedId, "element-1");
	navigator.handleInput("\u007f");
	assert.equal(navigator.numberFilterQuery, "");
	assert.equal(navigator.isNumberFilterOpen, true);
	assert.equal(navigator.selectedId, "element-1");
	navigator.render(100);
	assert.ok(navigator.lineRangeOf("element-2"));
	assert.deepEqual(groups.flatMap((group) => group.elements.map((element) => element.number)), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]);
	assert.deepEqual(completed, []);

	const secondNavigator = new ConversationNavigator(tui, theme, groups, () => {});
	secondNavigator.handleInput("2");
	assert.equal(secondNavigator.selectedId, "element-2");
	assert.notEqual(secondNavigator.selectedId, "element-12");
});

test("conserve la sélection pour une cible numérique indisponible", () => {
	const groups = groupConversationElements([
		link("fichier", 100, "file:///tmp/exemple.md"),
		link("lien", 100, "https://example.com"),
		code("extrait", 100),
	]);
	const completed: Array<string | null> = [];
	const tui = { terminal: { rows: 10 }, requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
		bg(_color: string, text: string) {
			return text;
		},
	} as never;

	const zeroNavigator = new ConversationNavigator(tui, theme, groups, (result) => completed.push(result));
	zeroNavigator.handleInput("0");
	assert.equal(zeroNavigator.selectedId, "fichier");
	assert.equal(zeroNavigator.isNumberTargetUnavailable, true);
	assert.ok(zeroNavigator.render(60).some((line) => line.includes("indisponible")));
	zeroNavigator.handleInput("\u007f");
	assert.equal(zeroNavigator.numberFilterQuery, "");
	assert.equal(zeroNavigator.isNumberFilterOpen, true);
	assert.equal(zeroNavigator.isNumberTargetUnavailable, false);
	assert.equal(zeroNavigator.selectedId, "fichier");

	const missingNavigator = new ConversationNavigator(tui, theme, groups, (result) => completed.push(result));
	missingNavigator.handleInput("9");
	assert.equal(missingNavigator.selectedId, "fichier");
	assert.equal(missingNavigator.isNumberTargetUnavailable, true);

	const hiddenNavigator = new ConversationNavigator(tui, theme, groups, (result) => completed.push(result));
	hiddenNavigator.handleInput("f");
	hiddenNavigator.handleInput("2");
	assert.equal(hiddenNavigator.selectedId, "fichier");
	assert.equal(hiddenNavigator.isNumberTargetUnavailable, true);
	hiddenNavigator.render(60);
	assert.equal(hiddenNavigator.lineRangeOf("lien"), undefined);
	assert.deepEqual(completed, []);
});

test("efface la saisie numérique avant chaque navigation", () => {
	const groups = groupConversationElements([
		code("ancien-a", 100),
		code("ancien-b", 100),
		code("recent-a", 300),
		code("recent-b", 300),
	]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const movements = [
		["\u001b[A", "recent-a"],
		["k", "recent-a"],
		["\u001b[B", "ancien-a"],
		["j", "ancien-a"],
		["\u001b[D", "recent-b"],
		["h", "recent-b"],
		["\u001b[C", "ancien-a"],
		["l", "ancien-a"],
	] as const;

	for (const [input, expectedId] of movements) {
		const navigator = new ConversationNavigator(tui, theme, groups, () => {});
		navigator.handleInput("2");
		assert.equal(navigator.selectedId, "recent-b");
		navigator.handleInput(input);
		assert.equal(navigator.selectedId, expectedId);
		assert.equal(navigator.numberFilterQuery, "");
		assert.equal(navigator.isNumberFilterOpen, false);
		assert.equal(navigator.isNumberTargetUnavailable, false);
	}
});

test("réinitialise la sélection numérique avec les filtres et la recherche", () => {
	const groups = groupConversationElements([
		link("fichier-a", 100, "file:///tmp/alpha.md"),
		link("fichier-b", 100, "file:///tmp/alpine.md"),
		link("lien", 100, "https://example.com/beta"),
	]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;

	const filterNavigator = new ConversationNavigator(tui, theme, groups, () => {});
	filterNavigator.handleInput("2");
	assert.equal(filterNavigator.selectedId, "fichier-b");
	filterNavigator.handleInput("f");
	assert.equal(filterNavigator.selectedId, "fichier-a");
	assert.equal(filterNavigator.numberFilterQuery, "");
	assert.equal(filterNavigator.isNumberFilterOpen, false);
	filterNavigator.handleInput("2");
	filterNavigator.handleInput("f");
	assert.equal(filterNavigator.selectedId, "fichier-a");
	assert.equal(filterNavigator.numberFilterQuery, "");

	const searchNavigator = new ConversationNavigator(tui, theme, groups, () => {});
	searchNavigator.handleInput("2");
	searchNavigator.handleInput("i");
	assert.equal(searchNavigator.selectedId, "fichier-a");
	assert.equal(searchNavigator.numberFilterQuery, "");
	assert.equal(searchNavigator.isNumberFilterOpen, false);
	searchNavigator.handleInput("a");
	searchNavigator.handleInput("\u001b[B");
	assert.equal(searchNavigator.selectedId, "fichier-b");
	searchNavigator.handleInput("l");
	assert.equal(searchNavigator.searchQuery, "al");
	assert.equal(searchNavigator.selectedId, "fichier-a");
	assert.equal(searchNavigator.numberFilterQuery, "");
	searchNavigator.handleInput("\u001b[B");
	searchNavigator.handleInput("\u007f");
	assert.equal(searchNavigator.searchQuery, "a");
	assert.equal(searchNavigator.selectedId, "fichier-a");
});

test("met à jour sélection et viewport sans filtrer ni exécuter", () => {
	const groups = groupConversationElements(
		Array.from({ length: 14 }, (_, index) => code(`element-${index + 1}`, 100)),
	);
	const completed: Array<string | null> = [];
	const tui = { terminal: { rows: 7 }, requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
		bg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, (result) => completed.push(result));

	navigator.handleInput("\u001b[B");
	assert.equal(navigator.selectedId, "element-2");
	navigator.handleInput("1");
	assert.equal(navigator.selectedId, "element-1");
	navigator.handleInput("\u001b[B");
	assert.equal(navigator.selectedId, "element-2");
	assert.equal(navigator.numberFilterQuery, "");
	assert.equal(navigator.isNumberFilterOpen, false);
	navigator.handleInput("1");
	navigator.handleInput("0");
	assert.equal(navigator.selectedId, "element-10");
	assert.deepEqual(completed, []);
	assert.ok(navigator.render(50).some((line) => line.includes("10. text")));

	navigator.handleInput("9");
	assert.equal(navigator.selectedId, "element-10");
	const unavailableLines = navigator.render(50);
	assert.ok(unavailableLines.some((line) => line.includes("indisponible")));
	assert.deepEqual(completed, []);

	navigator.handleInput("\u007f");
	assert.equal(navigator.selectedId, "element-10");
	assert.ok(navigator.render(50).some((line) => line.includes("10. text")));
});

test("saisit et efface les raccourcis comme texte en mode recherche", () => {
	const groups = groupConversationElements([code("extrait", 100, "cufihjkl12")]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	navigator.handleInput("i");
	assert.equal(navigator.isSearchMode, true);
	for (const character of "cufihjkl12") navigator.handleInput(character);
	assert.equal(navigator.searchQuery, "cufihjkl12");
	assert.equal(navigator.numberFilterQuery, "");
	assert.equal(navigator.isNumberFilterOpen, false);
	assert.equal(navigator.isTypeFilterActive("code"), false);
	assert.equal(navigator.isTypeFilterActive("link"), false);
	assert.equal(navigator.isTypeFilterActive("file"), false);

	for (let index = 0; index < "cufihjkl12".length; index++) navigator.handleInput("\u007f");
	assert.equal(navigator.searchQuery, "");
	assert.equal(navigator.isSearchMode, true);
	assert.equal(navigator.selectedId, "extrait");
});

test("met à jour sélection, viewport, groupes et état vide avec les filtres V3", () => {
	const groups = groupConversationElements([
		link("fichier", 300, "file:///tmp/sans-correspondance.md"),
		code("extrait", 300, "needle dans le code"),
		link("lien", 100, "https://example.com/needle", "Lien needle"),
	]);
	const completed: Array<string | null> = [];
	const tui = { terminal: { rows: 10 }, requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
		bg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, (result) => completed.push(result));

	navigator.handleInput("\u001b[B");
	assert.equal(navigator.selectedId, "extrait");
	navigator.handleInput("c");
	assert.equal(navigator.selectedId, "extrait");
	let lines = navigator.render(60);
	assert.ok(lines.some((line) => line.includes("2. text")));
	assert.equal(navigator.lineRangeOf("fichier"), undefined);
	assert.equal(navigator.lineRangeOf("lien"), undefined);

	navigator.handleInput("c");
	navigator.handleInput("i");
	for (const character of "needle") navigator.handleInput(character);
	assert.equal(navigator.selectedId, "extrait");
	navigator.handleInput("\u001b[B");
	assert.equal(navigator.selectedId, "lien");
	lines = navigator.render(60);
	assert.ok(lines.some((line) => line.includes("3. Lien needle")));
	assert.equal(navigator.lineRangeOf("fichier"), undefined);

	navigator.handleInput("x");
	assert.equal(navigator.selectedId, undefined);
	lines = navigator.render(60);
	assert.ok(lines.some((line) => line.includes("Aucune entrée ne correspond")));
	assert.equal(navigator.lineRangeOf("extrait"), undefined);
	assert.equal(navigator.lineRangeOf("lien"), undefined);
	navigator.handleInput("\r");
	assert.deepEqual(completed, []);

	navigator.handleInput("\u007f");
	assert.equal(navigator.selectedId, "extrait");
	assert.ok(navigator.render(60).some((line) => line.includes("2. text")));
});

test("déplace la sélection avec les flèches uniquement entre les éléments", () => {
	const groups = groupConversationElements([
		code("ancien", 100),
		code("recent-a", 300),
		code("recent-b", 300),
	]);
	let renderRequests = 0;
	const tui = {
		requestRender() {
			renderRequests++;
		},
	} as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	navigator.handleInput("\u001b[B");
	assert.equal(navigator.selectedId, "recent-b");
	navigator.handleInput("\u001b[B");
	assert.equal(navigator.selectedId, "ancien");
	navigator.handleInput("\u001b[B");
	assert.equal(navigator.selectedId, "ancien");
	navigator.handleInput("\u001b[A");
	assert.equal(navigator.selectedId, "recent-b");
	assert.equal(renderRequests, 3);
});

test("saute au premier élément du message suivant ou précédent avec gauche et droite", () => {
	const groups = groupConversationElements([
		code("ancien", 100),
		code("intermediaire", 200),
		code("recent-a", 300),
		code("recent-b", 300),
	]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	navigator.handleInput("\u001b[B");
	assert.equal(navigator.selectedId, "recent-b");
	navigator.handleInput("\u001b[C");
	assert.equal(navigator.selectedId, "intermediaire");
	navigator.handleInput("\u001b[C");
	assert.equal(navigator.selectedId, "ancien");
	navigator.handleInput("\u001b[C");
	assert.equal(navigator.selectedId, "ancien");
	navigator.handleInput("\u001b[D");
	assert.equal(navigator.selectedId, "intermediaire");
	navigator.handleInput("\u001b[D");
	assert.equal(navigator.selectedId, "recent-a");
});

test("H, J, K et L sont strictement équivalents aux quatre flèches", () => {
	const groups = groupConversationElements([
		code("ancien", 100),
		code("intermediaire", 200),
		code("recent-a", 300),
		code("recent-b", 300),
	]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const arrows = new ConversationNavigator(tui, theme, groups, () => {});
	const vim = new ConversationNavigator(tui, theme, groups, () => {});
	const inputs = [
		["\u001b[B", "j"],
		["\u001b[B", "j"],
		["\u001b[A", "k"],
		["\u001b[C", "l"],
		["\u001b[C", "l"],
		["\u001b[C", "l"],
		["\u001b[D", "h"],
		["\u001b[D", "h"],
		["\u001b[D", "h"],
		["\u001b[A", "k"],
	] as const;

	for (const [arrow, vimKey] of inputs) {
		arrows.handleInput(arrow);
		vim.handleInput(vimKey);
		assert.equal(vim.selectedId, arrows.selectedId);
	}
});

test("conserve navigation, validation et fermeture avec le filtre actif ou vidé", () => {
	const groups = groupConversationElements([
		...Array.from({ length: 6 }, (_, index) => code(`recent-${index + 1}`, 300)),
		...Array.from({ length: 6 }, (_, index) => code(`ancien-${index + 1}`, 100)),
	]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const createNavigator = (done: (result: string | null) => void = () => {}) =>
		new ConversationNavigator(tui, theme, groups, done);

	for (const emptyFilter of [false, true]) {
		const arrows = createNavigator();
		const vim = createNavigator();
		arrows.handleInput("1");
		vim.handleInput("1");
		if (emptyFilter) {
			arrows.handleInput("\u007f");
			vim.handleInput("\u007f");
		}
		for (const [arrow, vimKey] of [
			["\u001b[B", "j"],
			["\u001b[A", "k"],
			["\u001b[C", "l"],
			["\u001b[D", "h"],
		] as const) {
			arrows.handleInput(arrow);
			vim.handleInput(vimKey);
			assert.equal(vim.selectedId, arrows.selectedId);
		}
	}

	const confirmed: Array<string | null> = [];
	const confirmNavigator = createNavigator((result) => confirmed.push(result));
	confirmNavigator.handleInput("1");
	confirmNavigator.handleInput("j");
	confirmNavigator.handleInput("\r");
	assert.deepEqual(confirmed, ["recent-2"]);

	for (const closeInput of ["\u001b", "\u001b\f"]) {
		const cancelled: Array<string | null> = [];
		const navigator = createNavigator((result) => cancelled.push(result));
		navigator.handleInput("1");
		navigator.handleInput(closeInput);
		assert.deepEqual(cancelled, [null]);
	}
});

test("navigue, valide et ferme correctement depuis le mode recherche", () => {
	const groups = groupConversationElements([
		code("ancien", 100, "résultat ancien"),
		code("recent-a", 300, "résultat alpha"),
		code("recent-b", 300, "résultat beta"),
	]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const createNavigator = (done: (result: string | null) => void) =>
		new ConversationNavigator(tui, theme, groups, done);
	const enterSearch = (navigator: ConversationNavigator) => {
		navigator.handleInput("i");
		for (const character of "résultat") navigator.handleInput(character);
	};

	const confirmed: Array<string | null> = [];
	const confirmNavigator = createNavigator((result) => confirmed.push(result));
	enterSearch(confirmNavigator);
	confirmNavigator.handleInput("\u001b[B");
	assert.equal(confirmNavigator.selectedId, "recent-b");
	confirmNavigator.handleInput("\u001b[C");
	assert.equal(confirmNavigator.selectedId, "ancien");
	confirmNavigator.handleInput("\u001b[D");
	assert.equal(confirmNavigator.selectedId, "recent-a");
	confirmNavigator.handleInput("\u001b[B");
	confirmNavigator.handleInput("\u001b[A");
	assert.equal(confirmNavigator.selectedId, "recent-a");
	confirmNavigator.handleInput("\r");
	assert.deepEqual(confirmed, ["recent-a"]);

	const escaped: Array<string | null> = [];
	const escapeNavigator = createNavigator((result) => escaped.push(result));
	enterSearch(escapeNavigator);
	escapeNavigator.handleInput("\u001b");
	assert.equal(escapeNavigator.isSearchMode, false);
	assert.equal(escapeNavigator.searchQuery, "résultat");
	assert.deepEqual(escaped, []);
	escapeNavigator.handleInput("\u001b");
	assert.deepEqual(escaped, [null]);

	const toggled: Array<string | null> = [];
	const toggleNavigator = createNavigator((result) => toggled.push(result));
	enterSearch(toggleNavigator);
	toggleNavigator.handleInput("\u001b\f");
	assert.deepEqual(toggled, [null]);
});

test("préserve les comportements V2 sans filtre de type ni recherche", () => {
	const groups = groupConversationElements([
		...Array.from({ length: 6 }, (_, index) => code(`recent-${index + 1}`, 300)),
		...Array.from({ length: 6 }, (_, index) => code(`ancien-${index + 1}`, 100)),
	]);
	const completed: Array<string | null> = [];
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, (result) => completed.push(result));

	assert.equal(navigator.isSearchMode, false);
	assert.equal(navigator.searchQuery, "");
	assert.equal(navigator.isTypeFilterActive("code"), false);
	assert.equal(navigator.isTypeFilterActive("link"), false);
	assert.equal(navigator.isTypeFilterActive("file"), false);
	navigator.handleInput("j");
	assert.equal(navigator.selectedId, "recent-2");
	navigator.handleInput("k");
	assert.equal(navigator.selectedId, "recent-1");
	navigator.handleInput("l");
	assert.equal(navigator.selectedId, "ancien-1");
	navigator.handleInput("h");
	assert.equal(navigator.selectedId, "recent-1");
	navigator.handleInput("1");
	assert.equal(navigator.numberFilterQuery, "1");
	assert.equal(navigator.selectedId, "recent-1");
	navigator.handleInput("\u007f");
	assert.equal(navigator.numberFilterQuery, "");
	navigator.handleInput("\r");
	assert.deepEqual(completed, ["recent-1"]);
});

test("retourne l’identifiant avec Entrée et null avec Échap", () => {
	const groups = groupConversationElements([code("selection", 100)]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const confirmed: Array<string | null> = [];
	const cancelled: Array<string | null> = [];
	const confirmedNavigator = new ConversationNavigator(tui, theme, groups, (result) => confirmed.push(result));
	const cancelledNavigator = new ConversationNavigator(tui, theme, groups, (result) => cancelled.push(result));

	confirmedNavigator.handleInput("\r");
	confirmedNavigator.handleInput("\r");
	cancelledNavigator.handleInput("\u001b");
	cancelledNavigator.handleInput("\u001b");

	assert.deepEqual(confirmed, ["selection"]);
	assert.deepEqual(cancelled, [null]);
});

test("ferme le composant et retourne son identifiant avant de poursuivre", async () => {
	const events: string[] = [];
	let overlayOptions: unknown;
	const tui = {
		terminal: { rows: 30 },
		requestRender() {},
	};
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
		bg(_color: string, text: string) {
			return text;
		},
	};
	const ctx = {
		ui: {
			async custom(
				factory: (tuiValue: unknown, themeValue: unknown, keybindings: unknown, done: (value: string | null) => void) => ConversationNavigator,
				options: unknown,
			) {
				overlayOptions = options;
				events.push("ouvert");
				let result: string | null = null;
				const component = factory(tui, theme, {}, (value) => {
					events.push("fermé");
					result = value;
				});
				component.handleInput("\r");
				return result;
			},
		},
	} as never;

	const result = await selectConversationElement(ctx, [code("selection", 100)]);
	events.push("action suivante");

	assert.equal(result, "selection");
	assert.deepEqual(events, ["ouvert", "fermé", "action suivante"]);
	assert.deepEqual(overlayOptions, {
		overlay: true,
		overlayOptions: { anchor: "center", width: "80%", maxHeight: "80%", margin: 1 },
	});
});

test("Ctrl+Alt+L ferme sans action et la réouverture crée un état neuf", async () => {
	const selectedAtClose: Array<string | undefined> = [];
	const results: Array<string | null> = [];
	const visibleAtOpening: string[][] = [];
	let opening = 0;
	const tui = { terminal: { rows: 5 }, requestRender() {} };
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
		bg(_color: string, text: string) {
			return text;
		},
	};
	const ctx = {
		ui: {
			notify() {},
			async custom(
				factory: (tuiValue: unknown, themeValue: unknown, keybindings: unknown, done: (value: string | null) => void) => ConversationNavigator,
			) {
				let result: string | null = null;
				const component = factory(tui, theme, {}, (value) => {
					result = value;
				});
				visibleAtOpening.push(component.render(80));
				if (opening === 0) {
					component.handleInput("\u001b[B");
					component.render(80);
					component.handleInput("\u001b[B");
					component.render(80);
				}
				selectedAtClose.push(component.selectedId);
				component.handleInput(opening === 0 ? "\u001b\f" : "\u001b");
				results.push(result);
				opening++;
				return result;
			},
		},
	} as never;
	const elements = [
		link("a", 100, "file:///tmp/a.md"),
		link("b", 100, "file:///tmp/b.md"),
		link("c", 100, "file:///tmp/c.md"),
	];

	await selectConversationElement(ctx, elements);
	await selectConversationElement(ctx, elements);

	assert.deepEqual(selectedAtClose, ["c", "a"]);
	assert.deepEqual(results, [null, null]);
	assert.ok(visibleAtOpening[1]?.some((line) => line.includes("1. a.md")));
});

test("signale une conversation vide sans ouvrir le composant", async () => {
	const notifications: Array<{ message: string; level: string }> = [];
	let customCalls = 0;
	const ctx = {
		ui: {
			notify(message: string, level: string) {
				notifications.push({ message, level });
			},
			async custom() {
				customCalls++;
				return null;
			},
		},
	} as never;

	const result = await selectConversationElement(ctx, []);

	assert.equal(result, null);
	assert.equal(customCalls, 0);
	assert.deepEqual(notifications, [
		{ message: "Aucun lien ou extrait de code dans cette conversation.", level: "info" },
	]);
});

test("reconstruit le registre depuis la branche active au démarrage et après session_tree", async () => {
	const handlers = new Map<string, Array<(event: unknown, ctx: unknown) => unknown>>();
	let shortcutHandler: ((ctx: unknown) => Promise<void>) | undefined;
	const pi = {
		on(event: string, handler: (event: unknown, ctx: unknown) => unknown) {
			const eventHandlers = handlers.get(event) ?? [];
			eventHandlers.push(handler);
			handlers.set(event, eventHandlers);
		},
		registerShortcut(_shortcut: string, definition: { handler: (ctx: unknown) => Promise<void> }) {
			shortcutHandler = definition.handler;
		},
		appendEntry() {},
	} as never;
	conversationNavigationExtension(pi);

	let branch: unknown[] = [];
	const renderedMenus: string[][] = [];
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
		bg(_color: string, text: string) {
			return text;
		},
	};
	const tui = { terminal: { rows: 30 }, requestRender() {} };
	const ctx = {
		mode: "tui",
		cwd: "/tmp",
		sessionManager: {
			getBranch() {
				return branch;
			},
			isPersisted() {
				return false;
			},
		},
		ui: {
			notify() {},
			async custom(
				factory: (tuiValue: unknown, themeValue: unknown, keybindings: unknown, done: (value: string | null) => void) => ConversationNavigator,
			) {
				let result: string | null = null;
				const component = factory(tui, theme, {}, (value) => {
					result = value;
				});
				renderedMenus.push(component.render(80));
				component.handleInput("\u001b");
				return result;
			},
		},
	} as never;

	branch = [
		{ type: "message", message: { role: "assistant", timestamp: 100, content: [{ type: "text", text: "```text\nalpha\n```" }] } },
	];
	await handlers.get("session_start")?.[0]?.({}, ctx);
	await shortcutHandler?.(ctx);

	branch = [
		{ type: "message", message: { role: "assistant", timestamp: 200, content: [{ type: "text", text: "```text\nbeta\n```" }] } },
	];
	await handlers.get("session_tree")?.[0]?.({}, ctx);
	await shortcutHandler?.(ctx);

	assert.ok(renderedMenus[0]?.some((line) => line.includes("alpha")));
	assert.ok(renderedMenus[1]?.some((line) => line.includes("beta")));
	assert.ok(renderedMenus[1]?.every((line) => !line.includes("alpha")));
});

test("ouvre une URI avec xdg-open comme argument distinct et détache le processus", async () => {
	const calls: Array<{ command: string; args: string[]; options: unknown }> = [];
	let unrefCalled = false;
	const fakeSpawn = ((command: string, args: string[], options: unknown) => {
		calls.push({ command, args, options });
		const child = new EventEmitter() as EventEmitter & { unref(): void };
		child.unref = () => {
			unrefCalled = true;
		};
		queueMicrotask(() => child.emit("spawn"));
		return child;
	}) as unknown as typeof import("node:child_process").spawn;
	const uri = "https://example.com/document?q=deux mots&x='citation'";

	await openConversationLink(uri, fakeSpawn);

	assert.deepEqual(calls, [
		{
			command: "xdg-open",
			args: [uri],
			options: { detached: true, stdio: "ignore", shell: false },
		},
	]);
	assert.equal(unrefCalled, true);
});

test("copie exactement un extrait sur l’entrée standard de wl-copy et attend sa fin", async () => {
	const calls: Array<{ command: string; args: string[]; options: unknown }> = [];
	const chunks: Buffer[] = [];
	const fakeSpawn = ((command: string, args: string[], options: unknown) => {
		calls.push({ command, args, options });
		const child = new EventEmitter() as EventEmitter & { stdin: Writable };
		child.stdin = new Writable({
			write(chunk, _encoding, callback) {
				chunks.push(Buffer.from(chunk));
				callback();
			},
			final(callback) {
				callback();
				queueMicrotask(() => child.emit("close", 0, null));
			},
		});
		return child;
	}) as unknown as typeof import("node:child_process").spawn;
	const content = "\tconst message = 'été';  \n\nfin\n";

	await copyConversationCode(content, fakeSpawn);

	assert.deepEqual(calls, [
		{
			command: "wl-copy",
			args: [],
			options: { stdio: ["pipe", "ignore", "ignore"], shell: false },
		},
	]);
	assert.deepEqual(Buffer.concat(chunks), Buffer.from(content, "utf8"));
});

test("signale dans Pi les erreurs d’ouverture et de copie", async () => {
	const notifications: Array<{ message: string; level: string }> = [];
	const ctx = {
		ui: {
			notify(message: string, level: string) {
				notifications.push({ message, level });
			},
		},
	} as never;
	const actions = {
		async openLink() {
			throw new Error("xdg-open introuvable");
		},
		async copyCode() {
			throw new Error("wl-copy introuvable");
		},
	};

	const opened = await executeConversationElement(ctx, link("web", 100, "https://example.com"), actions);
	const copied = await executeConversationElement(ctx, code("extrait", 100), actions);

	assert.equal(opened, false);
	assert.equal(copied, false);
	assert.deepEqual(notifications, [
		{ message: "Impossible d’ouvrir le lien : xdg-open introuvable", level: "error" },
		{ message: "Impossible de copier l’extrait : wl-copy introuvable", level: "error" },
	]);
});

test("calcule la plage de lignes visuelles de chaque élément", () => {
	const groups = groupConversationElements([
		link("fichier", 100, "file:///tmp/exemple.md"),
		code("extrait", 100, "premiere\ndeuxieme", "text"),
	]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	assert.equal(navigator.lineRangeOf("fichier"), undefined);
	navigator.render(80);
	assert.deepEqual(navigator.lineRangeOf("fichier"), { start: 1, end: 3 });
	assert.deepEqual(navigator.lineRangeOf("extrait"), { start: 3, end: 6 });
	assert.equal(navigator.lineRangeOf("inconnu"), undefined);

	navigator.invalidate();
	assert.equal(navigator.lineRangeOf("fichier"), undefined);
});

test("fait défiler le viewport pour conserver tout l’élément sélectionné visible", () => {
	const groups = groupConversationElements([
		link("a", 100, "file:///tmp/a.md"),
		link("b", 100, "file:///tmp/b.md"),
		link("c", 100, "file:///tmp/c.md"),
	]);
	const tui = {
		terminal: { rows: 7 },
		requestRender() {},
	} as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	navigator.render(80);
	navigator.handleInput("\u001b[B");
	navigator.render(80);
	navigator.handleInput("\u001b[B");
	const visibleLines = navigator.render(80);

	assert.equal(visibleLines.length, 5);
	assert.ok(visibleLines.some((line) => line.includes("  3. c.md")));
	assert.ok(visibleLines.some((line) => line.includes("     /tmp/c.md")));
});

test("affiche le début d’un extrait plus haut que le viewport et permet de poursuivre la navigation", () => {
	const groups = groupConversationElements([
		link("avant", 100, "file:///tmp/avant.md"),
		code("long", 100, "ligne 1\nligne 2\nligne 3\nligne 4\nligne 5", "typescript"),
		link("apres", 100, "file:///tmp/apres.md"),
	]);
	const selectedLines: string[] = [];
	const tui = {
		terminal: { rows: 7 },
		requestRender() {},
	} as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
		bg(_color: string, text: string) {
			selectedLines.push(text);
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	navigator.render(80);
	selectedLines.length = 0;
	navigator.handleInput("\u001b[B");
	const longExcerptLines = navigator.render(80);
	assert.equal(longExcerptLines.length, 5);
	assert.ok(longExcerptLines.some((line) => line.includes("2. typescript")));
	assert.ok(longExcerptLines.some((line) => line.includes("ligne 1")));
	assert.ok(selectedLines.some((line) => line.includes("2. typescript")));

	navigator.handleInput("\u001b[B");
	const followingElementLines = navigator.render(80);
	assert.equal(navigator.selectedId, "apres");
	assert.ok(followingElementLines.some((line) => line.includes("3. apres.md")));
	assert.ok(followingElementLines.some((line) => line.includes("/tmp/apres.md")));
});

test("préserve navigation et viewport avec plusieurs groupes, hauteurs et dimensions", () => {
	const groups = groupConversationElements([
		code("ancien", 100, "a\nb\nc", "text"),
		link("intermediaire", 200, "file:///tmp/intermediaire.md"),
		code("recent-court", 300, "court", "text"),
		code("recent-long", 300, "un\ndeux\ntrois\nquatre\ncinq", "typescript"),
	]);
	const terminal = { rows: 7 };
	const tui = {
		terminal,
		requestRender() {},
	} as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
		bg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	let lines = navigator.render(18);
	assert.ok(lines.length <= 5);
	assert.ok(lines.every((line) => visibleWidth(line) <= 18));

	navigator.handleInput("\u001b[B");
	lines = navigator.render(18);
	assert.equal(navigator.selectedId, "recent-long");
	assert.ok(lines.some((line) => line.includes("2. typescript")));

	navigator.handleInput("\u001b[C");
	lines = navigator.render(18);
	assert.equal(navigator.selectedId, "intermediaire");
	assert.ok(lines.some((line) => line.includes("3.")));

	terminal.rows = 10;
	lines = navigator.render(40);
	assert.equal(navigator.selectedId, "intermediaire");
	assert.ok(lines.length <= 8);
	assert.ok(lines.every((line) => visibleWidth(line) <= 40));
	assert.ok(lines.some((line) => line.includes("/tmp/intermediaire.md")));

	navigator.handleInput("\u001b[C");
	assert.equal(navigator.selectedId, "ancien");
	navigator.render(40);
	navigator.handleInput("\u001b[D");
	assert.equal(navigator.selectedId, "intermediaire");
});

test("adapte le viewport de la sélection numérique aux groupes et dimensions", () => {
	const groups = groupConversationElements([
		...Array.from({ length: 6 }, (_, index) => code(`recent-${index + 1}`, 300)),
		...Array.from({ length: 6 }, (_, index) => code(`intermediaire-${index + 1}`, 200)),
		...Array.from({ length: 6 }, (_, index) => code(`ancien-${index + 1}`, 100)),
	]);
	const terminal = { rows: 20 };
	const tui = { terminal, requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
		bg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	navigator.handleInput("1");
	navigator.handleInput("7");
	assert.equal(navigator.selectedId, "ancien-5");
	let lines = navigator.render(80);
	assert.ok(lines.some((line) => line.includes("Numéro : 17")));
	assert.ok(lines.some((line) => line.includes("17. text")));
	assert.ok(navigator.lineRangeOf("recent-1"));
	assert.ok(navigator.lineRangeOf("ancien-6"));

	terminal.rows = 8;
	for (const width of [30, 12, 3, 2, 1]) {
		lines = navigator.render(width);
		assert.ok(lines.length <= Math.floor(terminal.rows * 0.8));
		assert.ok(lines.every((line) => visibleWidth(line) <= width));
	}
	assert.equal(navigator.selectedId, "ancien-5");
	assert.ok(navigator.render(30).some((line) => line.includes("17. text")));
});

test("redimensionne les indicateurs, champs, listes longues et vues vides", () => {
	const groups = groupConversationElements(
		Array.from({ length: 20 }, (_, index) => code(`element-${index + 1}`, 100, `item ${index + 1}`)),
	);
	const terminal = { rows: 20 };
	const tui = { terminal, requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
		bg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	navigator.handleInput("1");
	let lines = navigator.render(80);
	assert.ok(lines.some((line) => line.includes("Numéro : 1")));
	navigator.handleInput("i");
	for (const character of "item") navigator.handleInput(character);
	lines = navigator.render(80);
	assert.ok(lines.some((line) => line.includes("Filtres :")));
	assert.ok(lines.every((line) => !line.includes("Numéro :")));
	assert.ok(lines.some((line) => line.includes("Recherche : item")));
	assert.ok(lines.some((line) => line.includes("1. text")));
	assert.ok(lines.every((line) => visibleWidth(line) <= 80));

	terminal.rows = 10;
	for (const width of [24, 12, 3, 2, 1]) {
		lines = navigator.render(width);
		assert.ok(lines.length <= Math.floor(terminal.rows * 0.8));
		assert.ok(lines.every((line) => visibleWidth(line) <= width));
	}

	navigator.handleInput("z");
	lines = navigator.render(24);
	assert.equal(navigator.selectedId, undefined);
	assert.ok(lines.some((line) => line.includes("Aucune entrée")));
	assert.ok(lines.every((line) => visibleWidth(line) <= 24));
});

test("rend le nom et le chemin complet d’un fichier sur des lignes distinctes", () => {
	const groups = groupConversationElements([link("fichier", 100, "file:///tmp/dossier/exemple.md")]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	const lines = navigator.render(80);
	assert.ok(lines.some((line) => line.includes("  1. exemple.md")));
	assert.ok(lines.some((line) => line.includes("     /tmp/dossier/exemple.md")));
});

test("rend une étiquette lisible sans modifier l’URI complète d’un lien", () => {
	const uri = "https://example.com/documentation?page=2#section";
	const groups = groupConversationElements([
		link("web", 100, uri, uri),
		link("courriel", 100, "mailto:will@example.com", "mailto:will@example.com"),
	]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	const lines = navigator.render(100);
	assert.ok(lines.some((line) => line.includes("  1. example.com/documentation?page=2#section")));
	assert.ok(lines.some((line) => line.includes(`     ${uri}`)));
	assert.ok(lines.some((line) => line.includes("  2. will@example.com")));
	assert.equal(groups[0]?.elements[0]?.kind === "link" ? groups[0].elements[0].uri : undefined, uri);
});

test("rend toutes les lignes d’un extrait sous un seul numéro et son langage", () => {
	const groups = groupConversationElements([code("extrait", 100, "alpha\n\nbeta\n", "typescript")]);
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	const lines = navigator.render(80);
	assert.ok(lines.some((line) => line.includes("  1. typescript")));
	assert.ok(lines.some((line) => line.includes("     alpha")));
	assert.ok(lines.some((line) => line.includes("      ")));
	assert.ok(lines.some((line) => line.includes("     beta")));
	assert.equal(lines.filter((line) => line.includes("1. typescript")).length, 1);
});

test("entoure la fenêtre popup avec une bordure du thème Pi", () => {
	const groups = groupConversationElements([code("extrait", 100, "contenu", "text")]);
	const tui = { terminal: { rows: 20 }, requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			return text;
		},
		bg(_color: string, text: string) {
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	const lines = navigator.render(30);
	assert.equal(lines[0], `╭${"─".repeat(28)}╮`);
	assert.equal(lines.at(-1), `╰${"─".repeat(28)}╯`);
	assert.ok(lines.slice(1, -1).every((line) => line.startsWith("│") && line.endsWith("│")));
	assert.ok(lines.every((line) => visibleWidth(line) === 30));
});

test("applique le thème Pi et ne dépasse pas la largeur de rendu", () => {
	const groups = groupConversationElements([
		link("long", 100, "https://example.com/un/chemin/beaucoup/trop/long", "Une étiquette beaucoup trop longue"),
		code("code", 100, "une ligne de code beaucoup trop longue", "typescript"),
	]);
	const colors: string[] = [];
	const tui = { requestRender() {} } as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(color: string, text: string) {
			colors.push(color);
			return text;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	const lines = navigator.render(20);
	assert.ok(lines.every((line) => visibleWidth(line) <= 20));
	assert.ok(colors.includes("accent"));
	assert.ok(colors.includes("dim"));
	assert.deepEqual(navigator.render(0), []);
});

test("invalide le cache et redemande un rendu après un changement de thème", () => {
	const groups = groupConversationElements([link("web", 100, "https://example.com", "Exemple")]);
	let marker = "ancien";
	let foregroundCalls = 0;
	let renderRequests = 0;
	const tui = {
		requestRender() {
			renderRequests++;
		},
	} as never;
	const theme = {
		bold(text: string) {
			return text;
		},
		fg(_color: string, text: string) {
			foregroundCalls++;
			return `[${marker}]${text}`;
		},
	} as never;
	const navigator = new ConversationNavigator(tui, theme, groups, () => {});

	const firstRender = navigator.render(100);
	const callsAfterFirstRender = foregroundCalls;
	assert.equal(navigator.render(100), firstRender);
	assert.equal(foregroundCalls, callsAfterFirstRender);

	marker = "nouveau";
	navigator.invalidate();
	const secondRender = navigator.render(100);
	assert.equal(renderRequests, 1);
	assert.notDeepEqual(secondRender, firstRender);
	assert.ok(secondRender.some((line) => line.includes("[nouveau]")));
});

test("ne produit aucun groupe vide et retourne un snapshot immuable", () => {
	assert.deepEqual(groupConversationElements([]), []);

	const groups = groupConversationElements([code("a", 200), code("b", 100)]);
	assert.ok(groups.every((group) => group.elements.length > 0));
	assert.ok(Object.isFrozen(groups));
	assert.ok(groups.every(Object.isFrozen));
	assert.ok(groups.every((group) => Object.isFrozen(group.elements)));
	assert.ok(groups.every((group) => group.elements.every(Object.isFrozen)));
	assert.ok(Object.isFrozen(listSelectableIds(groups)));
});
