vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.clipboard = "unnamedplus"
vim.opt.linebreak = true
vim.opt.scrolloff = 15

vim.g.mapleader = " "

local memo_lines = {
  "CONSTRUIRE UNE COMMANDE",
  "[opérateur] + [cible]",
  "",
  "OPÉRATEURS",
  "y   copier",
  "d   supprimer",
  "c   modifier (supprime puis passe en insertion)",
  "r + caractère  remplacer un caractère",
  "R   remplacer plusieurs caractères",
  "",
  "CIBLES : MOT",
  "iw  intérieur du mot",
  "aw  mot avec l’espace adjacent",
  "w   jusqu’au mot suivant",
  "b   jusqu’au mot précédent",
  "e   jusqu’à la fin du mot",
  "",
  "CIBLES : LIGNE",
  "yy / dd / cc   ligne entière",
  "0              début absolu de ligne",
  "^              premier caractère non vide",
  "$              fin de ligne",
  "",
  "CIBLES : PHRASE",
  "is  intérieur de la phrase",
  "as  phrase avec l’espace adjacent",
  "",
  "CIBLES : PARAGRAPHE",
  "ip  intérieur du paragraphe",
  "ap  paragraphe avec séparation",
  "",
  "DÉPLACEMENT",
  "h j k l         gauche, bas, haut, droite",
  "gg / G          début / fin du fichier",
  "{ / }           paragraphe précédent / suivant",
  "( / )           phrase précédente / suivante",
  "",
  "INSERTION",
  "i / a           avant / après le curseur",
  "A              fin de ligne",
  "o / O           nouvelle ligne après / avant",
  "",
  "SÉLECTION",
  "v + cible      sélectionner une cible",
  "V              sélectionner une ligne",
  "Ctrl+v         sélectionner un bloc",
  "o              changer l’extrémité active",
  "gv             resélectionner la dernière sélection",
  "",
  "HISTORIQUE ET COLLAGE",
  "u / Ctrl+r      annuler / refaire",
  "p / P           coller après / avant",
}

local function show_memo()
  local buffer = vim.api.nvim_create_buf(false, true)
  vim.bo[buffer].bufhidden = "wipe"
  vim.api.nvim_buf_set_lines(buffer, 0, -1, false, memo_lines)

  local width = math.min(60, vim.o.columns - 4)
  local window = vim.api.nvim_open_win(buffer, true, {
    relative = "editor",
    width = width,
    height = #memo_lines,
    row = math.max(0, math.floor((vim.o.lines - #memo_lines) / 2)),
    col = math.max(0, math.floor((vim.o.columns - width) / 2)),
    style = "minimal",
    border = "rounded",
    title = " Mémo Neovim ",
    title_pos = "center",
  })

  local function close_memo()
    if vim.api.nvim_win_is_valid(window) then
      vim.api.nvim_win_close(window, true)
    end
  end

  vim.keymap.set("n", "q", close_memo, { buffer = buffer, nowait = true })
  vim.keymap.set("n", "<Esc>", close_memo, { buffer = buffer, nowait = true })
end

vim.keymap.set("n", "<leader>?", show_memo, { desc = "Afficher le mémo Neovim" })
