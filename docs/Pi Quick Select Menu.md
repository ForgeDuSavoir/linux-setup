# Pi Quick Select Menu

The Quick Select menu lets you find resources from the active Pi conversation:

- files that were used, modified, or mentioned;
- HTTP(S) links and `mailto:` addresses;
- Markdown code blocks.

## Opening and closing the menu

Press `Ctrl+Alt+L` to open the menu.

When the menu is already open:

- `Ctrl+Alt+L` closes it without performing an action;
- `Escape` also closes it, unless search mode is active.

Each time you open the menu, it starts with a fresh selection state and selects the first available item.

## Layout

Resources are grouped by message, from newest to oldest. Group headings show the message date and time, but cannot be selected.

Each resource has a stable number:

- a file shows its name followed by its full path;
- a link shows a readable label followed by its full URI;
- a code block shows its language and complete contents.

The menu scrolls automatically to keep the selected item visible.

## Normal navigation

| Key | Action |
|---|---|
| `↓` or `J` | Select the next item. |
| `↑` or `K` | Select the previous item. |
| `←` or `H` | Go to the first item in the previous message. |
| `→` or `L` | Go to the first item in the next message. |
| `Enter` | Perform the action associated with the selected item. |
| `Escape` | Close the menu without performing an action. |
| `Ctrl+Alt+L` | Close the menu without performing an action. |

## Selecting an item by number

Type one or more digits to immediately select the item whose number exactly matches the complete sequence.

For example:

- `2` selects item 2, not item 12;
- typing `1`, then `3`, selects item 13.

Numeric input does not filter the list or change the displayed numbers. `Backspace` removes the last digit and immediately reevaluates the remaining sequence. If the sequence becomes empty, the numeric field stays open and the current selection is preserved.

The number `0`, a number that does not exist, or the number of an item hidden by the active filters does not move the selection. The field indicates that the target is unavailable.

Pressing an arrow key or `H`, `J`, `K`, or `L` closes the numeric field before moving the selection. Typing a number never performs an action automatically: you must always press `Enter` to confirm.

## Filtering by resource type

The following filters are available in normal mode:

| Key | Resource type |
|---|---|
| `C` | Code blocks |
| `U` | HTTP(S) links and `mailto:` addresses |
| `F` | Files |

Press the same key again to disable its filter. Multiple filters can be active at the same time; the menu then shows all resources belonging to any selected type. When no type filter is active, all resource types are shown.

Every filter change closes the numeric field and selects the first visible result. The menu remains open when no items match.

## Search

Press `I` in normal mode to enter search mode. The text you type immediately filters the visible resources. Search is case-insensitive.

Search includes:

- file names and full paths;
- link labels and full URIs;
- code block languages and complete contents.

Type filters remain active during search. Entering search mode and every change to the query selects the first visible result.

### Keys in search mode

| Key | Action |
|---|---|
| Printable characters, including digits | Add text to the search query. |
| `Backspace` | Delete the last character. |
| `↑`, `↓`, `←`, `→` | Navigate through the results. |
| `Enter` | Perform the action associated with the selected item. |
| `Escape` | Leave search mode while keeping the menu open. |
| `Ctrl+Alt+L` | Close the menu immediately without performing an action. |

In search mode, `C`, `U`, `F`, `I`, `H`, `J`, `K`, `L`, and digits are entered as text. The arrow keys are therefore the only navigation keys available in this mode.

After leaving search mode with `Escape`, press `Escape` again to close the menu.

## Actions

After you confirm an item with `Enter`:

- a file opens in its associated system application;
- a link opens in its default handler;
- a `mailto:` address is passed to the configured email application;
- a code block is copied exactly to the clipboard, preserving spaces, tabs, and line breaks.

If opening or copying fails, Pi displays an error notification.

## Common workflows

- Open a resource quickly: press `Ctrl+Alt+L`, type its number, then press `Enter`.
- Show only files: press `Ctrl+Alt+L`, then `F`.
- Search for a URL or path: press `Ctrl+Alt+L`, then `I`, and type part of it.
- Copy a code block: open the menu, optionally enable `C`, select the block, then press `Enter`.
- Cancel without performing an action: press `Escape` or `Ctrl+Alt+L`.
