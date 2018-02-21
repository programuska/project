from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, Flask, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3  # встроенная поддержку SQLite базы данных
from passlib.apps import custom_app_context as pwd_context

from helpers import apology, login_required, lookup, usd, hrn
import re

# Configure application - Настроить приложение
app = Flask(__name__)


# Ensure responses aren't cached - Убедитесь, что ответы не кэшируются
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter - Пользовательский фильтр
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters["hrn"] = hrn

# Configure session to use filesystem (instead of signed cookies)
# Настроить сеанс для использования файловой системы (вместо подписанных файлов cookie)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
# Настройка библиотеки CS50 для использования базы данных SQLite
db = SQL("sqlite:///stock.db")


@app.route("/")
@login_required
def index():
    """ Show warehouse status - Показать состояние склада """
    # Variable indices for selecting from the table process quantity and part_code by id
    # Переменная indices для выбора из таблицы process quantity и part_code по id с помощью запроса db.execute()
    indices = db.execute("SELECT * FROM process")

    # вводим переменную для общей стоимости всех деталей
    total_stock = 0.0

    for index in indices:
        price = index["price"]  # шифр детали
        quantity = index["quantity"]  # кол-во деталей
        # всего суммарная стоимость деталей этого типа на текущий момент
        total_price = int(quantity) * float(price)
        total_stock += total_price

    return render_template("index.html", stocks=indices, total=hrn(total_stock))


@app.route("/coming", methods=["GET", "POST"])
@login_required
def coming():
    """Arrival of parts - Приход деталей"""

    # if user reached route via POST
    # если пользователь достиг маршрута через POST
    if request.method == "POST":

        # ensure that the cipher has been sent
        # гарантировать, что шифр был отправлен
        if not request.form.get("coming"):  # если не назван шифр детали во вкладке приход
            return apology("Must provide part_code")  # должен предоставить шифр детали

        # Ensure that the number of parts is named
        # гарантировать, что количество деталей названо
        elif not request.form.get("quantity"):
            return apology("Must provide quantity")  # должен предоставить кол-во деталей quantity

        # The number of quantity is returned to the quantity variable with request.form.get () function
        # в переменную quantity с функцией request.form.get() возвращается кол-во деталей
        quantity = request.form.get("quantity")
        #  Метод ищет по всей строке, но возвращает только первое найденное
        # совпадение c "\D". Обеспечивает кол-во деталей положительным и int
        if re.search(r"\D", quantity) != None:
            return apology("must provide int number")  # должен предоставить кол-во деталей целое
        if int(quantity) <= 0:
            # кол-во деталей должно быть положительным целым числом
            return apology("Quantity must be positive integer")

        # The variable code with the request.form.get () function looks for the part number
        # переменная code с функцией request.form.get() ищет шифр детали
        code = request.form.get("coming")

        # Choosing from the database details form part cipher
        # Выбор из базы данных формы details шифра детали
        result = db.execute("SELECT * FROM details WHERE part_code = :part_code", part_code=code)

        # Choosing from the database process form part cipher
        # Выбор из базы данных формы process шифра детали
        existing = db.execute("SELECT * FROM process WHERE part_code = :part_code",
                              part_code=result[0]["part_code"])

        price = result[0]["price"]
        trnasact_price = int(quantity) * float(price)  # расчёт всей суммы стоимости деталей

        # If the user does not have a record about these details, create a new stock object
        # если пользователь не имеет записи про эти детали, создайте новый объект запаса
        # Вставить в process (имя, шифр, наименование, цена, сумма, количество)
        if len(existing) != 1:
            db.execute("INSERT INTO process (part_code,  detail_name, price, total_price, quantity) "
                       "VALUES (:part_code, :detail_name, :price, :total_price, :quantity);",
                       part_code=result[0]["part_code"], detail_name=result[0]["detail_name"],
                       price=price, total_price=hrn(trnasact_price), quantity=quantity)

        else:
            # Обновление данных пользователя
            total_price = int(existing[0]["quantity"]) * float(price)
            total_price += trnasact_price

            db.execute("UPDATE process "
                       "SET quantity = :quantity+quantity, total_price = :total_price "
                       "WHERE part_code = :part_code;", quantity=quantity, total_price=hrn(total_price),
                       part_code=result[0]["part_code"])

        username = db.execute("SELECT username FROM users WHERE id=:id", id=session["user_id"])

        # update history - история обновления, Вставить в истории (шифр, наименование, цена, id, количество деталий)
        db.execute("INSERT INTO historys (id, username, part_code, detail_name, price, total_price, quantity) "
                   "VALUES ( :id, :username, :part_code, :detail_name, :price, :total_price, :quantity);",
                   id=session["user_id"], username=username[0]["username"], part_code=result[0]["part_code"],
                   detail_name=result[0]["detail_name"], price=price,
                   total_price=hrn(trnasact_price), quantity=int(quantity))

        flash("Success!")  # Успех
        flash("Операция прихода деталей проведена успешно!")
        return redirect(url_for("index"))
    else:

        # Выбор из базы данных формы details шифра детали
        rows = db.execute("SELECT part_code FROM details ")

        # Возврат запроса в coming.html
        return render_template("coming.html", choicecode=rows)


