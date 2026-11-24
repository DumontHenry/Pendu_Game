import ctypes
import sys
import unicodedata
from random import choice

import pygame

# ---------------- Configuration ----------------
BASE_W, BASE_H = 900, 600  # repère de conception : tout est mis à l'échelle à partir de là
WINDOW_RATIO = 0.85        # taille de la fenêtre au démarrage (part de l'écran)

CATEGORIES = {
    "Informatique": [
        "CODE", "SCRIPT", "PYTHON", "CLAVIER", "ÉCRAN", "SOURIS", "BOUCLE", "SERVEUR",
        "FICHIER", "RÉSEAU", "LOGICIEL", "TERMINAL", "VARIABLE", "FONCTION", "PROGRAMME",
        "ORDINATEUR", "NAVIGATEUR", "PROCESSEUR", "ALGORITHME", "COMPILATEUR",
        "BIBLIOTHÈQUE", "CYBERSÉCURITÉ",
    ],
    "Data et IA": [
        "AGENT", "FABRIC", "MODÈLE", "RAPPORT", "TABLEAU", "ANALYSE", "FORMULE", "DONNÉES",
        "MÉTRIQUE", "SCHÉMA", "REQUÊTE", "PIPELINE", "ENTREPÔT", "MICROSOFT", "PRÉDICTION",
        "INDICATEUR", "APPRENTISSAGE", "ENTRAÎNEMENT", "VISUALISATION", "CLASSIFICATION",
        "TRANSFORMATION", "INTELLIGENCE",
    ],
    "Géographie": [
        "PARIS", "NAMUR", "LIÈGE", "FRANCE", "ITALIE", "LONDRES", "ESPAGNE", "BELGIQUE",
        "PORTUGAL", "DANEMARK", "ARDENNES", "BRUXELLES", "MARSEILLE", "AMSTERDAM",
        "ALLEMAGNE", "LUXEMBOURG", "STRASBOURG", "MÉDITERRANÉE", "KILIMANDJARO",
    ],
    "Nature": [
        "LOUP", "OCÉAN", "VOLCAN", "RENARD", "FORÊT", "GIRAFE", "RIVIÈRE", "DAUPHIN",
        "MONTAGNE", "ÉCUREUIL", "HÉRISSON", "PAPILLON", "ARAIGNÉE", "TOURNESOL",
        "CROCODILE", "CHAMPIGNON", "HIRONDELLE", "RHINOCÉROS", "ÉLÉPHANT",
    ],
}
ALL_LABEL = "Tout mélangé"
CATEGORY_NAMES = list(CATEGORIES) + [ALL_LABEL]

# max_errors = erreurs autorisées, lengths = longueur des mots (min, max)
DIFFICULTIES = {
    "Facile": {"max_errors": 9, "lengths": (1, 6)},
    "Moyen": {"max_errors": 7, "lengths": (7, 9)},
    "Difficile": {"max_errors": 5, "lengths": (10, 99)},
}
DIFFICULTY_NAMES = list(DIFFICULTIES)
DIFFICULTY_DETAILS = {
    "Facile": "mots courts | 9 erreurs",
    "Moyen": "mots moyens | 7 erreurs",
    "Difficile": "mots longs | 5 erreurs",
}

KEY_ROWS = ["AZERTYUIOP", "QSDFGHJKLM", "WXCVBN"]

# Palette
BG = (238, 241, 246)
CARD = (255, 255, 255)
CARD_BORDER = (214, 220, 229)
SHADOW = (222, 227, 235)
INK = (35, 43, 60)
GREY = (125, 134, 150)
BLUE = (40, 100, 215)
GREEN = (40, 150, 85)
RED = (210, 65, 65)
WOOD = (139, 94, 60)
ROPE = (176, 141, 87)
STAGES = 7  # nombre d'étapes du dessin


# ---------------- Mise à l'échelle ----------------
class View:
    """Convertit les coordonnées 900x600 en pixels réels (ratio conservé, centré)."""

    def __init__(self, surface):
        w, h = surface.get_size()
        self.s = max(0.2, min(w / BASE_W, h / BASE_H))
        self.ox = (w - BASE_W * self.s) / 2
        self.oy = (h - BASE_H * self.s) / 2

    def pt(self, x, y):
        return int(self.ox + x * self.s), int(self.oy + y * self.s)

    def px(self, v):
        return max(1, int(round(v * self.s)))


_fonts = {}


