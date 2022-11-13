from datetime import datetime,timedelta

from mongoengine import IntField
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_mongoengine import MongoEngine
ROLES = ('MANAGER', 'EMPLOYEE')
AVATARS = ('https://robohash.org/3EC.png?set=set4','https://robohash.org/293.png?set=set4','https://robohash.org/ZOB.png?set=set4')
db = MongoEngine()

class User(UserMixin, db.Document):
    # User authentication information
    username = db.StringField(required=True)
    password_hash = db.StringField()
    # User information
    first_name = db.StringField(default='')
    last_name = db.StringField(default='')
    # Relationships
    role = db.StringField(default='', choices = ROLES)
    avatar =  db.StringField(default='', choices = AVATARS)
    Manager = db.StringField(default='')
    def get_role (self):
        return self.role
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Task(UserMixin,db.Document):
    employee = db.StringField(default='')
    manager = db.StringField(default='')
    task_text = db.StringField(default='missing text')
    assign_date = db.DateTimeField(default=datetime.utcnow())
    due_date = db.DateTimeField(default=datetime.utcnow()+timedelta(days=7))

class Report(UserMixin,db.Document):
    employee = db.StringField(default='')
    manager = db.StringField(default='')
    report_text = db.StringField(default='')
    report_date = db.DateTimeField(default=datetime.utcnow())
   