@app.route("/history")
@login_required
def history():
    """Show history of transactions - Показать историю транзакций пользователя"""

    histories = db.execute("SELECT * FROM historys WHERE id=:id", id=session["user_id"])
    return render_template("history.html", histories=histories, username=histories[0]["username"])


@app.route("/historys")
@login_required
def historys():
    """Show history of transactions - Показать общую историю транзакций"""

    histories = db.execute("SELECT * FROM historys")
    return render_template("historys.html", histories=histories)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in - Войти в систему"""

    # Forget any user_id - Забыть любой user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    # Пользователь достиг маршрута через POST (как, отправив форму через POST)
    if request.method == "POST":

        # Ensure username was submitted - Убедитесь, что имя пользователя отправлено
        if not request.form.get("username"):
            return apology("must provide username", 403)  # должен указать имя пользователя

        # Ensure password was submitted - Убедитесь, что пароль был отправлен
        elif not request.form.get("password"):
            return apology("must provide password", 403)  # должен предоставить пароль

        # Query database for username - База данных запросов для имени пользователя
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))  # строка

        # Ensure username exists and password is correct
        # Убедитесь, что имя пользователя существует и пароль правильный.
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in - Помните, какой пользователь вошел в систему
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page - Перенаправление пользователя на главную страницу
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    # Пользователь достиг маршрута через GET (например, нажав ссылку или перенаправляя)
    else:

        logins = db.execute("SELECT username FROM users ")
        return render_template("login.html", logins=logins)


@app.route("/logout")
def logout():
    """Log user out - Выйти из системы"""

    # Forget any user_id - Забыть любой user_id
    session.clear()

    # Redirect user to login form - Перенаправить пользователя в форму входа
    return redirect("/")


@app.route("/choice", methods=["GET", "POST"])
@login_required
def choice():
    """Get the price and drawing details - Получить цену и чертеж детали"""
    if request.method == "POST":

        code = request.form.get("choice")
        # Выбор из базы данных формы details шифра детали
        rows = db.execute("SELECT * FROM details WHERE part_code = :part_code", part_code=code)

        if not rows:
            return apology("Invalid code detailse")  # Сообщение об ошибке при проверке

        dollarprice = usd(rows[0]["price"] / 27.24)  # Переменная для перевода цены в доллары

        # Возвращаем в choiced.htm параметры из базы данных как результат
        return render_template("choiced.html", part_code=rows[0]["part_code"], detail_name=rows[0]["detail_name"],
                               price=rows[0]["price"], dollarprice=dollarprice)
    else:

        # Выбор из базы данных формы details шифра детали
        rows = db.execute("SELECT part_code FROM details ")

        # Возврат запроса в choice.html
        return render_template("choice.html", choicecode=rows)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user - Зарегистрировать пользователя"""

    # Forget any user_id - Забыть любой user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    # Пользователь достиг маршрута через POST (как, отправив форму через POST)
    if request.method == "POST":

        # Ensure username was submitted
        # get username - получить имя пользователя
        # Убедитесь, что имя пользователя отправлено
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        # Убедитесь, что пароль был отправлен
        elif not request.form.get("password"):
            return apology("must provide password")

        # Ensure passwordagain was submitted
        # Убедитесь, что повторный пароль был отправлен
        elif not request.form.get("confirmation"):
            # make sure that passwords are equivalent, a duplicate password
            # убедитесь, что пароли эквивалентны, дублированный пароль
            return apology("duplicate passwords, must retype password")

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Check whether such name already exists
        # Проверить существует ли уже такое имя
        if len(rows) == 1:
            # Имя пользователя уже используется, дублированный пользователь
            return apology("Username already in use, duplicate user")

        # make sure that passwords are equivalent, a duplicate password
        # убедитесь, что пароли эквивалентны, дублированный пароль
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("duplicate passwords, retype passwords")

        # encrypt password - шифровать пароль, добавить пользователя в БД
        hash = pwd_context.hash(request.form.get("password"))
        rows = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                          username=request.form.get("username"), hash=hash)

        # получить user_id
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # запомнить какой пользователь вошел в систему
        session["user_id"] = rows[0]["id"]

        # redirect user to home page - перенаправить пользователя на главную страницу
        flash("Successfully registered!!!")  # Успешно зарегистрирован!

        # перенаправить пользователя на домашнюю страницу
        return redirect(url_for("index"))

    # if user reached route via POST return register page
    # если пользователь достиг маршрута через POST верните страницу регистрации
    else:
        return render_template("register.html")


