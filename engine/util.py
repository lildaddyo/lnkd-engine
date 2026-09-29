"""Text, name and date helpers. Stdlib only."""
import html
import re
from datetime import date, datetime, timezone

CYR = re.compile(r"[а-яА-ЯёЁ]")

_BG = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
    "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "sht", "ъ": "a", "ь": "y", "ю": "yu", "я": "ya", "ё": "yo",
}


def translit(s):
    return "".join(_BG.get(c, c) for c in s.lower())


def name_key_tokens(name):
    """Phonetically squashed tokens so 'Илиян Райков' ~ 'Ilian Raykov'."""
    s = translit(name or "")
    s = re.sub(r"[^a-z\s-]", " ", s)
    out = []
    for t in re.split(r"[\s-]+", s):
        if len(t) < 2:
            continue
        for a, b in (("kh", "h"), ("iy", "i"), ("y", "i"), ("j", "i"), ("w", "v"),
                     ("ph", "f"), ("tz", "ts"), ("ou", "u"), ("ii", "i")):
            t = t.replace(a, b)
        out.append(t)
    return out


def names_match(a, b):
    ta, tb = name_key_tokens(a), name_key_tokens(b)
    if not ta or not tb:
        return False
    if ta[0] != tb[0]:
        return False
    return bool(set(ta[1:]) & set(tb[1:])) or (len(ta) == 1 or len(tb) == 1)


def first_name(full):
    for tok in re.split(r"[\s,]+", (full or "").strip()):
        clean = re.sub(r"[^\wА-Яа-я'-]", "", tok)
        if len(clean) >= 2 and not clean.isupper() and clean.lower() not in ("dr", "prof", "mr", "mrs", "ms", "professor", "д-р"):
            return clean[0].upper() + clean[1:]
    tok = (full or "").split()
    return tok[0].title() if tok else ""


def is_cyrillic(s):
    s = s or ""
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return False
    return sum(1 for c in letters if CYR.match(c)) / len(letters) > 0.5


def clean_html(t):
    t = re.sub(r"<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def norm_url(u):
    """Canonical key for a LinkedIn member URL: 'linkedin.com/in/<slug>'."""
    u = (u or "").strip().lower()
    m = re.search(r"linkedin\.com/in/([^/?#\s]+)", u)
    if not m:
        return ""
    return "linkedin.com/in/" + m.group(1).rstrip("/")


def full_url(key):
    return "https://www." + key if key else ""


def parse_dt(s):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S UTC", "%Y/%m/%d %H:%M:%S UTC", "%Y-%m-%d %H:%M:%S",
                "%m/%d/%y, %I:%M %p", "%a %b %d %H:%M:%S UTC %Y", "%d %b %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def iso(d):
    return d.isoformat() if d else None


def from_iso(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def today():
    return date.today()


def any_re(words):
    return re.compile("|".join(words), re.I)
