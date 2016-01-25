#!flask/Scripts/python
from flask import Flask, render_template, request, abort

from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from flask.ext.restless import APIManager
from flask.ext.login import LoginManager, login_user, logout_user, current_user
import json

def add_cors_headers(response):
	response.headers['Access-Control-Allow-Origin'] = 'http://localhost:8100'
	response.headers['Access-Control-Allow-Credentials'] = 'true'
	response.headers['Access-Control-Allow-Headers'] = 'Content-type'
	# Set whatever other headers you like...
	return response

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.after_request(add_cors_headers)

db = SQLAlchemy(app)
manager = APIManager(app, flask_sqlalchemy_db=db)
login_manager = LoginManager(app)

userPost = db.Table('user-post',
	db.Column('user_id', db.String(8), db.ForeignKey('user.id'), nullable=False),
	db.Column('post_id', db.Integer, db.ForeignKey('post.id'), nullable=False)
)
postSubject = db.Table('post-subject',
	db.Column('post_id', db.Integer, db.ForeignKey('post.id'), nullable=False),
	db.Column('subject_id', db.Integer, db.ForeignKey('subject.id'), nullable=False)
)
postPlace = db.Table('post-place',
	db.Column('post_id', db.Integer, db.ForeignKey('post.id'), nullable=False),
	db.Column('place_id', db.Integer, db.ForeignKey('place.id'), nullable=False)
)

class User(db.Model):
	id = db.Column(db.String(8), primary_key=True)
	name = db.Column(db.String(), nullable=False)
	password = db.Column(db.String(), nullable=False)
	posts = db.relationship('Post', backref='op', lazy='dynamic')

	def __init__(self, id, name, password):
		self.id = id
		self.name = name
		self.set_password(password)

	def set_password(self, password):
		self.password = generate_password_hash(password)

	def check_password(self, password):
		return check_password_hash(self.password, password)

	@property
	def is_authenticated(self):
		return True

	@property
	def is_active(self):
		return True

	@property
	def is_anonymouse(self):
		return False
	
	def get_id(self):
		return str(self.id)
	

class Post(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	content = db.Column(db.String(120), nullable=False)
	op_id = db.Column(db.String(8), db.ForeignKey('user.id'), nullable=False)
	places = db.relationship('Place', secondary=postPlace, backref=db.backref('posts', lazy='dynamic'))
	subjects = db.relationship('Subject', secondary=postSubject, backref=db.backref('posts', lazy='dynamic'))
	people = db.relationship('User', secondary=userPost, backref=db.backref('tagged', lazy='dynamic'))

class Place(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(), unique=True, nullable=False)

class Subject(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(), unique=True, nullable=False)

manager.create_api(User, methods=['POST', 'DELETE'])
manager.create_api(User, methods=['GET'], exclude_columns=['password'])


@login_manager.user_loader
def load_user(user_id):
	return User.query.get(str(user_id))

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
	try:
		user = User.query.filter_by(id=request.json['id']).first()
		if user == None or not user.check_password(request.json['password']):
			return abort(401)
		
		login_user(user)
		return json.dumps(dict(id=current_user.id, name=current_user.name, isAuthenticated=True))
	except KeyError:
		return abort(400)

@app.route('/logout')
def logout():
	logout_user()
	return ""

@app.route('/current-user')
def currentUser():
	if current_user.is_authenticated:
		return json.dumps(dict(id=current_user.id, name=current_user.name, isAuthenticated=True))
	else:
		return abort(401)

if __name__ == '__main__':
	app.secret_key = 'super secret key'
	app.config['SESSION_TYPE'] = 'filesystem'
	app.run(debug=True)