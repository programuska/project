import csv
import urllib.request

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Renders message as an apology to user."""
    """Отдает сообщение как извинение пользователю """
    def escape(s):
        """
        Escape special characters - Побег специальные символы

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login - Украсить маршруты, требующие входа

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:  # "Идентификатор пользователя"
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol - Смотри цитату для символа. """

    # reject symbol if it starts with caret
    # отклонить символ, если он начинается с каретки
    if symbol.startswith("^"):
        return None

    # Reject symbol if it contains comma
    # Отклонить символ, если он содержит запятую
    if "," in symbol:
        return None

    # Query Yahoo for quote
    # Запрос Yahoo для цитаты
    # http://stackoverflow.com/a/21351911
    try:

        # GET CSV
        url = f"http://download.finance.yahoo.com/d/quotes.csv?f=snl1&s={symbol}"
        webpage = urllib.request.urlopen(url)

        # Read CSV
        datareader = csv.reader(webpage.read().decode("utf-8").splitlines())

        # Parse first row - Выполнить первый ряд
        row = next(datareader)

        # Ensure stock exists - # Обеспечить наличие запасов
        try:
            price = float(row[2])
        except:
            return None

        # Return stock's name (as a str), price (as a float), and (uppercased) symbol (as a str)
        # Имя возвращаемого запаса (как str), цена (как float) и (верхний) символ (как str)
        return {
            "name": row[1],
            "price": price,
            "symbol": row[0].upper()
        }

    except:
        pass

    # Query Alpha Vantage for quote instead - вместо цитаты
    # https://www.alphavantage.co/documentation/
    try:

        # GET CSV
        url = f"https://www.alphavantage.co/query?apikey=NAJXWIA8D6VN6A3K&datatype=csv&function=TIME_SERIES_INTRADAY&interval=1min&symbol={symbol}"
        webpage = urllib.request.urlopen(url)

        # Parse CSV
        datareader = csv.reader(webpage.read().decode("utf-8").splitlines())

        # Ignore first row - Игнорировать первую строку
        next(datareader)

        # Parse second row - Разбор второй строки
        row = next(datareader)

        # Ensure stock exists - Обеспечить наличие запасов
        try:
            price = float(row[4])
        except:
            return None

        # Return stock's name (as a str), price (as a float), and (uppercased) symbol (as a str)
        # Возвращаемое имя запаса (как str), цена (как float) и (верхний) символ (как str)
        return {
            "name": symbol.upper(),  # for backward compatibility with Yahoo - для обратной совместимости
            "price": price,
            "symbol": symbol.upper()
        }

    except:
        return None


def usd(value):
    """Formats value as USD - Форматирует значение как USD"""
    return f"${value:,.2f}"


def hrn(value):
    """Formats value as HRN Ukraine - Форматирует значение как Гривна"""
    return f"{value:,.2f} грн."