def get_font(px):
    if px not in _fonts:
        _fonts[px] = pygame.font.SysFont(None, px)
    return _fonts[px]


def draw_text(window, view, content, size, color, pos, anchor="topleft", max_width=None):
    px = view.px(size)
    surf = get_font(px).render(content, True, color)
    if max_width:  # réduit la police si le texte dépasse la largeur disponible
        limit = view.px(max_width)
        while surf.get_width() > limit and px > 10:
            px -= 2
            surf = get_font(px).render(content, True, color)
    window.blit(surf, surf.get_rect(**{anchor: view.pt(*pos)}))


def rrect(window, view, color, rect, radius=12, border=0, border_color=None):
    x, y, w, h = rect
    r = pygame.Rect(view.pt(x, y), (view.px(w), view.px(h)))
    pygame.draw.rect(window, color, r, border_radius=view.px(radius))
    if border:
        pygame.draw.rect(window, border_color, r, view.px(border), border_radius=view.px(radius))


def card(window, view, rect, border_color=CARD_BORDER):
    x, y, w, h = rect
    rrect(window, view, SHADOW, (x, y + 4, w, h), 18)
    rrect(window, view, CARD, rect, 18, 2, border_color)


def cap_line(window, view, color, p1, p2, width):
    """Trait épais aux extrémités arrondies."""
    a, b, px = view.pt(*p1), view.pt(*p2), view.px(width)
    pygame.draw.line(window, color, a, b, px)
    if px >= 3:
        pygame.draw.circle(window, color, a, px // 2)
        pygame.draw.circle(window, color, b, px // 2)


# ---------------- Logique ----------------
def strip_accents(text):
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").upper()


def pick_word(category, difficulty, previous=None):
    pool = sum(CATEGORIES.values(), []) if category == ALL_LABEL else CATEGORIES[category]
    lo, hi = DIFFICULTIES[difficulty]["lengths"]
    filtered = [w for w in pool if lo <= len(w) <= hi and w != previous]
    candidates = filtered or [w for w in pool if w != previous]
    word = choice(candidates)
    return word, strip_accents(word)


# ---------------- Dessin ----------------
def draw_gallows(window, view, errors, max_errors, lost):
    """Dessine le pendu progressivement; la dernière erreur complète toujours le dessin."""
    stage = -(-errors * STAGES // max_errors)  # arrondi au supérieur
    figure = INK
    if stage >= 1:
        cap_line(window, view, WOOD, (70, 520), (350, 520), 14)
    if stage >= 2:
        cap_line(window, view, WOOD, (130, 520), (130, 90), 12)
    if stage >= 3:
        cap_line(window, view, WOOD, (130, 90), (300, 90), 12)
        cap_line(window, view, WOOD, (130, 155), (195, 90), 8)
        cap_line(window, view, ROPE, (300, 90), (300, 130), 5)
    if stage >= 4:
        pygame.draw.circle(window, figure, view.pt(300, 160), view.px(30), view.px(5))
        if lost:  # yeux en croix, bouche triste
            for ex in (288, 312):
                cap_line(window, view, RED, (ex - 5, 150), (ex + 5, 160), 3)
                cap_line(window, view, RED, (ex + 5, 150), (ex - 5, 160), 3)
            cap_line(window, view, figure, (288, 177), (300, 170), 3)
            cap_line(window, view, figure, (300, 170), (312, 177), 3)
        else:
            for ex in (288, 312):
                pygame.draw.circle(window, figure, view.pt(ex, 154), view.px(3))
            cap_line(window, view, figure, (289, 172), (311, 172), 3)
    if stage >= 5:
        cap_line(window, view, figure, (300, 190), (300, 310), 5)
    if stage >= 6:
        cap_line(window, view, figure, (300, 225), (262, 285), 5)
        cap_line(window, view, figure, (300, 225), (338, 285), 5)
    if stage >= 7:
        cap_line(window, view, figure, (300, 310), (266, 390), 5)
        cap_line(window, view, figure, (300, 310), (334, 390), 5)


def draw_word(window, view, word, key, guessed, lost):
    n = len(word)
    gap = 8
    w = min(60, (410 - gap * (n - 1)) / n)
    total = n * w + (n - 1) * gap
    x = 665 - total / 2
    size = min(72, w * 1.2)
    for orig, k in zip(word, key):
        revealed = k in guessed
        if revealed or lost:
            color = INK if revealed else RED
            draw_text(window, view, orig, size, color, (x + w / 2, 205), "midbottom")
        cap_line(window, view, INK if revealed else GREY, (x, 218), (x + w, 218), 5)
        x += w + gap


def draw_pips(window, view, errors, max_errors):
    draw_text(window, view, f"Erreurs  {errors} / {max_errors}", 28, GREY, (460, 250))
    for i in range(max_errors):
        c = view.pt(471 + i * 28, 292)
        if i < errors:
            pygame.draw.circle(window, RED, c, view.px(10))
        else:
            pygame.draw.circle(window, GREY, c, view.px(10), view.px(2))


def draw_keyboard(window, view, guessed, wrong):
    kw, kh, gap = 35, 40, 6
    for r, row in enumerate(KEY_ROWS):
        total = len(row) * kw + (len(row) - 1) * gap
        x = 665 - total / 2
        y = 340 + r * (kh + gap)
        for letter in row:
            if letter in guessed:
                fill, border, color = GREEN, GREEN, (255, 255, 255)
            elif letter in wrong:
                fill, border, color = RED, RED, (255, 255, 255)
            else:
                fill, border, color = CARD, CARD_BORDER, INK
            rrect(window, view, fill, (x, y, kw, kh), 8, 2, border)
            draw_text(window, view, letter, 30, color, (x + kw / 2, y + kh / 2), "center")
            x += kw + gap


def menu_input(event, cursor, size):
    """Navigation flèches + ENTRÉE (ou chiffre). Retourne (curseur, validé)."""
    if event.key == pygame.K_UP:
        return (cursor - 1) % size, False
    if event.key == pygame.K_DOWN:
        return (cursor + 1) % size, False
    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return cursor, True
    if event.unicode.isdigit() and 1 <= int(event.unicode) <= size:
        return int(event.unicode) - 1, True
    return cursor, False


def draw_menu(window, view, title, options, details, cursor):
    window.fill(BG)
    draw_text(window, view, "PENDU", 96, INK, (BASE_W // 2, 85), "center")
    cap_line(window, view, BLUE, (BASE_W // 2 - 70, 135), (BASE_W // 2 + 70, 135), 6)
    draw_text(window, view, title, 36, GREY, (BASE_W // 2, 172), "center", max_width=800)
    for i, label in enumerate(options):
        y = 205 + i * 58
        selected = i == cursor
        rrect(window, view, BLUE if selected else CARD, (240, y, 420, 48), 14, 2,
              BLUE if selected else CARD_BORDER)
        text_color = (255, 255, 255) if selected else INK
        draw_text(window, view, f"{i + 1}. {label}", 36, text_color, (262, y + 24), "midleft",
                  max_width=230)
        draw_text(window, view, details[i], 26, (215, 228, 250) if selected else GREY,
                  (638, y + 24), "midright", max_width=170)
    draw_text(window, view, "Flèches + ENTRÉE   |   F11 : plein écran   |   ÉCHAP : quitter",
              26, GREY, (BASE_W // 2, BASE_H - 40), "center", max_width=860)


def screen_size():
    info = pygame.display.Info()
    return info.current_w, info.current_h


def windowed_size():
    """Fenêtre de démarrage : ratio 3:2, WINDOW_RATIO de l'écran."""
    dw, dh = screen_size()
    scale = min(WINDOW_RATIO * dw / BASE_W, WINDOW_RATIO * dh / BASE_H)
    return max(450, int(BASE_W * scale)), max(300, int(BASE_H * scale))


def main():
    if sys.platform == "win32":  # tailles d'écran réelles sur les écrans à mise à l'échelle Windows
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    pygame.init()
    win_size = windowed_size()
    window = pygame.display.set_mode(win_size, pygame.RESIZABLE)
    pygame.display.set_caption("Pendu")
    fullscreen = False
    clock = pygame.time.Clock()

    wins = losses = 0
    state = "menu_category"  # menu_category | menu_difficulty | playing | won | lost
    cursor = 0
    category = difficulty = None
    g = {}  # état de la partie en cours
    category_details = [f"{len(CATEGORIES[c])} mots" for c in CATEGORIES]
    category_details.append(f"{sum(len(v) for v in CATEGORIES.values())} mots")
    difficulty_details = [DIFFICULTY_DETAILS[d] for d in DIFFICULTY_NAMES]

    def start_game(previous=None):
        word, key = pick_word(category, difficulty, previous)
        g.update(word=word, key=key, guessed=set(), wrong=[], penalty=0, hint_used=False,
                 max_errors=DIFFICULTIES[difficulty]["max_errors"])

    def errors():
        return len(g["wrong"]) + g["penalty"]

    def check_end():
        nonlocal state, wins, losses
        if all(c in g["guessed"] for c in g["key"]):
            state, wins = "won", wins + 1
        elif errors() >= g["max_errors"]:
            state, losses = "lost", losses + 1

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if event.type == pygame.VIDEORESIZE and not fullscreen:
                win_size = (max(450, event.w), max(300, event.h))
                window = pygame.display.set_mode(win_size, pygame.RESIZABLE)
                continue
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_F11:
                fullscreen = not fullscreen
                if fullscreen:
                    window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    window = pygame.display.set_mode(win_size, pygame.RESIZABLE)
                    if window.get_size() != win_size:  # certains pilotes gardent la taille plein écran
                        pygame.display.quit()
                        pygame.display.init()
                        window = pygame.display.set_mode(win_size, pygame.RESIZABLE)
                        pygame.display.set_caption("Pendu")
            elif event.key == pygame.K_ESCAPE:
                running = False
            elif state == "menu_category":
                cursor, ok = menu_input(event, cursor, len(CATEGORY_NAMES))
                if ok:
                    category, state, cursor = CATEGORY_NAMES[cursor], "menu_difficulty", 1
            elif state == "menu_difficulty":
                cursor, ok = menu_input(event, cursor, len(DIFFICULTY_NAMES))
                if ok:
                    difficulty = DIFFICULTY_NAMES[cursor]
                    start_game()
                    state = "playing"
            elif state in ("won", "lost"):
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    start_game(g["word"])
                    state = "playing"
                elif event.key == pygame.K_m:
                    state, cursor = "menu_category", 0
            elif state == "playing":
                if event.key == pygame.K_TAB:
                    hidden = [c for c in g["key"] if c not in g["guessed"]]
                    if not g["hint_used"] and hidden and errors() + 1 < g["max_errors"]:
                        g["guessed"].add(choice(hidden))
                        g["hint_used"] = True
                        g["penalty"] = 1
                        check_end()
                    continue
                letter = strip_accents(event.unicode)
                if len(letter) == 1 and "A" <= letter <= "Z":
                    if letter in g["guessed"] or letter in g["wrong"]:
                        continue
                    if letter in g["key"]:
                        g["guessed"].add(letter)
                    else:
                        g["wrong"].append(letter)
                    check_end()

        window = pygame.display.get_surface()
        view = View(window)

        if state == "menu_category":
            draw_menu(window, view, "Choisis une catégorie", CATEGORY_NAMES, category_details, cursor)
        elif state == "menu_difficulty":
            draw_menu(window, view, f"{category} : choisis la difficulté", DIFFICULTY_NAMES,
                      difficulty_details, cursor)
        else:
            lost = state == "lost"
            window.fill(BG)
            border = GREEN if state == "won" else RED if lost else CARD_BORDER
            card(window, view, (30, 30, 400, 540), border)
            draw_gallows(window, view, errors(), g["max_errors"], lost)

            draw_text(window, view, f"{category}  |  {difficulty}", 34, BLUE, (460, 40),
                      max_width=410)
            draw_text(window, view, f"Victoires {wins}   Défaites {losses}", 26, GREY, (460, 80))
            draw_word(window, view, g["word"], g["key"], g["guessed"], lost)
            draw_pips(window, view, errors(), g["max_errors"])
            draw_keyboard(window, view, g["guessed"], set(g["wrong"]))

            if state == "playing":
                hint = "indice utilisé" if g["hint_used"] else "TAB : indice (+1 erreur)"
                draw_text(window, view, hint, 28, GREY, (665, 520), "center", max_width=410)
                draw_text(window, view, "F11 : plein écran   |   ÉCHAP : quitter", 24, GREY,
                          (665, 552), "center", max_width=410)
            else:
                color = GREEN if state == "won" else RED
                rrect(window, view, color, (460, 492, 410, 72), 16)
                draw_text(window, view, "GAGNÉ !" if state == "won" else "PERDU", 44,
                          (255, 255, 255), (665, 517), "center")
                draw_text(window, view, "ENTRÉE : rejouer   |   M : menu", 26, (255, 255, 255),
                          (665, 548), "center", max_width=390)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
