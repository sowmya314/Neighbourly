from flask import Flask, render_template, request, url_for, session, redirect, flash
from config import MONGO_URI
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "secretkey"

# creating db
client = MongoClient(MONGO_URI)
db = client.get_database('db')
users = db.get_collection('users')
tasks = db.get_collection('tasks')

@app.route("/")
def home():
    if "user" in session:
        if session["age-group"] == "Volunteer":
            return redirect(url_for("volunteer"))
        else:
            return redirect(url_for("elderly"))
    return render_template("index.html")


@app.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        address = request.form.get('address')
        age_group = request.form.get('age')
        name = request.form.get('name')
        if users.find_one({"email" : email}):
            flash("Email already exists, please login", "error")
        else:
            print("made it here")
            users.insert_one({"email": email, 
                              "name": name,
                              "password": password, 
                              "address": address, 
                              "age_group": age_group})
            flash("Account creation successful!", "info")
            return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if (users.find_one({"email" : email})):
            user = users.find_one({"email" : email})
            if user["password"] == password:
                session["user"] = email
                session["age-group"] = user["age_group"]
                session["name"] = user["name"]
                flash("Successfully logged in", "info")
                if session["age-group"] == "Volunteer":
                    return redirect(url_for("volunteer"))
                else:
                    return redirect(url_for("elderly"))
            else:
                flash("Invalid username or password. Please try again.", "error")
        else:
            flash("Invalid username or password. Please try again.", "error")
    else:
        if "user" in session:
            return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Successfully logged out!", "info")
    return redirect(url_for("login"))

@app.route("/volunteer")
def volunteer():
    if "user" in session:
        if session["age-group"] == "Volunteer":
            raw_tasks = list(tasks.find({"complete" : session["user"]}))
            accepted_items = []
            completed_items = []

            for task in raw_tasks:
                raw_date = task["fancy-date"]
                task_datetime = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M")
                if task_datetime >= datetime.now():
                    accepted_items.append(task)
                else:
                    completed_items.append(task)

            items = list(tasks.find({"complete" : False}))
            open_items = []

            for task in items:
                raw_date = task["fancy-date"]
                task_datetime = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M")
                if task_datetime >= datetime.now():
                    open_items.append(task)
                else:
                    tasks.delete_one({"_id": task["_id"]})

            return render_template("volunteer.html", items=open_items, accepted_items=accepted_items, completed_items=completed_items)
        else:
            return redirect(url_for("elderly"))
    else:
        return redirect(url_for("home"))
    
@app.route("/elderly", methods=["GET", "POST"])
def elderly():
    if request.method == "POST":
        task = request.form.get("task")
        date = request.form.get("date")
        email = session["user"]
        user = users.find_one({"email" : email})
        address = user["address"]
        dt = datetime.strptime(date, "%Y-%m-%dT%H:%M")    
        dt = dt.strftime("%B %d, %Y at %I:%M %p")    
        tasks.insert_one({"task" : task,
                          "date" : dt,
                          "fancy-date" : date,
                          "address" : address,
                          "email" : email,
                          "complete" : False,
                          "elderly-name" : user["name"],
                          "volunter-name" : ""})
        flash("Request successfully submitted!", "info")
        return render_template("elderly.html")
    else:
        if "user" in session:
            if session["age-group"] == "Volunteer":
                return redirect(url_for("volunteer"))
            return render_template("elderly.html")
        else:
            return redirect(url_for("home"))

# Elderly page for sent requests
@app.route("/sent-requests")
def sent_requests():
    if "user" in session:
        if session["age-group"] == "Elderly":
            raw_tasks = list(tasks.find({"email" : session["user"]}))
            accepted_items = []
            pending_items = []

            for task in raw_tasks:
                raw_date = task["fancy-date"]
                task_datetime = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M")
                if task_datetime >= datetime.now():
                    if task["complete"] == False:
                        pending_items.append(task)
                    else:
                        accepted_items.append(task)
            return render_template("sent_requests.html", accepted_items=accepted_items, pending_items=pending_items)
        else:
            return redirect(url_for("volunteer"))
    else:
        return redirect(url_for("home"))
@app.route("/accept/<task_id>")
def accept(task_id):
    tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {"complete": session["user"], "volunter-name": session["name"]}}
    )
    flash("Task accepted successfully!", "info")
    return redirect(url_for("volunteer"))

@app.route("/remove/<task_id>")
def remove(task_id):
    tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {"complete": False}}
    )
    flash("Task removed successfully!", "info")
    return redirect(url_for("volunteer"))

if __name__ == "__main__":
    app.run(debug=True, port=5001)

