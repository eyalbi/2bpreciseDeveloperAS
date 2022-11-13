import time

from flask.globals import session
from models import User,Task,Report
import os
from boto.s3.connection import S3Connection, Bucket, Key
import smtplib
from email.message import EmailMessage
import PyPDF2
from datetime import datetime
from pdf_mail import sendpdf 
# import schedule
from datetime import date
import boto3
import boto
import boto.s3.connection
from flask import Flask, config, current_app, flash, Response, request, render_template_string, render_template, jsonify, redirect, url_for
from flask_mongoengine import MongoEngine
from bson.objectid import ObjectId
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
from flask_principal import Principal, Permission, RoleNeed, identity_changed, identity_loaded, Identity, AnonymousIdentity, UserNeed

from forms import LoginForm, RegistrationForm
from models import ROLES
import atexit

from apscheduler.schedulers.background import BackgroundScheduler

from flask_dropzone import Dropzone
basedir = os.path.abspath(os.path.dirname(__file__))
access_key = '**********************'
secret_key = '######################'


# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-MongoEngine settings
    MONGODB_SETTINGS = {
        'db': 'PdfMerger',
        'host': 'mongodb://localhost:27017/PdfMerger',
    }

app = Flask(__name__)
app.config.from_object(__name__+'.ConfigClass')




db = MongoEngine()
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# create role based auth
principals = Principal(app)

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except:
        redirect('index')


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    # Set the identity user object
    identity.user = current_user

    # Add the UserNeed to the identity
    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.id))

    # Assuming the User model has a list of roles, update the
    # identity with the roles that the user provides
    if hasattr(current_user, 'role'):
        identity.provides.add(RoleNeed(current_user.role))


@app.route('/new', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form1 = LoginForm()
    form2 = RegistrationForm()
    managers = User.objects(role = "MANAGER").all()

    if form1.validate_on_submit():
        user = User.objects(username=form1.username.data).first()
        if user is None or not user.check_password(form1.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form1.remember_me.data)
        identity_changed.send(current_app._get_current_object(),
                              identity=Identity(user.username))
        return redirect(url_for('index'))
    print(form2.errors)
    if form2.validate_on_submit():
            register(form2)
    else:
        form2.manager.choices = [(u.username, u.username) for u in User.objects.filter(role = 'MANAGER')]
        form2.manager.choices.append(("No Manager","No Direct Manager"))
    return render_template('new.html', title='Sign In', form1=form1, form2=form2)


@app.route('/logout')
def logout():
    logout_user()
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())
    return redirect(url_for('index'))


@app.route('/')
@app.route('/index')
@login_required
def index():
    user = User.objects(username=current_user.username).first()
    return render_template('Employee.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register(form):
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = form
    if form.validate_on_submit():  
        create_user(form)
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('index'))
    return render_template('new.html', title='Register', form=form)
    # else:
    #     flash('username Already exists')
    #     return redirect('/register')


def create_user(form):
    user = User(username=form.username1.data)
    user.role = form.role.data
    user.first_name = form.first_name.data
    user.last_name = form.last_name.data
    user.set_password(form.password1.data)
    user.avatar = form.avatar.data
    user.Manager = form.manager.data
    user.save()


@app.route('/EmployeeDetails', methods=['POST'])
@login_required
def Employee_details():
    username = request.form.get('username')
    employee = User.objects(username=username).first()
    manager = User.objects(username=employee.Manager).first()
    myEmployees = User.objects(Manager=username).all()
    myTasks = Task.objects(employee=username).all()
    if manager:
        return render_template('EmployeeDetails.html', title='EmployeeDetailes', myEmployees=myEmployees,
                               employee=employee, manager=manager,myTasks=myTasks)
    else:
        return render_template('EmployeeDetails.html', title='EmployeeDetailes', myEmployees=myEmployees,
                               employee=employee, manager=employee,myTasks=myTasks)
    # return render_template('EmployeeDetails.html', title='EmployeeDetailes',myEmployees = myEmployees,employee=employee, manager=manager)


@app.route('/EmployeeList', methods=['POST', 'GET'])
@login_required
def EmployeeList():
    
    user = User.objects(username=current_user.username).first()
    employeeList = User.objects.all()
    if request.method == 'GET':
        return render_template('EmployeesList.html', employeesList = employeeList)


@app.route('/Customer/myProfile', methods=['POST', 'GET'])
@login_required
def myprofile():
    user = User.objects(username=current_user.username).first()
    return render_template('myProfile.html', title='myProfile', user=user)


@app.route('/ReportModal', methods=['POST', 'GET'])
@login_required
def Report_Modal():
    if request.method == 'POST':
        manager = request.form.get("reportManager")
        employee = request.form.get("reportUser")
        return render_template("Modal.html", manager=manager, employee=employee,taskFlag=False)
    return redirect('index')


@app.route('/CreateReport', methods=['POST', 'GET'])
@login_required
def create_report():
    if request.method == 'POST':
        manager = User.objects(username=request.form.get("reportManager")).first()
        employee = User.objects(username=request.form.get("reportUser")).first()
        myEmployees = User.objects(Manager=employee.username).all()
        myTasks = Task.objects(employee=employee.username).all()
        reportText = request.form.get("ReportText")
        CreateReport(manager.username, employee.username, reportText)
        if manager:
            return render_template('EmployeeDetails.html', title='EmployeeDetailes',myEmployees=myEmployees,
                                   employee=employee, manager=manager,myTasks=myTasks)
        else:
            return render_template('EmployeeDetails.html', title='EmployeeDetailes', myEmployees=myEmployees,
                                   employee=employee, manager=employee,myTasks=myTasks)
    return redirect('index')


def CreateReport(manager,employee,reportText):
    report = Report()
    report.manager = manager
    report.employee = employee
    report.report_text = reportText
    report.report_date = datetime.utcnow()
    report.save()


@app.route('/CreateTask', methods=['POST', 'GET'])
@login_required
def create_task():
    if request.method == 'POST':
        manager = User.objects(username=request.form.get("taskManager")).first()
        employee = User.objects(username=request.form.get("taskUser")).first()
        myEmployees = User.objects(Manager=manager.username).all()
        TaskText = request.form.get("taskText")
        due_date = request.form.get("due_date")
        CreateTask(manager.username, employee.username, TaskText,due_date)
        if manager.Manager and manager.Manager == "No Manager":
            return render_template('EmployeeDetails.html', title='EmployeeDetailes',
                                   myEmployees=myEmployees, employee=manager, manager=manager)
        else:
            Manager = User.objects(username=manager.Manager).first()
            return render_template('EmployeeDetails.html', title='EmployeeDetailes', myEmployees=myEmployees,
                                   employee=manager, manager=Manager)
    return redirect('index')


@app.route('/AssignTask', methods=['POST', 'GET'])
@login_required
def assign_task():
    if request.method == 'POST':
        manager = request.form.get("TaskManager")
        employee = request.form.get("TaskUser")
        return render_template("Modal.html", manager=manager, employee=employee, taskFlag=True)
    return redirect('index')


def CreateTask(manager, employee, taskText, dueDate):
    task = Task()
    task.manager = manager
    task.employee = employee
    task.task_text = taskText
    task.assign_date = datetime.utcnow()
    task.due_date = datetime.strptime(dueDate,"%Y-%m-%d").date()
    task.save()


if __name__ == '__main__':
    app.run()



