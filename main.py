from flask import (Flask,
                   render_template,
                   request,
                   redirect,
                   url_for,
                   make_response,
                   flash,
                   session)
import hashlib
from datetime import datetime, date
import random, string
from config import users
import json

app = Flask(__name__)

def _id(collection):
    last_doc = collection.find_one(sort=[("_id", -1)])
    return last_doc["_id"] + 1 if last_doc else 1

@app.route('/')
def index():
    login = request.cookies.get('login')

    if login != None:
        return make_response(redirect(url_for('home')))
    # elif login == None:
    #     return render_template('index.html')

    return render_template('index.html',
                           action = '/profile' if login != None else '/login'
                        )

@app.route('/register')
def register():
    return render_template('register.html')
@app.route('/reg', methods=['POST', 'GET'])
def reg():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password2 = request.form.get('password2')

        is_exists = users.find_one({"username": username})

        if is_exists != None:
            return render_template('register.html', error='Користувач з таким ім\'ям користувача вже існує')

        if len(username) == 0 or len(password) == 0 or len(password2) == 0:
            return render_template('register.html', error='Введи усі дані')
        elif len(username) < 5 or len(username) > 20:
            return render_template('register.html', error='Ім\'я користувача від 5 до 20 символів')
        elif len(password) < 8 or len(password) > 20:
            return render_template('register.html', error='Пароль від 8 до 20 символів')
        elif password != password2:
            return render_template('register.html', error='Паролі не збігаються')
        else:
            md5 = hashlib.md5(password.encode()).hexdigest()

            current_date = datetime.now()
            date = current_date.strftime('%Y-%m-%d %H:%M:%S')

            query = {
                "_id": _id(users),
                "username": username,
                "password": md5,
                "date": date,
                "about": {
                    "text": "",
                    "city": "",
                    "habits_quantity": "",
                    "max_days": ""
                },
                "habits": [],
                "active": [],
                "achievements": []
            }
            users.insert_one(query)

            response = make_response(redirect(url_for('profile')))
            response.set_cookie('login', username, max_age=2592000)
            return response

@app.route('/login')
def login():
    return render_template('login.html')
@app.route('/log', methods=['POST', 'GET'])
def log():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        md5 = hashlib.md5(password.encode()).hexdigest()

        is_exists = users.find_one({"username": username, "password": md5})
        if is_exists == None:
            return render_template('login.html', error='Неправильний логін чи пароль')

        response = make_response(redirect(url_for('profile')))
        response.set_cookie('login', username, max_age=2592000)
        return response


@app.route('/profile')
def profile():
    username = request.cookies.get('login')

    avatar = username[:1].upper()

    user_data = users.find_one({"username": username})

    city = user_data["about"]["city"]
    about = user_data["about"]["text"]

    user_active = user_data['active']
    habits_len = len(user_data['habits'])

    return render_template('profile.html',
                           avatar = avatar,
                           username = username,
                           city = city,
                           about = about,
                           user_active = user_active,
                           habits_len = habits_len
                        )

@app.route('/city', methods=['POST', 'GET'])
def city():
    username = request.cookies.get('login')

    city = request.form.get('city')

    users.find_one_and_update(
        {"username": username},
        {"$set": {"about.city": city}}
    )

    user_actives = users.find_one({"username": username})["active"]

    for i in user_actives:
        users.update_one(
            {"username": username, "active.q": i["q"]},
            {"$set": {"active.$.city": city}}
        )

    return make_response(redirect(url_for('profile')))

@app.route('/about', methods=['POST', 'GET'])
def about():
    username = request.cookies.get('login')

    about = request.form.get('about')

    users.find_one_and_update(
        {"username": username},
        {"$set": {"about.text": about}}
    )

    return make_response(redirect(url_for('profile')))

@app.route('/home')
def home():
    username = request.cookies.get('login')

    query = [
        {"$match": {"username": {"$ne": username}}},
        {"$unwind": "$active"},
        {"$replaceRoot": {"newRoot": "$active"}},
        {"$sort": {"_id": 1}}
    ]

    users_actives = list(users.aggregate(query))

    return render_template('home.html',
                           users_actives = users_actives
                           )

@app.route('/new', methods=['POST', 'GET'])
def new():
    return render_template('new.html')

@app.route('/create', methods=['POST', 'GET'])
def create():
    username = request.cookies.get('login')

    title = request.form.get('title')
    text = request.form.get('description')
    goal = request.form.get('goal')

    characters = string.ascii_letters + string.digits
    q = ''.join(random.choice(characters) for _ in range(5))

    current_date = datetime.now()
    date = current_date.strftime('%Y-%m-%d %H:%M:%S')

    query = {
        "q": q,
        "author": username,
        "title": title,
        "text": text,
        "goal": goal,
        "date": date
    }

    users.update_one(
        {"username": username},
        {"$push": {"habits": query}}
    )

    return make_response(redirect(url_for('journal')))

@app.route('/journal', methods=['POST', 'GET'])
def journal():
    username = request.cookies.get('login')

    user_habits = users.find_one({"username": username})["habits"]
    user_city = users.find_one({"username": username})["about"]["city"]

    return render_template('journal.html',
                           user_habits = user_habits,
                           user_city = user_city
                        )

@app.route('/delete-habit')
def delete_habit():
    username = request.cookies.get('login')
    q = request.args.get('q')

    users.update_one(
        {"username": username},
        {"$pull": {"habits": {"q": q}}}
    )

    return make_response(redirect(url_for('journal')))

@app.route('/active_add')
def active_add():
    username = request.cookies.get('login')
    q = request.args.get('q')

    user_data = users.find_one({"username": username})

    habit = users.find_one(
        {"username": username},
        {"habits": {"$elemMatch": {"q": q}}}
    )['habits'][0]
    
    query = {
        "q": q,
        "title": habit["title"],
        "text": habit["text"],
        "city": user_data["about"]["city"],
        "goal": habit["goal"],
        "author": username,
        "days_author": "",
        "last_day_author": "",
        "procent_author": "",
        "mate": "",
        "days_mate": "",
        "last_day_mate": "",
        "procent_mate": ""  
    }

    users.update_one(
        {"username": username},
        {"$push": {"active": query}}
    )

    return make_response(redirect(url_for('profile')))

@app.route('/add_day')
def add_day():
    username = request.cookies.get('login')

    q = request.args.get('q')

    user_habit = users.find_one(
        {"username": username, "active.q": q},  
        {"active.$": 1}
    )

    # if user_habit['active'][0]['author'] == username:
    #     users.update_one(
    #         {"username": username, "active.q": q},
    #         {"$set": {"active.$.days_author": 1 if ...}}
    #     )

    return make_response(redirect(url_for('index')))

@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('index')))
    response.delete_cookie('login')
    return response

if __name__ == '__main__':
    # app.run(host='192.168.242.236', port='1111')
    app.run(host='0.0.0.0')