@app.route("/consumption", methods=["GET", "POST"])
@login_required
def consumption():
    """Consumption of parts - Расход деталей"""

    # if user reached route via POST
    # если пользователь достиг маршрута через POST
    if request.method == "POST":

        # ensure that the cipher has been sent
        # гарантировать, что шифр был отправлен
        if not request.form.get("consumption"):  # если не назван шифр детали во вкладке приход
            return apology("Must provide part_code")  # должен предоставить шифр детали

        # Ensure that the number of parts is named
        # гарантировать, что количество деталей названо
        elif not request.form.get("quantity"):
            return apology("Must provide quantity")  # должен предоставить кол-во деталей quantity

        # The number of quantity is returned to the quantity variable with request.form.get () function
        # в переменную quantity с функцией request.form.get() возвращается кол-во деталей
        quantity = request.form.get("quantity")
        #  Метод ищет по всей строке, но возвращает только первое найденное
        # совпадение c "\D". Обеспечивает кол-во деталей положительным и int
        if re.search(r"\D", quantity) != None:
            return apology("must provide int number")  # должен предоставить кол-во деталей целое
        if int(quantity) <= 0:
            # кол-во деталей должно быть положительным целым числом
            return apology("Quantity must be positive integer")

        # The variable code with the request.form.get () function looks for the part number
        # переменная code с функцией request.form.get() ищет шифр детали
        code = request.form.get("consumption")

        # Choosing from the database details form part cipher
        # Выбор из базы данных формы details шифра детали
        result = db.execute("SELECT * FROM details "
                            "WHERE part_code = :part_code",
                            part_code=code)

        # Choosing from the database process form part cipher
        # Выбор из базы данных формы process шифра детали
        existing = db.execute("SELECT * FROM process WHERE part_code = :part_code",
                              part_code=result[0]["part_code"])

        if len(existing) != 1:
            # У вас нет деталей для расхода
            return apology("You do not have the details for the expense")

        price = result[0]["price"]
        trnasact_price = int(quantity) * float(price)  # расчёт всей суммы стоимости деталей
        total_price = int(existing[0]["quantity"]) * float(price)
        total_price -= float(trnasact_price)

        # make sure that the user has enough stock for sale
        # убедитесь, что у пользователя достаточно деталей для расхода
        quantity_total = int(existing[0]["quantity"])

        # If the user entered a larger number than he has shares
        # Если пользователь ввёл большее число, чем у него есть деталей
        if int(quantity) > quantity_total:
            # You do not have the right amount of parts for this cipher for consumption
            # У вас недостаточно деталей данного шифра для расхода
            return apology("You do not have enough details")

        # Updating user data
        # Обновление данных пользователя
        db.execute("UPDATE process "
                   "SET quantity = quantity-:quantity, total_price = :total_price "
                   "WHERE part_code = :part_code;",
                   quantity=quantity, total_price=hrn(total_price),
                   part_code=result[0]["part_code"])

        username = db.execute("SELECT username FROM users WHERE id=:id", id=session["user_id"])

        # update history - история обновления, Вставить в истории (шифр, наименование, цена, id, количество деталий)
        db.execute("INSERT INTO historys (id, username, part_code, detail_name, price, total_price, quantity) "
                   "VALUES ( :id, :username, :part_code, :detail_name, :price, :total_price, :quantity);",
                   id=session["user_id"], username=username[0]["username"], part_code=result[0]["part_code"],
                   detail_name=result[0]["detail_name"], price=price, total_price=hrn(total_price), quantity=-int(quantity))

        flash("Success!")  # Успех
        flash("Операция расхода деталей проведена успешно!")
        return redirect(url_for("index"))
    else:

        # Выбор из базы данных формы details шифра детали
        rows = db.execute("SELECT part_code FROM details ")

        # Возврат запроса в coming.html
        return render_template("consumption.html", choicecode=rows)


@app.route("/password", methods=["GET", "POST"])
@login_required
def password():
    """ Change password - Изменение пароля """

    # User reached route via POST (as by submitting a form via POST)
    # Пользователь достиг маршрута через POST (как, отправив форму через POST)
    if request.method == "POST":

        # Ensure password was submitted - Убедитесь, что пароль был отправлен
        if not request.form.get("password"):
            return apology("must provide password")  # должен предоставить пароль

        # Ensure passwordagain was submitted - Убедитесь, что повторный пароль был отправлен
        elif not request.form.get("confirmation"):
            # должен предоставить пароль повторно
            return apology("must provide password again")

        # query database for username - запрашивать базу данных для имени пользователя, обеспечить уникальное имя пользователя
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # убедитесь, что пароли эквивалентны
        if request.form.get("password") != request.form.get("confirmation"):
            # дублированный пароль, повторный пароль
            return apology("duplicate passwords, retype passwords")

        # encrypt password - шифровать пароль, добавить пользователя в БД
        hash = pwd_context.hash(request.form.get("password"))
        rows = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                          username=request.form.get("username"), hash=hash)

        db.execute("UPDATE users SET hash = :hash WHERE id = :id", hash=hash, id=session["user_id"])

        flash("Password changed!")  # Пароль был изменён!

        # перенаправить пользователя на домашнюю страницу
        # return render_template("index.html")
        return redirect(url_for("index"))

    # if user reached route via POST return register page
    # если пользователь достиг маршрута через POST верните страницу регистрации
    else:
        return render_template("password.html")


def errorhandler(e):
    """Handle error - Ошибка обработки """
    return apology(e.name, e.code)


# listen for errors - слушать ошибки
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
