import os
import re
import sqlite3
import asyncio
import calendar
from datetime import datetime, date, timedelta, timezone

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# ASOSIY SOZLAMALAR
# =========================================================

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN topilmadi.")

DATA_DIR = os.environ.get("DATA_DIR", ".")

os.makedirs(
    DATA_DIR,
    exist_ok=True,
)

DB_PATH = os.path.join(
    DATA_DIR,
    "hisobliy.db",
)

TASHKENT_TZ = timezone(
    timedelta(hours=5)
)


def tashkent_now():
    return datetime.now(
        TASHKENT_TZ
    )


def tashkent_today():
    return tashkent_now().date()


# =========================================================
# MENYULAR
# =========================================================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [
            "💰 Balans",
            "🎯 Budjet",
        ],
        [
            "📊 Bugungi hisobot",
            "📅 Oylik hisobot",
        ],
        [
            "💳 Qarzlar",
            "🧾 Tarix",
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

BALANCE_MENU = ReplyKeyboardMarkup(
    [
        [
            "♻️ Yangi hisob boshlash",
        ],
        [
            "⬅️ Asosiy menyu",
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

DEBT_MENU = ReplyKeyboardMarkup(
    [
        [
            "➕ Menga qarz",
            "➖ Men qarzdorman",
        ],
        [
            "📋 Qarzlar ro'yxati",
            "💸 Qisman to'lov",
        ],
        [
            "✅ To'liq yopildi",
            "⚠️ Muddatli qarzlar",
        ],
        [
            "⬅️ Asosiy menyu",
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

HISTORY_MENU = ReplyKeyboardMarkup(
    [
        [
            "🧾 Oxirgi 10 ta",
            "🔎 Qidirish / filtr",
        ],
        [
            "⬅️ Asosiy menyu",
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

OPERATIONS_MENU = ReplyKeyboardMarkup(
    [
        [
            "✏️ Operatsiyani tahrirlash",
            "🗑 Operatsiyani o'chirish",
        ],
        [
            "⬅️ Asosiy menyu",
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

BUDGET_MENU = ReplyKeyboardMarkup(
    [
        [
            "➕ Budjet qo'shish",
            "📊 Budjet holati",
        ],
        [
            "🗑 Budjetni o'chirish",
        ],
        [
            "⬅️ Asosiy menyu",
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

RECURRING_MENU = ReplyKeyboardMarkup(
    [
        [
            "➕ Doimiy xarajat",
            "➕ Doimiy daromad",
        ],
        [
            "📋 Doimiy to'lovlar",
            "🗑 Doimiy to'lovni o'chirish",
        ],
        [
            "⬅️ Asosiy menyu",
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

CATEGORY_MENU = ReplyKeyboardMarkup(
    [
        [
            "➕ Kategoriya qo'shish",
            "📋 Kategoriyalar",
        ],
        [
            "🗑 Kategoriya o'chirish",
        ],
        [
            "⬅️ Asosiy menyu",
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

SETTINGS_MENU = ReplyKeyboardMarkup(
    [
        [
            "🗑 Barcha ma'lumotlarni tozalash",
        ],
        [
            "⬅️ Asosiy menyu",
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

CLEAR_CONFIRM_MENU = ReplyKeyboardMarkup(
    [
        [
            "✅ Ha, tozalash",
            "❌ Yo'q",
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

RESET_ACCOUNT_CONFIRM_MENU = ReplyKeyboardMarkup(
    [
        [
            "✅ Ha, 0 dan boshlash",
            "❌ Bekor qilish",
        ],
    ],
    resize_keyboard=True,
    is_persistent=True,
)


# =========================================================
# SO'ZLAR VA KATEGORIYALAR
# =========================================================

INCOME_WORDS = [
    "oylik",
    "oyilik",
    "maosh",
    "daromad",
    "kirim",
    "tushum",
    "tushdi",
    "bonus",
    "foyda",
    "stipendiya",
    "cashback",
]

CATEGORY_WORDS = {
    "oylik": [
        "oylik",
        "oyilik",
        "maosh",
    ],

    "bonus": [
        "bonus",
        "mukofot",
    ],

    "reklama": [
        "reklama",
        "ads",
        "target",
        "targeting",
        "promo",
        "promotion",
    ],

    "ovqat": [
        "ovqat",
        "tushlik",
        "nonushta",
        "restoran",
        "kafe",
        "fastfood",
        "burger",
        "pizza",
        "osh",
        "lavash",
        "market",
        "bozor",
        "non",
    ],

    "transport": [
        "taksi",
        "taxi",
        "benzin",
        "avtobus",
        "metro",
        "transport",
        "yo'l",
        "mashina",
    ],

    "kommunal": [
        "svet",
        "elektr",
        "gaz",
        "suv",
        "kommunal",
        "internet",
    ],

    "salomatlik": [
        "dori",
        "apteka",
        "shifokor",
        "doktor",
        "kasalxona",
    ],

    "kiyim": [
        "kiyim",
        "kurtka",
        "shim",
        "futbolka",
        "oyoq kiyim",
        "krossovka",
    ],

    "telefon": [
        "telefon",
        "aloqa",
        "mobil",
        "sim karta",
    ],

    "uy": [
        "uy",
        "ijara",
        "remont",
        "mebel",
    ],

    "ko'ngilochar": [
        "kino",
        "o'yin",
        "game",
        "sayr",
    ],
}

MONTH_WORDS = {
    "yanvar": 1,
    "fevral": 2,
    "mart": 3,
    "aprel": 4,
    "may": 5,
    "iyun": 6,
    "iyul": 7,
    "avgust": 8,
    "sentabr": 9,
    "sentyabr": 9,
    "oktabr": 10,
    "noyabr": 11,
    "dekabr": 12,
}

AMOUNT_WITH_UNIT_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*"
    r"(ming|mingta|k|"
    r"mln|miln|million|milion|millon|"
    r"milyon|miliyon|milyion|"
    r"milliard|miliard|milyard|milard|mlrd)\b",
    re.IGNORECASE,
)


# =========================================================
# YORDAMCHI FUNKSIYALAR
# =========================================================

def db():
    return sqlite3.connect(
        DB_PATH,
        timeout=30,
    )


def now_str():
    return tashkent_now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def current_month_str():
    return tashkent_now().strftime(
        "%Y-%m"
    )


def previous_month_str():
    first_day = tashkent_today().replace(
        day=1
    )

    previous_last_day = (
        first_day
        - timedelta(days=1)
    )

    return previous_last_day.strftime(
        "%Y-%m"
    )


def normalize_text(text):
    text = text.lower()

    for symbol in [
        "’",
        "‘",
        "ʼ",
        "`",
        "´",
    ]:
        text = text.replace(
            symbol,
            "'",
        )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def clean_person(person):
    person = normalize_text(
        person
    )

    person = re.sub(
        r"^(aka|opa|uka|amaki|xola)\s+",
        "",
        person,
    )

    return person.strip(
        " ,.-:"
    ).title()


def format_due_date(
    due_date
):
    if not due_date:
        return (
            "Muddat belgilanmagan"
        )

    try:
        return datetime.strptime(
            due_date,
            "%Y-%m-%d",
        ).strftime(
            "%d.%m.%Y"
        )

    except ValueError:
        return due_date


def parse_due_date(text):
    text = normalize_text(
        text
    )

    today = tashkent_today()

    if "ertaga" in text:
        return (
            today
            + timedelta(days=1)
        ).isoformat()

    if "bugun" in text:
        return today.isoformat()

    match = re.search(
        r"\b(\d{1,2})[./-]"
        r"(\d{1,2})[./-]"
        r"(\d{4})\b",
        text,
    )

    if match:
        try:
            return date(
                int(match.group(3)),
                int(match.group(2)),
                int(match.group(1)),
            ).isoformat()

        except ValueError:
            return None

    match = re.search(
        r"\b(\d{4})-"
        r"(\d{1,2})-"
        r"(\d{1,2})\b",
        text,
    )

    if match:
        try:
            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            ).isoformat()

        except ValueError:
            return None

    return None


def parse_transaction_date(
    text
):
    text = normalize_text(
        text
    )

    today = tashkent_today()

    if (
        "avvalgi kun" in text
        or "kechadan oldin" in text
        or "ikki kun oldin" in text
    ):
        return (
            today
            - timedelta(days=2)
        )

    if "kecha" in text:
        return (
            today
            - timedelta(days=1)
        )

    if "bugun" in text:
        return today

    match = re.search(
        r"\b(\d{1,2})[./-]"
        r"(\d{1,2})[./-]"
        r"(\d{4})\b",
        text,
    )

    if match:
        try:
            return date(
                int(match.group(3)),
                int(match.group(2)),
                int(match.group(1)),
            )

        except ValueError:
            return None

    return None


def created_at_from_text(
    text
):
    transaction_date = (
        parse_transaction_date(
            text
        )
    )

    if transaction_date is None:
        return now_str()

    current_time = (
        tashkent_now().strftime(
            "%H:%M:%S"
        )
    )

    return (
        f"{transaction_date.isoformat()} "
        f"{current_time}"
    )


def remove_date_words(
    text
):
    text = normalize_text(
        text
    )

    for phrase in [
        "kechadan oldin",
        "ikki kun oldin",
        "avvalgi kun",
        "bugun",
        "kecha",
    ]:
        text = text.replace(
            phrase,
            " ",
        )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip(
        " ,.-:"
    )


# =========================================================
# SUMMANI TUSHUNISH
# =========================================================

def parse_amount(text):
    text = normalize_text(
        text
    )

    match = AMOUNT_WITH_UNIT_RE.search(
        text
    )

    if match:
        number = float(
            match.group(1).replace(
                ",",
                ".",
            )
        )

        unit = (
            match.group(2).lower()
        )

        if unit in [
            "ming",
            "mingta",
            "k",
        ]:
            return int(
                number * 1_000
            )

        if unit in [
            "mln",
            "miln",
            "million",
            "milion",
            "millon",
            "milyon",
            "miliyon",
            "milyion",
        ]:
            return int(
                number * 1_000_000
            )

        return int(
            number * 1_000_000_000
        )

    match = re.search(
        r"\d[\d\s.,]*",
        text,
    )

    if not match:
        return None

    digits = re.sub(
        r"\D",
        "",
        match.group(0),
    )

    if not digits:
        return None

    return int(
        digits
    )


def find_amount_span(
    text
):
    normalized = normalize_text(
        text
    )

    match = AMOUNT_WITH_UNIT_RE.search(
        normalized
    )

    if match:
        return (
            match.start(),
            match.end(),
            parse_amount(
                match.group(0)
            ),
        )

    match = re.search(
        r"\b(?:"
        r"\d{1,3}"
        r"(?:[\s.,]\d{3})+"
        r"|\d+)\b",
        normalized,
    )

    if match:
        return (
            match.start(),
            match.end(),
            parse_amount(
                match.group(0)
            ),
        )

    return None


def parse_month_from_text(
    text
):
    text = normalize_text(
        text
    )

    today = tashkent_today()

    if (
        "bu oy" in text
        or "shu oy" in text
    ):
        return today.strftime(
            "%Y-%m"
        )

    if (
        "o'tgan oy" in text
        or "otgan oy" in text
    ):
        return previous_month_str()

    for (
        word,
        month_number,
    ) in MONTH_WORDS.items():

        if word in text:
            return (
                f"{today.year:04d}-"
                f"{month_number:02d}"
            )

    return None


# =========================================================
# DATABASE VA MIGRATSIYA
# =========================================================

def table_columns(
    conn,
    table,
):
    return {
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    }


def ensure_column(
    conn,
    table,
    column_name,
    definition,
):
    columns = table_columns(
        conn,
        table,
    )

    if column_name not in columns:
        conn.execute(
            f"ALTER TABLE {table} "
            f"ADD COLUMN {column_name} "
            f"{definition}"
        )


def init_db():
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS incomes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER, "
        "amount INTEGER, "
        "category TEXT, "
        "created_at TEXT, "
        "source TEXT DEFAULT 'manual', "
        "reference_id INTEGER"
        ")"
    )

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS expenses ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER, "
        "amount INTEGER, "
        "category TEXT, "
        "created_at TEXT, "
        "source TEXT DEFAULT 'manual', "
        "reference_id INTEGER"
        ")"
    )

    ensure_column(
        conn,
        "incomes",
        "source",
        "TEXT DEFAULT 'manual'",
    )

    ensure_column(
        conn,
        "incomes",
        "reference_id",
        "INTEGER",
    )

    ensure_column(
        conn,
        "expenses",
        "source",
        "TEXT DEFAULT 'manual'",
    )

    ensure_column(
        conn,
        "expenses",
        "reference_id",
        "INTEGER",
    )

    cursor.execute(
        "UPDATE incomes "
        "SET source = 'manual' "
        "WHERE source IS NULL "
        "OR source = ''"
    )

    cursor.execute(
        "UPDATE expenses "
        "SET source = 'manual' "
        "WHERE source IS NULL "
        "OR source = ''"
    )

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS debts ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER, "
        "person TEXT, "
        "amount INTEGER, "
        "original_amount INTEGER, "
        "created_at TEXT, "
        "debt_type TEXT DEFAULT 'receivable', "
        "status TEXT DEFAULT 'active', "
        "due_date TEXT, "
        "last_reminder_date TEXT, "
        "closed_at TEXT"
        ")"
    )

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS debt_payments ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER, "
        "debt_id INTEGER, "
        "amount INTEGER, "
        "created_at TEXT"
        ")"
    )

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS budgets ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER, "
        "month TEXT, "
        "category TEXT, "
        "amount INTEGER"
        ")"
    )

    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "idx_budget_unique "
        "ON budgets("
        "user_id, month, category"
        ")"
    )

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS "
        "custom_categories ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER, "
        "name TEXT, "
        "created_at TEXT"
        ")"
    )

    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "idx_category_unique "
        "ON custom_categories("
        "user_id, name"
        ")"
    )

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS recurring ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER, "
        "title TEXT, "
        "amount INTEGER, "
        "category TEXT, "
        "entry_type TEXT, "
        "day_of_month INTEGER, "
        "mode TEXT, "
        "active INTEGER DEFAULT 1, "
        "last_run_month TEXT, "
        "created_at TEXT"
        ")"
    )

    conn.commit()
    conn.close()


# =========================================================
# KATEGORIYALAR
# =========================================================

def get_custom_categories(
    user_id
):
    conn = db()

    rows = conn.execute(
        "SELECT id, name "
        "FROM custom_categories "
        "WHERE user_id = ? "
        "ORDER BY name",
        (
            user_id,
        ),
    ).fetchall()

    conn.close()

    return rows


def add_custom_category(
    user_id,
    name,
):
    name = name.strip().title()

    if (
        not name
        or len(name) > 30
    ):
        return (
            False,
            "invalid",
        )

    conn = db()

    try:
        conn.execute(
            "INSERT INTO custom_categories "
            "(user_id, name, created_at) "
            "VALUES (?, ?, ?)",
            (
                user_id,
                name,
                now_str(),
            ),
        )

        conn.commit()

        result = (
            True,
            name,
        )

    except sqlite3.IntegrityError:
        result = (
            False,
            "duplicate",
        )

    finally:
        conn.close()

    return result


def delete_custom_category(
    user_id,
    category_id,
):
    conn = db()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT name "
        "FROM custom_categories "
        "WHERE id = ? "
        "AND user_id = ?",
        (
            category_id,
            user_id,
        ),
    ).fetchone()

    if not row:
        conn.close()
        return None

    cursor.execute(
        "DELETE FROM custom_categories "
        "WHERE id = ? "
        "AND user_id = ?",
        (
            category_id,
            user_id,
        ),
    )

    conn.commit()
    conn.close()

    return row[0]


def detect_category(
    text,
    user_id=None,
):
    text = normalize_text(
        text
    )

    if user_id is not None:

        for (
            _,
            name,
        ) in get_custom_categories(
            user_id
        ):

            if normalize_text(
                name
            ) in text:
                return name

    for (
        category,
        words,
    ) in CATEGORY_WORDS.items():

        if any(
            word in text
            for word in words
        ):
            return category

    return "boshqa"


def category_from_label(
    user_id,
    text,
):
    clean = normalize_text(
        text
    )

    for category in CATEGORY_WORDS:

        if clean == normalize_text(
            category
        ):
            return category

    for (
        _,
        name,
    ) in get_custom_categories(
        user_id
    ):

        if clean == normalize_text(
            name
        ):
            return name

    if clean == "boshqa":
        return "boshqa"

    return None


def is_income_text(
    text
):
    text = normalize_text(
        text
    )

    if text.startswith("+"):
        return True

    if text.startswith("-"):
        return False

    expense_phrases = [
        "sarfladim",
        "ishlatdim",
        "to'ladim",
        "tuladim",
        "berdim",
        "ketdi",
        "xarajat",
        "chiqim",
        "sotib oldim",
        "xarid qildim",
    ]

    if any(
        phrase in text
        for phrase in expense_phrases
    ):
        return False

    income_phrases = [
        "tushdi",
        "kelib tushdi",
        "qabul qildim",
        "daromad",
        "kirim",
        "tushum",
        "maosh",
        "oylik",
        "oyilik",
        "bonus",
        "foyda",
        "stipendiya",
        "cashback",
    ]

    if any(
        phrase in text
        for phrase in income_phrases
    ):
        return True

    if "oldim" in text:

        income_hints = [
            "pul",
            "maosh",
            "oylik",
            "oyilik",
            "bonus",
            "foyda",
            "stipendiya",
            "cashback",
            "daromad",
        ]

        return any(
            hint in text
            for hint in income_hints
        )

    return any(
        word in text
        for word in INCOME_WORDS
    )


# =========================================================
# KIRIM / CHIQIM
# =========================================================

def add_income(
    user_id,
    amount,
    category,
    source="manual",
    reference_id=None,
    created_at=None,
):
    conn = db()

    conn.execute(
        "INSERT INTO incomes "
        "(user_id, amount, category, "
        "created_at, source, reference_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            user_id,
            amount,
            category,
            created_at or now_str(),
            source,
            reference_id,
        ),
    )

    conn.commit()
    conn.close()


def add_expense(
    user_id,
    amount,
    category,
    source="manual",
    reference_id=None,
    created_at=None,
):
    conn = db()

    conn.execute(
        "INSERT INTO expenses "
        "(user_id, amount, category, "
        "created_at, source, reference_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            user_id,
            amount,
            category,
            created_at or now_str(),
            source,
            reference_id,
        ),
    )

    conn.commit()
    conn.close()


# =========================================================
# BIR XABARDA BIR NECHTA OPERATSIYA
# =========================================================

def parse_multi_transactions(
    text,
    user_id,
):
    normalized = normalize_text(
        text
    )

    amount_matches = list(
        AMOUNT_WITH_UNIT_RE.finditer(
            normalized
        )
    )

    if len(
        amount_matches
    ) < 2:
        return None

    parts = re.split(
        r"\s*(?:"
        r","
        r"|;"
        r"|\n"
        r"|\s+va\s+"
        r"|\s+hamda\s+"
        r")\s*",
        normalized,
    )

    parts = [
        part.strip(
            " ,.-:"
        )
        for part in parts
        if part.strip(
            " ,.-:"
        )
    ]

    amount_parts = [
        part
        for part in parts
        if AMOUNT_WITH_UNIT_RE.search(
            part
        )
    ]

    if len(
        amount_parts
    ) < 2:
        return None

    common_created_at = (
        created_at_from_text(
            text
        )
    )

    operations = []

    for part in amount_parts:

        amount = parse_amount(
            part
        )

        if (
            amount is None
            or amount <= 0
        ):
            return None

        category = detect_category(
            part,
            user_id,
        )

        entry_type = (
            "income"
            if is_income_text(
                part
            )
            else "expense"
        )

        operations.append(
            {
                "amount": amount,
                "category": category,
                "entry_type": entry_type,
                "created_at": common_created_at,
                "raw": part,
            }
        )

    if len(
        operations
    ) < 2:
        return None

    return operations


def save_multi_transactions(
    user_id,
    operations,
):
    total_income = 0
    total_expense = 0

    saved = []

    for operation in operations:

        amount = operation[
            "amount"
        ]

        category = operation[
            "category"
        ]

        created_at = operation[
            "created_at"
        ]

        entry_type = operation[
            "entry_type"
        ]

        if entry_type == "income":

            add_income(
                user_id,
                amount,
                category,
                created_at=created_at,
            )

            total_income += amount

            icon = "🟢"
            sign = "+"

        else:

            add_expense(
                user_id,
                amount,
                category,
                created_at=created_at,
            )

            total_expense += amount

            icon = "🔴"
            sign = "-"

        saved.append(
            f"{icon} "
            f"{sign}{amount:,} so'm "
            f"— {category}"
        )

    return (
        saved,
        total_income,
        total_expense,
    )


# =========================================================
# BALANS VA HISOBOT
# =========================================================

def get_balance(
    user_id
):
    conn = db()

    income = conn.execute(
        "SELECT COALESCE("
        "SUM(amount), 0"
        ") "
        "FROM incomes "
        "WHERE user_id = ?",
        (
            user_id,
        ),
    ).fetchone()[0]

    expense = conn.execute(
        "SELECT COALESCE("
        "SUM(amount), 0"
        ") "
        "FROM expenses "
        "WHERE user_id = ?",
        (
            user_id,
        ),
    ).fetchone()[0]

    conn.close()

    return (
        income,
        expense,
        income - expense,
    )


def get_today_expenses(
    user_id
):
    today = tashkent_now().strftime(
        "%Y-%m-%d"
    )

    conn = db()

    rows = conn.execute(
        "SELECT category, "
        "SUM(amount) "
        "FROM expenses "
        "WHERE user_id = ? "
        "AND created_at LIKE ? "
        "GROUP BY category "
        "ORDER BY SUM(amount) DESC",
        (
            user_id,
            today + "%",
        ),
    ).fetchall()

    conn.close()

    return rows


def get_month_totals(
    user_id,
    month,
):
    conn = db()

    income = conn.execute(
        "SELECT COALESCE("
        "SUM(amount), 0"
        ") "
        "FROM incomes "
        "WHERE user_id = ? "
        "AND created_at LIKE ?",
        (
            user_id,
            month + "%",
        ),
    ).fetchone()[0]

    expense = conn.execute(
        "SELECT COALESCE("
        "SUM(amount), 0"
        ") "
        "FROM expenses "
        "WHERE user_id = ? "
        "AND created_at LIKE ?",
        (
            user_id,
            month + "%",
        ),
    ).fetchone()[0]

    conn.close()

    return (
        income,
        expense,
        income - expense,
    )


def get_month_report(
    user_id
):
    return get_month_totals(
        user_id,
        current_month_str(),
    )


# =========================================================
# TARIX VA AMALLAR
# =========================================================

def get_recent_operations(
    user_id,
    limit=10,
):
    conn = db()

    rows = conn.execute(
        "SELECT "
        "op_type, id, amount, "
        "category, created_at, source "
        "FROM ("
        "SELECT "
        "'I' AS op_type, "
        "id, amount, category, "
        "created_at, source "
        "FROM incomes "
        "WHERE user_id = ? "
        "UNION ALL "
        "SELECT "
        "'E' AS op_type, "
        "id, amount, category, "
        "created_at, source "
        "FROM expenses "
        "WHERE user_id = ?"
        ") "
        "ORDER BY created_at DESC, "
        "id DESC "
        "LIMIT ?",
        (
            user_id,
            user_id,
            limit,
        ),
    ).fetchall()

    conn.close()

    return rows


def parse_operation_id(
    text
):
    match = re.fullmatch(
        r"\s*([IEie])#?(\d+)\s*",
        text,
    )

    if not match:
        return None

    return (
        match.group(1).upper(),
        int(match.group(2)),
    )


def get_operation(
    user_id,
    op_type,
    op_id,
):
    table = (
        "incomes"
        if op_type.upper() == "I"
        else "expenses"
    )

    conn = db()

    row = conn.execute(
        f"SELECT "
        f"id, amount, category, "
        f"created_at, source "
        f"FROM {table} "
        f"WHERE id = ? "
        f"AND user_id = ?",
        (
            op_id,
            user_id,
        ),
    ).fetchone()

    conn.close()

    return row


def edit_operation(
    user_id,
    op_type,
    op_id,
    new_amount,
    new_category=None,
):
    table = (
        "incomes"
        if op_type.upper() == "I"
        else "expenses"
    )

    conn = db()
    cursor = conn.cursor()

    row = cursor.execute(
        f"SELECT amount, "
        f"category, source "
        f"FROM {table} "
        f"WHERE id = ? "
        f"AND user_id = ?",
        (
            op_id,
            user_id,
        ),
    ).fetchone()

    if not row:
        conn.close()
        return None

    if row[2] == "debt":
        conn.close()
        return "protected"

    category = (
        new_category
        if new_category
        else row[1]
    )

    cursor.execute(
        f"UPDATE {table} "
        f"SET amount = ?, "
        f"category = ? "
        f"WHERE id = ? "
        f"AND user_id = ?",
        (
            new_amount,
            category,
            op_id,
            user_id,
        ),
    )

    conn.commit()
    conn.close()

    return (
        new_amount,
        category,
    )


def delete_operation(
    user_id,
    op_type,
    op_id,
):
    table = (
        "incomes"
        if op_type.upper() == "I"
        else "expenses"
    )

    conn = db()
    cursor = conn.cursor()

    row = cursor.execute(
        f"SELECT amount, "
        f"category, source "
        f"FROM {table} "
        f"WHERE id = ? "
        f"AND user_id = ?",
        (
            op_id,
            user_id,
        ),
    ).fetchone()

    if not row:
        conn.close()
        return None

    if row[2] == "debt":
        conn.close()
        return "protected"

    cursor.execute(
        f"DELETE FROM {table} "
        f"WHERE id = ? "
        f"AND user_id = ?",
        (
            op_id,
            user_id,
        ),
    )

    conn.commit()
    conn.close()

    return (
        row[0],
        row[1],
    )


def delete_last_operation(
    user_id
):
    rows = get_recent_operations(
        user_id,
        1,
    )

    if not rows:
        return None

    (
        op_type,
        op_id,
        amount,
        category,
        created_at,
        source,
    ) = rows[0]

    if source == "debt":
        return "protected"

    return (
        op_type,
        op_id,
        delete_operation(
            user_id,
            op_type,
            op_id,
        ),
    )


# =========================================================
# BUDJET
# =========================================================

def set_budget(
    user_id,
    category,
    amount,
):
    month = current_month_str()

    conn = db()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT id "
        "FROM budgets "
        "WHERE user_id = ? "
        "AND month = ? "
        "AND category = ?",
        (
            user_id,
            month,
            category,
        ),
    ).fetchone()

    if row:

        cursor.execute(
            "UPDATE budgets "
            "SET amount = ? "
            "WHERE id = ?",
            (
                amount,
                row[0],
            ),
        )

        budget_id = row[0]

    else:

        cursor.execute(
            "INSERT INTO budgets "
            "(user_id, month, "
            "category, amount) "
            "VALUES (?, ?, ?, ?)",
            (
                user_id,
                month,
                category,
                amount,
            ),
        )

        budget_id = (
            cursor.lastrowid
        )

    conn.commit()
    conn.close()

    return budget_id


def get_budgets(
    user_id
):
    conn = db()

    rows = conn.execute(
        "SELECT id, category, amount "
        "FROM budgets "
        "WHERE user_id = ? "
        "AND month = ? "
        "ORDER BY category",
        (
            user_id,
            current_month_str(),
        ),
    ).fetchall()

    conn.close()

    return rows


def delete_budget(
    user_id,
    budget_id,
):
    conn = db()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT category "
        "FROM budgets "
        "WHERE id = ? "
        "AND user_id = ?",
        (
            budget_id,
            user_id,
        ),
    ).fetchone()

    if not row:
        conn.close()
        return None

    cursor.execute(
        "DELETE FROM budgets "
        "WHERE id = ? "
        "AND user_id = ?",
        (
            budget_id,
            user_id,
        ),
    )

    conn.commit()
    conn.close()

    return row[0]


def get_category_spent(
    user_id,
    category,
):
    conn = db()

    amount = conn.execute(
        "SELECT COALESCE("
        "SUM(amount), 0"
        ") "
        "FROM expenses "
        "WHERE user_id = ? "
        "AND category = ? "
        "AND created_at LIKE ?",
        (
            user_id,
            category,
            current_month_str()
            + "%",
        ),
    ).fetchone()[0]

    conn.close()

    return amount


def get_budget_for_category(
    user_id,
    category,
):
    conn = db()

    row = conn.execute(
        "SELECT id, amount "
        "FROM budgets "
        "WHERE user_id = ? "
        "AND month = ? "
        "AND category = ?",
        (
            user_id,
            current_month_str(),
            category,
        ),
    ).fetchone()

    conn.close()

    return row


def budget_status_text(
    user_id
):
    rows = get_budgets(
        user_id
    )

    if not rows:
        return None

    text = (
        "🎯 BU OYGI BUDJET\n\n"
    )

    for (
        budget_id,
        category,
        limit_amount,
    ) in rows:

        spent = get_category_spent(
            user_id,
            category,
        )

        remaining = (
            limit_amount
            - spent
        )

        percent = (
            spent
            / limit_amount
            * 100
            if limit_amount
            else 0
        )

        if remaining >= 0:

            status = (
                f"✅ Qoldi: "
                f"{remaining:,} so'm"
            )

        else:

            status = (
                f"⚠️ Oshib ketdi: "
                f"{abs(remaining):,} so'm"
            )

        text += (
            f"#{budget_id} "
            f"📂 {category}\n"
            f"🎯 Limit: "
            f"{limit_amount:,} so'm\n"
            f"💸 Sarflandi: "
            f"{spent:,} so'm "
            f"({percent:.0f}%)\n"
            f"{status}\n\n"
        )

    return text


# =========================================================
# DOIMIY TO'LOVLAR
# =========================================================

def add_recurring(
    user_id,
    title,
    amount,
    category,
    entry_type,
    day_of_month,
    mode,
):
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO recurring "
        "(user_id, title, amount, "
        "category, entry_type, "
        "day_of_month, mode, active, "
        "last_run_month, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, "
        "1, NULL, ?)",
        (
            user_id,
            title,
            amount,
            category,
            entry_type,
            day_of_month,
            mode,
            now_str(),
        ),
    )

    recurring_id = (
        cursor.lastrowid
    )

    conn.commit()
    conn.close()

    return recurring_id


def get_recurring(
    user_id
):
    conn = db()

    rows = conn.execute(
        "SELECT id, title, amount, "
        "category, entry_type, "
        "day_of_month, mode "
        "FROM recurring "
        "WHERE user_id = ? "
        "AND active = 1 "
        "ORDER BY day_of_month, id",
        (
            user_id,
        ),
    ).fetchall()

    conn.close()

    return rows


def delete_recurring(
    user_id,
    recurring_id,
):
    conn = db()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT title "
        "FROM recurring "
        "WHERE id = ? "
        "AND user_id = ? "
        "AND active = 1",
        (
            recurring_id,
            user_id,
        ),
    ).fetchone()

    if not row:
        conn.close()
        return None

    cursor.execute(
        "UPDATE recurring "
        "SET active = 0 "
        "WHERE id = ? "
        "AND user_id = ?",
        (
            recurring_id,
            user_id,
        ),
    )

    conn.commit()
    conn.close()

    return row[0]


def parse_recurring_input(
    text,
    user_id,
    entry_type,
):
    normalized = normalize_text(
        text
    )

    span = find_amount_span(
        normalized
    )

    if not span:
        return None

    (
        start,
        end,
        amount,
    ) = span

    title = normalized[
        :start
    ].strip(
        " ,.-:"
    )

    tail = normalized[
        end:
    ].strip()

    match = re.fullmatch(
        r"(\d{1,2})\s+"
        r"(eslatma|avto|avtomatik)",
        tail,
    )

    if not match:
        return None

    day = int(
        match.group(1)
    )

    if (
        day < 1
        or day > 31
        or not title
    ):
        return None

    recurring_mode = (
        "auto"
        if match.group(2)
        in [
            "avto",
            "avtomatik",
        ]
        else "reminder"
    )

    category = detect_category(
        title,
        user_id,
    )

    return (
        title.title(),
        amount,
        category,
        entry_type,
        day,
        recurring_mode,
    )


# =========================================================
# QARZLAR
# =========================================================

def add_debt(
    user_id,
    person,
    amount,
    debt_type,
    due_date=None,
):
    conn = db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO debts "
        "(user_id, person, amount, "
        "original_amount, created_at, "
        "debt_type, status, due_date) "
        "VALUES (?, ?, ?, ?, ?, ?, "
        "'active', ?)",
        (
            user_id,
            person,
            amount,
            amount,
            now_str(),
            debt_type,
            due_date,
        ),
    )

    debt_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return debt_id


def parse_simple_debt_input(
    text
):
    amount = parse_amount(
        text
    )

    if amount is None:
        return (
            None,
            None,
            None,
        )

    match = re.search(
        r"\d",
        text,
    )

    if not match:
        return (
            None,
            None,
            None,
        )

    person = clean_person(
        text[
            :match.start()
        ]
    )

    if not person:
        return (
            None,
            None,
            None,
        )

    return (
        person,
        amount,
        parse_due_date(
            text
        ),
    )


def detect_natural_debt(
    text
):
    text = normalize_text(
        text
    )

    amount = parse_amount(
        text
    )

    if amount is None:
        return None

    due_date = parse_due_date(
        text
    )

    patterns = [
        (
            r"^(?P<person>.+?)\s+menga\s+.*"
            r"(?:qarz|qarzdor|berishi kerak|"
            r"qaytarishi kerak)\b",
            "receivable",
        ),

        (
            r"^(?P<person>.+?)\s+menda\s+.*"
            r"(?:qarz|qarzdor)\b",
            "receivable",
        ),

        (
            r"^(?P<person>.+?)\s+mendan\s+.*"
            r"(?:qarz|olgan|oldi|"
            r"olib ketgan)\b",
            "receivable",
        ),

        (
            r"^men\s+"
            r"(?P<person>.+?)\s*dan\s+.*"
            r"(?:qarzman|qarzdorman|"
            r"qarz\s+oldim|"
            r"qarz\s+olganman|"
            r"oldim|olganman)\b",
            "payable",
        ),

        (
            r"^men\s+"
            r"(?P<person>.+?)"
            r"(?:ga|ka|qa)\s+.*"
            r"(?:qarzman|qarzdorman|"
            r"berishim kerak|"
            r"to'lashim kerak)\b",
            "payable",
        ),

        (
            r"^(?P<person>.+?)"
            r"(?:ga|ka|qa)\s+.*"
            r"(?:berishim kerak|"
            r"to'lashim kerak|"
            r"qarzman|qarzdorman)\b",
            "payable",
        ),
    ]

    for (
        pattern,
        debt_type,
    ) in patterns:

        match = re.match(
            pattern,
            text,
        )

        if match:
            return (
                clean_person(
                    match.group(
                        "person"
                    )
                ),
                amount,
                debt_type,
                due_date,
            )

    return None


def looks_like_debt(
    text
):
    text = normalize_text(
        text
    )

    words = [
        "qarz",
        "qarzdor",
        "qarzman",
        "qarzdorman",
        "berishim kerak",
        "berishi kerak",
        "qaytarishi kerak",
        "qarz oldim",
        "qarz olganman",
    ]

    return any(
        word in text
        for word in words
    )


def get_debts(
    user_id
):
    conn = db()

    rows = conn.execute(
        "SELECT id, person, amount, "
        "debt_type, created_at, due_date "
        "FROM debts "
        "WHERE user_id = ? "
        "AND status = 'active' "
        "ORDER BY "
        "CASE WHEN due_date IS NULL "
        "THEN 1 ELSE 0 END, "
        "due_date ASC, id DESC",
        (
            user_id,
        ),
    ).fetchall()

    conn.close()

    return rows


def get_due_debts(
    user_id
):
    conn = db()

    rows = conn.execute(
        "SELECT id, person, amount, "
        "debt_type, due_date "
        "FROM debts "
        "WHERE user_id = ? "
        "AND status = 'active' "
        "AND due_date IS NOT NULL "
        "ORDER BY due_date ASC",
        (
            user_id,
        ),
    ).fetchall()

    conn.close()

    return rows


def partial_payment(
    user_id,
    debt_id,
    payment_amount,
    created_at=None,
):
    conn = db()
    cursor = conn.cursor()

    payment_time = (
        created_at
        or now_str()
    )

    row = cursor.execute(
        "SELECT person, amount, debt_type "
        "FROM debts "
        "WHERE id = ? "
        "AND user_id = ? "
        "AND status = 'active'",
        (
            debt_id,
            user_id,
        ),
    ).fetchone()

    if not row:
        conn.close()
        return None

    (
        person,
        remaining,
        debt_type,
    ) = row

    if payment_amount <= 0:
        conn.close()
        return "invalid"

    paid = min(
        payment_amount,
        remaining,
    )

    new_remaining = (
        remaining
        - paid
    )

    closed = (
        new_remaining == 0
    )

    if closed:

        cursor.execute(
            "UPDATE debts "
            "SET amount = 0, "
            "status = 'closed', "
            "closed_at = ? "
            "WHERE id = ? "
            "AND user_id = ?",
            (
                payment_time,
                debt_id,
                user_id,
            ),
        )

    else:

        cursor.execute(
            "UPDATE debts "
            "SET amount = ? "
            "WHERE id = ? "
            "AND user_id = ?",
            (
                new_remaining,
                debt_id,
                user_id,
            ),
        )

    cursor.execute(
        "INSERT INTO debt_payments "
        "(user_id, debt_id, "
        "amount, created_at) "
        "VALUES (?, ?, ?, ?)",
        (
            user_id,
            debt_id,
            paid,
            payment_time,
        ),
    )

    if debt_type == "receivable":

        cursor.execute(
            "INSERT INTO incomes "
            "(user_id, amount, category, "
            "created_at, source, reference_id) "
            "VALUES (?, ?, ?, ?, "
            "'debt', ?)",
            (
                user_id,
                paid,
                "qarz qaytdi",
                payment_time,
                debt_id,
            ),
        )

    else:

        cursor.execute(
            "INSERT INTO expenses "
            "(user_id, amount, category, "
            "created_at, source, reference_id) "
            "VALUES (?, ?, ?, ?, "
            "'debt', ?)",
            (
                user_id,
                paid,
                "qarz to'lovi",
                payment_time,
                debt_id,
            ),
        )

    conn.commit()
    conn.close()

    return (
        person,
        paid,
        new_remaining,
        debt_type,
        closed,
    )


def close_debt(
    user_id,
    debt_id,
):
    conn = db()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT person, amount, debt_type "
        "FROM debts "
        "WHERE id = ? "
        "AND user_id = ? "
        "AND status = 'active'",
        (
            debt_id,
            user_id,
        ),
    ).fetchone()

    if not row:
        conn.close()
        return None

    (
        person,
        remaining,
        debt_type,
    ) = row

    closing_time = now_str()

    cursor.execute(
        "UPDATE debts "
        "SET status = 'closed', "
        "amount = 0, "
        "closed_at = ? "
        "WHERE id = ? "
        "AND user_id = ?",
        (
            closing_time,
            debt_id,
            user_id,
        ),
    )

    cursor.execute(
        "INSERT INTO debt_payments "
        "(user_id, debt_id, "
        "amount, created_at) "
        "VALUES (?, ?, ?, ?)",
        (
            user_id,
            debt_id,
            remaining,
            closing_time,
        ),
    )

    if debt_type == "receivable":

        cursor.execute(
            "INSERT INTO incomes "
            "(user_id, amount, category, "
            "created_at, source, reference_id) "
            "VALUES (?, ?, ?, ?, "
            "'debt', ?)",
            (
                user_id,
                remaining,
                "qarz qaytdi",
                closing_time,
                debt_id,
            ),
        )

    else:

        cursor.execute(
            "INSERT INTO expenses "
            "(user_id, amount, category, "
            "created_at, source, reference_id) "
            "VALUES (?, ?, ?, ?, "
            "'debt', ?)",
            (
                user_id,
                remaining,
                "qarz to'lovi",
                closing_time,
                debt_id,
            ),
        )

    conn.commit()
    conn.close()

    return (
        person,
        remaining,
        debt_type,
    )


def normalize_person_key(
    name
):
    name = normalize_text(
        name
    )

    name = remove_date_words(
        name
    )

    name = re.sub(
        r"[^a-z0-9'ʻʼ\-\s]",
        "",
        name,
    )

    name = re.sub(
        r"\s+",
        " ",
        name,
    )

    return name.strip()


def clean_payable_person(
    person
):
    person = remove_date_words(
        person
    ).strip(
        " ,.-:"
    )

    person = re.sub(
        r"(ga|ka|qa)$",
        "",
        person,
    )

    return clean_person(
        person
    )


def find_active_debts_by_person(
    user_id,
    person,
    debt_type,
):
    target = normalize_person_key(
        person
    )

    conn = db()

    rows = conn.execute(
        "SELECT id, person, amount, debt_type "
        "FROM debts "
        "WHERE user_id = ? "
        "AND status = 'active' "
        "AND debt_type = ? "
        "ORDER BY id DESC",
        (
            user_id,
            debt_type,
        ),
    ).fetchall()

    conn.close()

    exact = [
        row
        for row in rows
        if normalize_person_key(
            row[1]
        ) == target
    ]

    if exact:
        return exact

    return [
        row
        for row in rows
        if (
            target
            and (
                target
                in normalize_person_key(
                    row[1]
                )
                or normalize_person_key(
                    row[1]
                )
                in target
            )
        )
    ]


def parse_natural_debt_payment(
    text
):
    normalized = normalize_text(
        text
    )

    span = find_amount_span(
        normalized
    )

    if not span:
        return None

    (
        start,
        end,
        amount,
    ) = span

    before = normalized[
        :start
    ].strip(
        " ,.-:"
    )

    after = normalized[
        end:
    ].strip(
        " ,.-:"
    )

    if not before:
        return None

    if (
        "qaytardi" in after
        or "qarzini berdi" in after
    ):

        person = clean_person(
            remove_date_words(
                before
            )
        )

        if person:
            return (
                person,
                amount,
                "receivable",
                created_at_from_text(
                    text
                ),
            )

    if (
        "qaytardim" in after
        or "qarzimni berdim" in after
    ):

        person = clean_payable_person(
            before
        )

        if person:
            return (
                person,
                amount,
                "payable",
                created_at_from_text(
                    text
                ),
            )

    return None


def debt_matches_text(
    rows
):
    return "\n".join(
        (
            f"#{row[0]} "
            f"{row[1]} — "
            f"{row[2]:,} so'm"
        )
        for row in rows[:5]
    )


# =========================================================
# STATISTIKA
# =========================================================

def get_statistics_data(
    user_id
):
    current = (
        current_month_str()
    )

    previous = (
        previous_month_str()
    )

    (
        income,
        expense,
        balance,
    ) = get_month_totals(
        user_id,
        current,
    )

    (
        _,
        previous_expense,
        _,
    ) = get_month_totals(
        user_id,
        previous,
    )

    conn = db()

    categories = conn.execute(
        "SELECT category, "
        "SUM(amount) "
        "FROM expenses "
        "WHERE user_id = ? "
        "AND created_at LIKE ? "
        "GROUP BY category "
        "ORDER BY SUM(amount) DESC",
        (
            user_id,
            current + "%",
        ),
    ).fetchall()

    conn.close()

    return {
        "income": income,
        "expense": expense,
        "balance": balance,
        "previous_expense": previous_expense,
        "categories": categories,
    }


# =========================================================
# TARIX QIDIRUV
# =========================================================

def search_history(
    user_id,
    query,
):
    text = normalize_text(
        query
    )

    month = parse_month_from_text(
        text
    )

    category = detect_category(
        text,
        user_id,
    )

    if category == "boshqa":
        category = None

    if (
        "daromad" in text
        or "kirim" in text
    ):
        types = [
            "income"
        ]

    elif (
        "xarajat" in text
        or "chiqim" in text
    ):
        types = [
            "expense"
        ]

    else:
        types = [
            "income",
            "expense",
        ]

    threshold = None
    comparator = None

    amount = parse_amount(
        text
    )

    if amount is not None:

        if any(
            word in text
            for word in [
                "dan katta",
                "katta",
                "ko'p",
                "yuqori",
            ]
        ):
            threshold = amount
            comparator = ">"

        elif any(
            word in text
            for word in [
                "dan kichik",
                "kichik",
                "kam",
                "past",
            ]
        ):
            threshold = amount
            comparator = "<"

    conn = db()

    results = []

    for operation_type in types:

        table = (
            "incomes"
            if operation_type
            == "income"
            else "expenses"
        )

        sql = (
            f"SELECT id, amount, "
            f"category, created_at "
            f"FROM {table} "
            f"WHERE user_id = ?"
        )

        params = [
            user_id
        ]

        if month:

            sql += (
                " AND created_at "
                "LIKE ?"
            )

            params.append(
                month + "%"
            )

        if category:

            sql += (
                " AND category = ?"
            )

            params.append(
                category
            )

        if (
            threshold is not None
            and comparator
        ):
            sql += (
                f" AND amount "
                f"{comparator} ?"
            )

            params.append(
                threshold
            )

        sql += (
            " ORDER BY "
            "created_at DESC "
            "LIMIT 30"
        )

        rows = conn.execute(
            sql,
            params,
        ).fetchall()

        for row in rows:

            results.append(
                (
                    operation_type,
                )
                + row
            )

    conn.close()

    results.sort(
        key=lambda row: row[4],
        reverse=True,
    )

    results = results[:30]

    if not results:
        return (
            "🔎 Hech narsa topilmadi."
        )

    result = (
        "🔎 Qidiruv natijasi:\n\n"
    )

    for (
        operation_type,
        operation_id,
        amount,
        category,
        created_at,
    ) in results:

        if operation_type == "income":

            icon = "🟢"
            code = "I"
            sign = "+"

        else:

            icon = "🔴"
            code = "E"
            sign = "-"

        result += (
            f"{icon} "
            f"{code}{operation_id} "
            f"{sign}{amount:,} so'm\n"
            f"📂 {category}\n"
            f"🕐 {created_at[5:16]}\n\n"
        )

    return result


# =========================================================
# YANGI HISOBNI 0 DAN BOSHLASH
# =========================================================

def reset_financial_data(
    user_id
):
    conn = db()
    cursor = conn.cursor()

    # Moliyaviy summalar va ularga bog'liq tarix tozalanadi.
    # Foydalanuvchining shaxsiy kategoriyalari saqlanib qoladi.
    for table in [
        "debt_payments",
        "debts",
        "expenses",
        "incomes",
        "budgets",
        "recurring",
    ]:

        cursor.execute(
            f"DELETE FROM {table} "
            f"WHERE user_id = ?",
            (
                user_id,
            ),
        )

    conn.commit()
    conn.close()


# =========================================================
# BARCHA MA'LUMOTNI TOZALASH
# =========================================================

def clear_user_data(
    user_id
):
    conn = db()
    cursor = conn.cursor()

    for table in [
        "debt_payments",
        "debts",
        "expenses",
        "incomes",
        "budgets",
        "recurring",
        "custom_categories",
    ]:

        cursor.execute(
            f"DELETE FROM {table} "
            f"WHERE user_id = ?",
            (
                user_id,
            ),
        )

    conn.commit()
    conn.close()


# =========================================================
# FON ESLATMALARI
# =========================================================

def get_due_recurring_items():
    today = tashkent_today()

    month = today.strftime(
        "%Y-%m"
    )

    last_day = calendar.monthrange(
        today.year,
        today.month,
    )[1]

    conn = db()

    rows = conn.execute(
        "SELECT id, user_id, "
        "title, amount, category, "
        "entry_type, day_of_month, "
        "mode, last_run_month "
        "FROM recurring "
        "WHERE active = 1"
    ).fetchall()

    conn.close()

    due = []

    for row in rows:

        effective_day = min(
            row[6],
            last_day,
        )

        if (
            today.day >= effective_day
            and row[8] != month
        ):
            due.append(
                row
            )

    return due


def mark_recurring_run(
    recurring_id
):
    conn = db()

    conn.execute(
        "UPDATE recurring "
        "SET last_run_month = ? "
        "WHERE id = ?",
        (
            current_month_str(),
            recurring_id,
        ),
    )

    conn.commit()
    conn.close()


async def background_loop(
    application
):
    await asyncio.sleep(
        5
    )

    while True:

        try:

            for (
                recurring_id,
                user_id,
                title,
                amount,
                category,
                entry_type,
                day_of_month,
                recurring_mode,
                last_run_month,
            ) in get_due_recurring_items():

                try:

                    if recurring_mode == "auto":

                        if entry_type == "income":

                            add_income(
                                user_id,
                                amount,
                                category,
                                source="recurring",
                                reference_id=recurring_id,
                            )

                            text = (
                                "🔁 Doimiy daromad "
                                "avtomatik qo'shildi.\n\n"
                                f"📌 {title}\n"
                                f"🟢 {amount:,} so'm"
                            )

                        else:

                            add_expense(
                                user_id,
                                amount,
                                category,
                                source="recurring",
                                reference_id=recurring_id,
                            )

                            text = (
                                "🔁 Doimiy xarajat "
                                "avtomatik qo'shildi.\n\n"
                                f"📌 {title}\n"
                                f"🔴 {amount:,} so'm"
                            )

                    else:

                        text = (
                            "🔔 Doimiy to'lov "
                            "eslatmasi\n\n"
                            f"📌 {title}\n"
                            f"💵 {amount:,} so'm"
                        )

                    await application.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        reply_markup=MAIN_MENU,
                    )

                    mark_recurring_run(
                        recurring_id
                    )

                except Exception as exc:

                    print(
                        f"Recurring item xatosi "
                        f"#{recurring_id}: "
                        f"{exc}"
                    )

        except Exception as exc:

            print(
                "Background loop xatosi:",
                exc,
            )

        await asyncio.sleep(
            3600
        )


async def post_init(
    application
):
    application.bot_data[
        "background_task"
    ] = asyncio.create_task(
        background_loop(
            application
        )
    )


async def post_shutdown(
    application
):
    task = application.bot_data.get(
        "background_task"
    )

    if task:

        task.cancel()

        try:
            await task

        except asyncio.CancelledError:
            pass


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        "👋 Salom!\n\n"
        "Hisobliy botiga xush kelibsiz.\n\n"
        "Masalan:\n"
        "🟢 Oylik 8 mln tushdi\n"
        "🔴 Bugun taksiga 70 ming ketdi\n"
        "🔴 Kecha 1.5 mln reklama uchun berdim\n"
        "🧾 Bugun taksi 50 ming, "
        "ovqat 80 ming, telefon 30 ming\n"
        "💳 Ali mendan 500 ming qarz\n"
        "💸 Ali 200 ming qaytardi",
        reply_markup=MAIN_MENU,
    )


# =========================================================
# HISOBOTLAR
# =========================================================

async def today_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    rows = get_today_expenses(
        update.effective_user.id
    )

    if not rows:

        await update.message.reply_text(
            "📊 Bugun hali xarajat yo'q.",
            reply_markup=MAIN_MENU,
        )

        return

    total = sum(
        amount
        for _, amount in rows
    )

    text = (
        "📊 Bugungi hisobot\n\n"
    )

    for (
        category,
        amount,
    ) in rows:

        text += (
            f"📂 {category}: "
            f"{amount:,} so'm\n"
        )

    text += (
        f"\n💸 Jami: "
        f"{total:,} so'm"
    )

    await update.message.reply_text(
        text,
        reply_markup=MAIN_MENU,
    )


async def monthly_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    (
        income,
        expense,
        balance,
    ) = get_month_report(
        update.effective_user.id
    )

    await update.message.reply_text(
        "📅 OYLIK HISOBOT\n\n"
        f"🟢 Kirim: "
        f"{income:,} so'm\n"
        f"🔴 Chiqim: "
        f"{expense:,} so'm\n\n"
        f"💰 Farq: "
        f"{balance:,} so'm",
        reply_markup=MAIN_MENU,
    )


async def balance_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    (
        income,
        expense,
        balance,
    ) = get_balance(
        update.effective_user.id
    )

    await update.message.reply_text(
        "💰 UMUMIY BALANS\n\n"
        f"🟢 Kirim: "
        f"{income:,} so'm\n"
        f"🔴 Chiqim: "
        f"{expense:,} so'm\n\n"
        f"💳 Balans: "
        f"{balance:,} so'm",
        reply_markup=BALANCE_MENU,
    )


async def history_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    rows = get_recent_operations(
        update.effective_user.id,
        10,
    )

    if not rows:

        text = (
            "🧾 Hozircha tarix bo'sh."
        )

    else:

        text = (
            "🧾 Oxirgi 10 "
            "operatsiya:\n\n"
        )

        for (
            op_type,
            op_id,
            amount,
            category,
            created_at,
            source,
        ) in rows:

            if op_type == "I":

                icon = "🟢"
                sign = "+"

            else:

                icon = "🔴"
                sign = "-"

            text += (
                f"{icon} "
                f"{op_type}{op_id} "
                f"{sign}{amount:,} so'm\n"
                f"📂 {category}\n"
                f"🕐 {created_at[5:16]}\n\n"
            )

    await update.message.reply_text(
        text,
        reply_markup=HISTORY_MENU,
    )


async def statistics_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    data = get_statistics_data(
        update.effective_user.id
    )

    categories = data[
        "categories"
    ]

    days_passed = max(
        tashkent_today().day,
        1,
    )

    daily_average = (
        data["expense"]
        / days_passed
    )

    if (
        data[
            "previous_expense"
        ]
        > 0
    ):

        difference = (
            (
                data["expense"]
                - data[
                    "previous_expense"
                ]
            )
            / data[
                "previous_expense"
            ]
            * 100
        )

        if difference > 0:

            comparison = (
                f"📈 O'tgan oydan "
                f"{difference:.1f}% ko'p"
            )

        elif difference < 0:

            comparison = (
                f"📉 O'tgan oydan "
                f"{abs(difference):.1f}% kam"
            )

        else:

            comparison = (
                "➖ O'tgan oy bilan bir xil"
            )

    else:

        comparison = (
            "ℹ️ O'tgan oyda xarajat yo'q"
        )

    if categories:

        top = (
            f"{categories[0][0]} — "
            f"{categories[0][1]:,} so'm"
        )

    else:

        top = (
            "Ma'lumot yo'q"
        )

    await update.message.reply_text(
        "📈 KUCHLI STATISTIKA\n\n"
        f"🟢 Daromad: "
        f"{data['income']:,} so'm\n"
        f"🔴 Xarajat: "
        f"{data['expense']:,} so'm\n"
        f"💰 Farq: "
        f"{data['balance']:,} so'm\n\n"
        f"📆 Kunlik o'rtacha: "
        f"{daily_average:,.0f} so'm\n"
        f"🏆 Eng katta kategoriya: "
        f"{top}\n"
        f"{comparison}",
        reply_markup=MAIN_MENU,
    )


# =========================================================
# BO'LIM MENYULARI
# =========================================================

async def debts_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.pop(
        "mode",
        None,
    )

    rows = get_debts(
        update.effective_user.id
    )

    receive_total = 0
    pay_total = 0

    receive_text = ""
    pay_text = ""

    for (
        debt_id,
        person,
        amount,
        debt_type,
        created_at,
        due_date,
    ) in rows:

        due_text = (
            f" | 📅 "
            f"{format_due_date(due_date)}"
            if due_date
            else ""
        )

        if debt_type == "receivable":

            receive_total += amount

            receive_text += (
                f"#{debt_id} "
                f"👤 {person} — "
                f"{amount:,} so'm"
                f"{due_text}\n"
            )

        else:

            pay_total += amount

            pay_text += (
                f"#{debt_id} "
                f"👤 {person} — "
                f"{amount:,} so'm"
                f"{due_text}\n"
            )

    text = (
        "💳 QARZLAR\n\n"
    )

    text += (
        "🟢 MENDAN QARZ:\n"
    )

    text += (
        receive_text
        if receive_text
        else "Hozircha yo'q.\n"
    )

    text += (
        f"\n💰 Jami: "
        f"{receive_total:,} so'm\n\n"
    )

    text += (
        "🔴 MEN QARZMAN:\n"
    )

    text += (
        pay_text
        if pay_text
        else "Hozircha yo'q.\n"
    )

    text += (
        f"\n💰 Jami: "
        f"{pay_total:,} so'm"
    )

    await update.message.reply_text(
        text,
        reply_markup=DEBT_MENU,
    )


async def budgets_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = budget_status_text(
        update.effective_user.id
    )

    if not text:

        text = (
            "🎯 BUDJET\n\n"
            "Hozircha budjet "
            "belgilanmagan."
        )

    await update.message.reply_text(
        text,
        reply_markup=BUDGET_MENU,
    )


async def recurring_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    rows = get_recurring(
        update.effective_user.id
    )

    text = (
        "🔁 DOIMIY TO'LOVLAR\n\n"
    )

    if not rows:

        text += (
            "Hozircha yo'q."
        )

    else:

        for (
            recurring_id,
            title,
            amount,
            category,
            entry_type,
            day_of_month,
            recurring_mode,
        ) in rows:

            icon = (
                "🟢"
                if entry_type
                == "income"
                else "🔴"
            )

            mode_text = (
                "Avtomatik"
                if recurring_mode
                == "auto"
                else "Eslatma"
            )

            text += (
                f"#{recurring_id} "
                f"{icon} {title}\n"
                f"💵 {amount:,} so'm\n"
                f"📅 Har oyning "
                f"{day_of_month}-kuni\n"
                f"⚙️ {mode_text}\n\n"
            )

    await update.message.reply_text(
        text,
        reply_markup=RECURRING_MENU,
    )


async def categories_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    rows = get_custom_categories(
        update.effective_user.id
    )

    text = (
        "🏷 KATEGORIYALAR\n\n"
    )

    text += (
        "Standart:\n"
        + ", ".join(
            CATEGORY_WORDS.keys()
        )
        + ", boshqa\n\n"
    )

    if rows:

        text += (
            "Siz yaratgan:\n"
        )

        for (
            category_id,
            name,
        ) in rows:

            text += (
                f"#{category_id} "
                f"— {name}\n"
            )

    else:

        text += (
            "Shaxsiy kategoriya yo'q."
        )

    await update.message.reply_text(
        text,
        reply_markup=CATEGORY_MENU,
    )


async def operations_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    rows = get_recent_operations(
        update.effective_user.id,
        10,
    )

    text = (
        "✏️ AMALLAR\n\n"
    )

    for (
        op_type,
        op_id,
        amount,
        category,
        created_at,
        source,
    ) in rows:

        icon = (
            "🟢"
            if op_type == "I"
            else "🔴"
        )

        text += (
            f"{icon} "
            f"{op_type}{op_id} — "
            f"{amount:,} so'm — "
            f"{category}\n"
        )

    if not rows:

        text += (
            "Hozircha operatsiya yo'q."
        )

    await update.message.reply_text(
        text,
        reply_markup=OPERATIONS_MENU,
    )


async def voice_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "🎤 Ovozli kiritishni "
        "keyingi bosqichda ulaymiz.",
        reply_markup=MAIN_MENU,
    )


# =========================================================
# ASOSIY MESSAGE
# =========================================================

async def message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = (
        update.message.text.strip()
    )

    user_id = (
        update.effective_user.id
    )

    # ASOSIY MENYU

    if text == "📊 Bugungi hisobot":

        await today_report(
            update,
            context,
        )

        return

    if text == "📅 Oylik hisobot":

        await monthly_report(
            update,
            context,
        )

        return

    if text == "💰 Balans":

        await balance_report(
            update,
            context,
        )

        return

    if text == "🧾 Tarix":

        await history_report(
            update,
            context,
        )

        return

    if text == "💳 Qarzlar":

        await debts_menu(
            update,
            context,
        )

        return

    if text == "📈 Statistika":

        await statistics_report(
            update,
            context,
        )

        return

    if text == "🎯 Budjet":

        await budgets_menu(
            update,
            context,
        )

        return

    if text == "🔁 Doimiy to'lovlar":

        await recurring_menu(
            update,
            context,
        )

        return

    if text == "✏️ Amallar":

        await operations_menu(
            update,
            context,
        )

        return

    if text == "🏷 Kategoriyalar":

        await categories_menu(
            update,
            context,
        )

        return

    if text == "🎤 Ovozli kiritish":

        await update.message.reply_text(
            "🎤 Ovozli kiritishni "
            "keyingi bosqichda ulaymiz.",
            reply_markup=MAIN_MENU,
        )

        return

    if text == "⚙️ Sozlamalar":

        await update.message.reply_text(
            "⚙️ SOZLAMALAR\n\n"
            "🌐 Til: O'zbekcha\n"
            "💵 Valyuta: so'm\n"
            "🕐 Vaqt: Toshkent (+05:00)",
            reply_markup=SETTINGS_MENU,
        )

        return

    if text == "⬅️ Asosiy menyu":

        context.user_data.clear()

        await update.message.reply_text(
            "🏠 Asosiy menyu",
            reply_markup=MAIN_MENU,
        )

        return

    # YANGI HISOBNI 0 DAN BOSHLASH

    if text == "♻️ Yangi hisob boshlash":

        context.user_data.clear()
        context.user_data[
            "mode"
        ] = "confirm_reset_account"

        await update.message.reply_text(
            "⚠️ YANGI HISOB BOSHLASH\n\n"
            "Bu amal barcha moliyaviy summalarni "
            "0 ga tushiradi va tarixni tozalaydi.\n\n"
            "O'chiriladi:\n"
            "• daromad va xarajatlar\n"
            "• operatsiyalar tarixi\n"
            "• qarzlar va qarz to'lovlari\n"
            "• budjetlar\n"
            "• doimiy to'lovlar\n\n"
            "🏷 Shaxsiy kategoriyalaringiz saqlanadi.\n\n"
            "Bu amalni ortga qaytarib bo'lmaydi. "
            "Davom etasizmi?",
            reply_markup=RESET_ACCOUNT_CONFIRM_MENU,
        )

        return

    if text == "✅ Ha, 0 dan boshlash":

        if (
            context.user_data.get(
                "mode"
            )
            == "confirm_reset_account"
        ):

            reset_financial_data(
                user_id
            )

            context.user_data.clear()

            await update.message.reply_text(
                "✅ Yangi hisob boshlandi.\n\n"
                "💰 Balans: 0 so'm\n"
                "📊 Daromad: 0 so'm\n"
                "📉 Xarajat: 0 so'm\n"
                "💳 Qarzlar: 0 so'm\n\n"
                "Endi hisob-kitobni 0 dan "
                "davom ettirishingiz mumkin.",
                reply_markup=MAIN_MENU,
            )

        else:

            await update.message.reply_text(
                "⚠️ Tasdiqlash muddati tugagan. "
                "Yangi hisob boshlashni qayta tanlang.",
                reply_markup=MAIN_MENU,
            )

        return

    if text == "❌ Bekor qilish":

        if (
            context.user_data.get(
                "mode"
            )
            == "confirm_reset_account"
        ):

            context.user_data.clear()

            await update.message.reply_text(
                "✅ Bekor qilindi. "
                "Hech qanday ma'lumot o'chirilmadi.",
                reply_markup=BALANCE_MENU,
            )

            return

    # TARIX

    if text == "🧾 Oxirgi 10 ta":

        await history_report(
            update,
            context,
        )

        return

    if text == "🔎 Qidirish / filtr":

        context.user_data[
            "mode"
        ] = "history_search"

        await update.message.reply_text(
            "🔎 Masalan:\n\n"
            "sentabrdagi taksi xarajatlari\n"
            "100 mingdan katta xarajatlar",
            reply_markup=HISTORY_MENU,
        )

        return

    # AMALLAR

    if text == "✏️ Operatsiyani tahrirlash":

        context.user_data[
            "mode"
        ] = "edit_select"

        await update.message.reply_text(
            "ID yuboring.\n"
            "Masalan: E12 yoki I5",
            reply_markup=OPERATIONS_MENU,
        )

        return

    if text == "🗑 Operatsiyani o'chirish":

        context.user_data[
            "mode"
        ] = "delete_operation"

        await update.message.reply_text(
            "ID yuboring.\n"
            "Masalan: E12 yoki I5",
            reply_markup=OPERATIONS_MENU,
        )

        return

    # BUDJET

    if text == "➕ Budjet qo'shish":

        context.user_data[
            "mode"
        ] = "add_budget"

        await update.message.reply_text(
            "Masalan:\n"
            "ovqat 2 mln",
            reply_markup=BUDGET_MENU,
        )

        return

    if text == "📊 Budjet holati":

        await budgets_menu(
            update,
            context,
        )

        return

    if text == "🗑 Budjetni o'chirish":

        context.user_data[
            "mode"
        ] = "delete_budget"

        await update.message.reply_text(
            "Budjet ID raqamini yuboring.",
            reply_markup=BUDGET_MENU,
        )

        return

    # KATEGORIYA

    if text == "➕ Kategoriya qo'shish":

        context.user_data[
            "mode"
        ] = "add_category"

        await update.message.reply_text(
            "Masalan: Salon",
            reply_markup=CATEGORY_MENU,
        )

        return

    if text == "📋 Kategoriyalar":

        await categories_menu(
            update,
            context,
        )

        return

    if text == "🗑 Kategoriya o'chirish":

        context.user_data[
            "mode"
        ] = "delete_category"

        await update.message.reply_text(
            "Kategoriya ID raqamini yuboring.",
            reply_markup=CATEGORY_MENU,
        )

        return

    # DOIMIY TO'LOV

    if text == "➕ Doimiy xarajat":

        context.user_data[
            "mode"
        ] = "add_recurring_expense"

        await update.message.reply_text(
            "Masalan:\n"
            "internet 150 ming 10 eslatma\n"
            "ijara 2 mln 1 avto",
            reply_markup=RECURRING_MENU,
        )

        return

    if text == "➕ Doimiy daromad":

        context.user_data[
            "mode"
        ] = "add_recurring_income"

        await update.message.reply_text(
            "Masalan:\n"
            "oylik 8 mln 5 avto",
            reply_markup=RECURRING_MENU,
        )

        return

    if text == "📋 Doimiy to'lovlar":

        await recurring_menu(
            update,
            context,
        )

        return

    if text == "🗑 Doimiy to'lovni o'chirish":

        context.user_data[
            "mode"
        ] = "delete_recurring"

        await update.message.reply_text(
            "ID raqamini yuboring.",
            reply_markup=RECURRING_MENU,
        )

        return

    # QARZLAR

    if text == "➕ Menga qarz":

        context.user_data[
            "mode"
        ] = "add_receivable"

        await update.message.reply_text(
            "Masalan:\n"
            "Ali 500 ming\n"
            "Ali 500 ming 20.10.2026",
            reply_markup=DEBT_MENU,
        )

        return

    if text == "➖ Men qarzdorman":

        context.user_data[
            "mode"
        ] = "add_payable"

        await update.message.reply_text(
            "Masalan:\n"
            "Vali 300 ming",
            reply_markup=DEBT_MENU,
        )

        return

    if text == "📋 Qarzlar ro'yxati":

        await debts_menu(
            update,
            context,
        )

        return

    if text == "⚠️ Muddatli qarzlar":

        rows = get_due_debts(
            user_id
        )

        if not rows:

            reply = (
                "⚠️ Muddatli qarz yo'q."
            )

        else:

            reply = (
                "⚠️ MUDDATLI QARZLAR\n\n"
            )

            for row in rows:

                reply += (
                    f"#{row[0]} "
                    f"👤 {row[1]}\n"
                    f"💵 {row[2]:,} so'm\n"
                    f"📅 "
                    f"{format_due_date(row[4])}\n\n"
                )

        await update.message.reply_text(
            reply,
            reply_markup=DEBT_MENU,
        )

        return

    if text == "💸 Qisman to'lov":

        context.user_data[
            "mode"
        ] = "partial_payment"

        await update.message.reply_text(
            "Masalan:\n"
            "2 200 ming",
            reply_markup=DEBT_MENU,
        )

        return

    if text == "✅ To'liq yopildi":

        context.user_data[
            "mode"
        ] = "close_debt"

        await update.message.reply_text(
            "Qarz ID raqamini yuboring.",
            reply_markup=DEBT_MENU,
        )

        return

    # BEKOR

    if text == "↩️ Bekor":

        result = delete_last_operation(
            user_id
        )

        if result is None:

            reply = (
                "↩️ Bekor qilinadigan "
                "operatsiya yo'q."
            )

        elif result == "protected":

            reply = (
                "⚠️ Oxirgi operatsiya "
                "qarz bilan bog'liq. "
                "Uni bu tugma bilan "
                "bekor qilib bo'lmaydi."
            )

        else:

            reply = (
                "✅ Oxirgi operatsiya "
                "bekor qilindi."
            )

        await update.message.reply_text(
            reply,
            reply_markup=MAIN_MENU,
        )

        return

    # TOZALASH

    if text == "🗑 Barcha ma'lumotlarni tozalash":

        context.user_data[
            "mode"
        ] = "confirm_clear"

        await update.message.reply_text(
            "⚠️ Barcha ma'lumotlar "
            "butunlay o'chadi.\n\n"
            "Rostdan ham davom etasizmi?",
            reply_markup=CLEAR_CONFIRM_MENU,
        )

        return

    if text == "✅ Ha, tozalash":

        if (
            context.user_data.get(
                "mode"
            )
            == "confirm_clear"
        ):

            clear_user_data(
                user_id
            )

            context.user_data.clear()

            await update.message.reply_text(
                "✅ Barcha ma'lumotlaringiz "
                "tozalandi.",
                reply_markup=MAIN_MENU,
            )

        return

    if text == "❌ Yo'q":

        context.user_data.clear()

        await update.message.reply_text(
            "✅ Ma'lumotlar o'chirilmadi.",
            reply_markup=MAIN_MENU,
        )

        return

    mode = context.user_data.get(
        "mode"
    )

    # QARZ TOPILMAGANDA TASDIQ

    if (
        mode
        == "confirm_unmatched_debt_transaction"
    ):

        answer = normalize_text(
            text
        )

        pending = (
            context.user_data.get(
                "pending_debt_transaction"
            )
        )

        if (
            answer
            in [
                "ha",
                "xa",
                "yes",
                "ok",
                "mayli",
            ]
            and pending
        ):

            amount = pending[
                "amount"
            ]

            created_at = pending[
                "created_at"
            ]

            if (
                pending[
                    "entry_type"
                ]
                == "income"
            ):

                add_income(
                    user_id,
                    amount,
                    "qarz qaytdi",
                    created_at=created_at,
                )

                reply = (
                    "✅ Oddiy kirim "
                    "sifatida saqlandi.\n\n"
                    f"🟢 {amount:,} so'm"
                )

            else:

                add_expense(
                    user_id,
                    amount,
                    "qarz to'lovi",
                    created_at=created_at,
                )

                reply = (
                    "✅ Oddiy chiqim "
                    "sifatida saqlandi.\n\n"
                    f"🔴 {amount:,} so'm"
                )

            context.user_data.clear()

            await update.message.reply_text(
                reply,
                reply_markup=MAIN_MENU,
            )

            return

        if answer in [
            "yo'q",
            "yoq",
            "no",
            "bekor",
        ]:

            context.user_data.clear()

            await update.message.reply_text(
                "✅ Saqlanmadi.",
                reply_markup=MAIN_MENU,
            )

            return

        await update.message.reply_text(
            "Iltimos, faqat "
            "Ha yoki Yo'q deb yozing.",
            reply_markup=MAIN_MENU,
        )

        return

    # TARIX QIDIRUV

    if mode == "history_search":

        result = search_history(
            user_id,
            text,
        )

        context.user_data.clear()

        await update.message.reply_text(
            result,
            reply_markup=HISTORY_MENU,
        )

        return

    # KATEGORIYA

    if mode == "add_category":

        (
            success,
            result,
        ) = add_custom_category(
            user_id,
            text,
        )

        context.user_data.clear()

        if success:

            reply = (
                "✅ Kategoriya qo'shildi: "
                f"{result}"
            )

        else:

            reply = (
                "⚠️ Kategoriya mavjud "
                "yoki nom noto'g'ri."
            )

        await update.message.reply_text(
            reply,
            reply_markup=CATEGORY_MENU,
        )

        return

    if mode == "delete_category":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ ID raqamini yuboring.",
                reply_markup=CATEGORY_MENU,
            )

            return

        result = delete_custom_category(
            user_id,
            int(text),
        )

        context.user_data.clear()

        await update.message.reply_text(
            (
                f"✅ {result} o'chirildi."
                if result
                else "❌ Topilmadi."
            ),
            reply_markup=CATEGORY_MENU,
        )

        return

    # BUDJET

    if mode == "add_budget":

        span = find_amount_span(
            text
        )

        if not span:

            await update.message.reply_text(
                "❌ Masalan: "
                "ovqat 2 mln",
                reply_markup=BUDGET_MENU,
            )

            return

        (
            start,
            end,
            amount,
        ) = span

        category_text = (
            normalize_text(
                text
            )[:start]
            .strip(
                " ,.-:"
            )
        )

        category = category_from_label(
            user_id,
            category_text,
        )

        if category is None:

            await update.message.reply_text(
                "❌ Kategoriya topilmadi.",
                reply_markup=BUDGET_MENU,
            )

            return

        budget_id = set_budget(
            user_id,
            category,
            amount,
        )

        context.user_data.clear()

        await update.message.reply_text(
            "✅ Budjet saqlandi.\n\n"
            f"#{budget_id}\n"
            f"📂 {category}\n"
            f"🎯 {amount:,} so'm",
            reply_markup=BUDGET_MENU,
        )

        return

    if mode == "delete_budget":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ ID raqamini yuboring.",
                reply_markup=BUDGET_MENU,
            )

            return

        result = delete_budget(
            user_id,
            int(text),
        )

        context.user_data.clear()

        await update.message.reply_text(
            (
                f"✅ {result} "
                "budjeti o'chirildi."
                if result
                else "❌ Topilmadi."
            ),
            reply_markup=BUDGET_MENU,
        )

        return

    # RECURRING

    if mode in [
        "add_recurring_expense",
        "add_recurring_income",
    ]:

        entry_type = (
            "expense"
            if mode
            == "add_recurring_expense"
            else "income"
        )

        parsed = parse_recurring_input(
            text,
            user_id,
            entry_type,
        )

        if not parsed:

            await update.message.reply_text(
                "❌ Format noto'g'ri.",
                reply_markup=RECURRING_MENU,
            )

            return

        recurring_id = add_recurring(
            user_id,
            *parsed,
        )

        context.user_data.clear()

        await update.message.reply_text(
            "✅ Doimiy to'lov "
            "saqlandi.\n\n"
            f"ID: #{recurring_id}",
            reply_markup=RECURRING_MENU,
        )

        return

    if mode == "delete_recurring":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ ID raqamini yuboring.",
                reply_markup=RECURRING_MENU,
            )

            return

        result = delete_recurring(
            user_id,
            int(text),
        )

        context.user_data.clear()

        await update.message.reply_text(
            (
                f"✅ {result} o'chirildi."
                if result
                else "❌ Topilmadi."
            ),
            reply_markup=RECURRING_MENU,
        )

        return

    # OPERATSIYA TAHRIR

    if mode == "edit_select":

        target = parse_operation_id(
            text
        )

        if not target:

            await update.message.reply_text(
                "❌ Masalan: E12 yoki I5",
                reply_markup=OPERATIONS_MENU,
            )

            return

        row = get_operation(
            user_id,
            *target,
        )

        if not row:

            await update.message.reply_text(
                "❌ Topilmadi.",
                reply_markup=OPERATIONS_MENU,
            )

            return

        context.user_data[
            "edit_target"
        ] = target

        context.user_data[
            "mode"
        ] = "edit_value"

        await update.message.reply_text(
            "Yangi summa va kategoriya:\n"
            "Masalan: 85 ming ovqat",
            reply_markup=OPERATIONS_MENU,
        )

        return

    if mode == "edit_value":

        target = context.user_data.get(
            "edit_target"
        )

        span = find_amount_span(
            text
        )

        if (
            not target
            or not span
        ):

            await update.message.reply_text(
                "❌ Summani tushunmadim.",
                reply_markup=OPERATIONS_MENU,
            )

            return

        (
            start,
            end,
            amount,
        ) = span

        tail = (
            normalize_text(
                text
            )[end:]
            .strip(
                " ,.-:"
            )
        )

        category = None

        if tail:

            category = category_from_label(
                user_id,
                tail,
            )

        result = edit_operation(
            user_id,
            target[0],
            target[1],
            amount,
            category,
        )

        context.user_data.clear()

        if result == "protected":

            reply = (
                "❌ Qarz bilan bog'liq "
                "operatsiyani tahrirlab "
                "bo'lmaydi."
            )

        elif result:

            reply = (
                "✅ Operatsiya yangilandi."
            )

        else:

            reply = (
                "❌ Tahrirlab bo'lmadi."
            )

        await update.message.reply_text(
            reply,
            reply_markup=OPERATIONS_MENU,
        )

        return

    if mode == "delete_operation":

        target = parse_operation_id(
            text
        )

        if not target:

            await update.message.reply_text(
                "❌ Masalan: E12 yoki I5",
                reply_markup=OPERATIONS_MENU,
            )

            return

        result = delete_operation(
            user_id,
            *target,
        )

        context.user_data.clear()

        if result == "protected":

            reply = (
                "❌ Qarz bilan bog'liq "
                "operatsiyani o'chirib "
                "bo'lmaydi."
            )

        elif result:

            reply = (
                "✅ Operatsiya o'chirildi."
            )

        else:

            reply = (
                "❌ O'chirib bo'lmadi."
            )

        await update.message.reply_text(
            reply,
            reply_markup=OPERATIONS_MENU,
        )

        return

    # QARZ QO'SHISH

    if mode in [
        "add_receivable",
        "add_payable",
    ]:

        (
            person,
            amount,
            due_date,
        ) = parse_simple_debt_input(
            text
        )

        if (
            not person
            or amount is None
        ):

            await update.message.reply_text(
                "❌ Masalan: "
                "Ali 500 ming",
                reply_markup=DEBT_MENU,
            )

            return

        debt_type = (
            "receivable"
            if mode
            == "add_receivable"
            else "payable"
        )

        debt_id = add_debt(
            user_id,
            person,
            amount,
            debt_type,
            due_date,
        )

        context.user_data.clear()

        await update.message.reply_text(
            "✅ Qarz saqlandi.\n\n"
            f"ID: #{debt_id}\n"
            f"👤 {person}\n"
            f"💵 {amount:,} so'm",
            reply_markup=DEBT_MENU,
        )

        return

    # QISMAN TO'LOV

    if mode == "partial_payment":

        match = re.match(
            r"^#?(\d+)\s+(.+)$",
            text,
        )

        if not match:

            await update.message.reply_text(
                "❌ Masalan: "
                "2 200 ming",
                reply_markup=DEBT_MENU,
            )

            return

        debt_id = int(
            match.group(1)
        )

        amount = parse_amount(
            match.group(2)
        )

        if amount is None:

            await update.message.reply_text(
                "❌ Summani tushunmadim.",
                reply_markup=DEBT_MENU,
            )

            return

        result = partial_payment(
            user_id,
            debt_id,
            amount,
        )

        context.user_data.clear()

        if result == "invalid":

            reply = (
                "❌ To'lov summasi "
                "noto'g'ri."
            )

        elif not result:

            reply = (
                "❌ Qarz topilmadi."
            )

        else:

            reply = (
                "✅ To'lov saqlandi.\n\n"
                f"👤 {result[0]}\n"
                f"💸 To'landi: "
                f"{result[1]:,} so'm\n"
                f"💰 Qoldi: "
                f"{result[2]:,} so'm"
            )

        await update.message.reply_text(
            reply,
            reply_markup=DEBT_MENU,
        )

        return

    if mode == "close_debt":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ Qarz ID raqamini yuboring.",
                reply_markup=DEBT_MENU,
            )

            return

        result = close_debt(
            user_id,
            int(text),
        )

        context.user_data.clear()

        await update.message.reply_text(
            (
                "✅ Qarz yopildi."
                if result
                else "❌ Qarz topilmadi."
            ),
            reply_markup=DEBT_MENU,
        )

        return

    # =====================================================
    # TABIIY QARZ TO'LOVI
    # =====================================================

    debt_payment = (
        parse_natural_debt_payment(
            text
        )
    )

    if debt_payment:

        (
            person,
            payment_amount,
            debt_type,
            payment_time,
        ) = debt_payment

        matches = (
            find_active_debts_by_person(
                user_id,
                person,
                debt_type,
            )
        )

        if len(matches) == 1:

            result = partial_payment(
                user_id,
                matches[0][0],
                payment_amount,
                created_at=payment_time,
            )

            if result:

                direction = (
                    "🟢 Qarzdan qaytdi"
                    if debt_type
                    == "receivable"
                    else
                    "🔴 Qarzga qaytarildi"
                )

                reply = (
                    "✅ Qarz to'lovi "
                    "tushunildi.\n\n"
                    f"👤 {result[0]}\n"
                    f"{direction}: "
                    f"{result[1]:,} so'm\n"
                    f"💰 Qoldi: "
                    f"{result[2]:,} so'm"
                )

                if result[4]:

                    reply += (
                        "\n✅ Qarz to'liq yopildi."
                    )

                await update.message.reply_text(
                    reply,
                    reply_markup=MAIN_MENU,
                )

                return

        if len(matches) > 1:

            await update.message.reply_text(
                "⚠️ Shu ismda bir nechta "
                "faol qarz topildi. "
                "Qaysi biri ekanini "
                "ID orqali tanlang:\n\n"
                + debt_matches_text(
                    matches
                )
                + "\n\n💳 Qarzlar → "
                "💸 Qisman to'lov "
                "bo'limidan ID bilan kiriting.",
                reply_markup=DEBT_MENU,
            )

            return

        context.user_data[
            "mode"
        ] = (
            "confirm_unmatched_debt_transaction"
        )

        context.user_data[
            "pending_debt_transaction"
        ] = {
            "amount": payment_amount,
            "created_at": payment_time,
            "entry_type": (
                "income"
                if debt_type
                == "receivable"
                else "expense"
            ),
        }

        if debt_type == "receivable":

            question = (
                f"🤔 {person} nomida "
                "faol qarz topilmadi.\n\n"
                f"{payment_amount:,} so'mni "
                "oddiy kirim sifatida "
                "saqlaymi?\n"
                "Ha / Yo'q"
            )

        else:

            question = (
                f"🤔 {person} nomida "
                "sizning faol qarzingiz "
                "topilmadi.\n\n"
                f"{payment_amount:,} so'mni "
                "oddiy chiqim sifatida "
                "saqlaymi?\n"
                "Ha / Yo'q"
            )

        await update.message.reply_text(
            question,
            reply_markup=MAIN_MENU,
        )

        return

    # =====================================================
    # TABIIY QARZ YARATISH
    # =====================================================

    debt = detect_natural_debt(
        text
    )

    if debt:

        (
            person,
            amount,
            debt_type,
            due_date,
        ) = debt

        debt_id = add_debt(
            user_id,
            person,
            amount,
            debt_type,
            due_date,
        )

        await update.message.reply_text(
            "✅ Qarz saqlandi.\n\n"
            f"ID: #{debt_id}\n"
            f"👤 {person}\n"
            f"💵 {amount:,} so'm",
            reply_markup=MAIN_MENU,
        )

        return

    if looks_like_debt(
        text
    ):

        await update.message.reply_text(
            "🤔 Qarz ekanini tushundim, "
            "lekin aniq tushunmadim.\n\n"
            "Masalan:\n"
            "Ali mendan 500 ming qarz\n"
            "Men Validan 300 ming qarzman",
            reply_markup=MAIN_MENU,
        )

        return

    # =====================================================
    # YANGI:
    # BIR XABARDA BIR NECHTA OPERATSIYA
    # =====================================================

    multi_operations = (
        parse_multi_transactions(
            text,
            user_id,
        )
    )

    if multi_operations:

        (
            saved,
            total_income,
            total_expense,
        ) = save_multi_transactions(
            user_id,
            multi_operations,
        )

        (
            _,
            _,
            balance,
        ) = get_balance(
            user_id
        )

        reply = (
            f"✅ {len(saved)} ta "
            f"operatsiya saqlandi!\n\n"
        )

        reply += "\n".join(
            saved
        )

        if total_income:

            reply += (
                f"\n\n🟢 Jami kirim: "
                f"{total_income:,} so'm"
            )

        if total_expense:

            reply += (
                f"\n🔴 Jami chiqim: "
                f"{total_expense:,} so'm"
            )

        reply += (
            f"\n\n💰 Balans: "
            f"{balance:,} so'm"
        )

        warned_categories = set()

        for operation in multi_operations:

            if (
                operation[
                    "entry_type"
                ]
                != "expense"
            ):
                continue

            category = operation[
                "category"
            ]

            if category in warned_categories:
                continue

            warned_categories.add(
                category
            )

            budget = (
                get_budget_for_category(
                    user_id,
                    category,
                )
            )

            if not budget:
                continue

            limit_amount = (
                budget[1]
            )

            spent = (
                get_category_spent(
                    user_id,
                    category,
                )
            )

            remaining = (
                limit_amount
                - spent
            )

            if remaining < 0:

                reply += (
                    f"\n\n⚠️ {category}: "
                    f"budjet "
                    f"{abs(remaining):,} "
                    f"so'mga oshib ketdi."
                )

            elif limit_amount:

                percent = (
                    spent
                    / limit_amount
                    * 100
                )

                if percent >= 80:

                    reply += (
                        f"\n\n🎯 {category}: "
                        f"budjet "
                        f"{percent:.0f}% "
                        f"ishlatildi."
                    )

        await update.message.reply_text(
            reply,
            reply_markup=MAIN_MENU,
        )

        return

    # =====================================================
    # ODDIY BITTA KIRIM / CHIQIM
    # =====================================================

    amount = parse_amount(
        text
    )

    if amount is None:

        await update.message.reply_text(
            "🤔 Summani tushunmadim.\n\n"
            "Masalan:\n"
            "Taksi 70 ming\n"
            "Oylik 8 mln\n"
            "Bugun taksi 50 ming, "
            "ovqat 80 ming",
            reply_markup=MAIN_MENU,
        )

        return

    category = detect_category(
        text,
        user_id,
    )

    transaction_time = (
        created_at_from_text(
            text
        )
    )

    if is_income_text(
        text
    ):

        add_income(
            user_id,
            amount,
            category,
            created_at=transaction_time,
        )

        (
            _,
            _,
            balance,
        ) = get_balance(
            user_id
        )

        await update.message.reply_text(
            "✅ Kirim saqlandi!\n\n"
            f"🟢 {amount:,} so'm\n"
            f"📂 {category}\n\n"
            f"💰 Balans: "
            f"{balance:,} so'm",
            reply_markup=MAIN_MENU,
        )

    else:

        add_expense(
            user_id,
            amount,
            category,
            created_at=transaction_time,
        )

        (
            _,
            _,
            balance,
        ) = get_balance(
            user_id
        )

        reply = (
            "✅ Chiqim saqlandi!\n\n"
            f"🔴 {amount:,} so'm\n"
            f"📂 {category}\n\n"
            f"💰 Balans: "
            f"{balance:,} so'm"
        )

        budget = (
            get_budget_for_category(
                user_id,
                category,
            )
        )

        if budget:

            limit_amount = (
                budget[1]
            )

            spent = (
                get_category_spent(
                    user_id,
                    category,
                )
            )

            remaining = (
                limit_amount
                - spent
            )

            if remaining < 0:

                reply += (
                    f"\n\n⚠️ Budjet "
                    f"{abs(remaining):,} "
                    f"so'mga oshib ketdi."
                )

            elif limit_amount:

                percent = (
                    spent
                    / limit_amount
                    * 100
                )

                if percent >= 80:

                    reply += (
                        f"\n\n🎯 Budjet "
                        f"{percent:.0f}% "
                        f"ishlatildi."
                    )

        await update.message.reply_text(
            reply,
            reply_markup=MAIN_MENU,
        )


# =========================================================
# XATO HANDLER
# =========================================================

async def error_handler(
    update,
    context,
):
    print(
        "Bot xatosi:",
        context.error,
    )


# =========================================================
# MAIN
# =========================================================

def main():
    init_db()

    app = (
        Application
        .builder()
        .token(TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "hisobot",
            today_report,
        )
    )

    app.add_handler(
        CommandHandler(
            "oylik",
            monthly_report,
        )
    )

    app.add_handler(
        CommandHandler(
            "balans",
            balance_report,
        )
    )

    app.add_handler(
        CommandHandler(
            "tarix",
            history_report,
        )
    )

    app.add_handler(
        CommandHandler(
            "qarz",
            debts_menu,
        )
    )

    app.add_handler(
        CommandHandler(
            "statistika",
            statistics_report,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.VOICE,
            voice_message,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            message,
        )
    )

    app.add_error_handler(
        error_handler
    )

    print(
        "Hisobliy ishga tushdi..."
    )

    print(
        "Database:",
        DB_PATH,
    )

    print(
        "Toshkent vaqti:",
        tashkent_now().strftime(
            "%Y-%m-%d %H:%M:%S %z"
        ),
    )

    app.run_polling()


if __name__ == "__main__":
    main()