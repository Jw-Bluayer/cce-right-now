#!flask/Scripts/python
from flask import Flask, render_template, request, abort

from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from flask.ext.restless import APIManager, ProcessingException
from flask.ext.login import LoginManager, login_user, logout_user, current_user
import json
from datetime import datetime

def add_cors_headers(response):
	origin = request.headers.get('Origin')
	response.headers['Access-Control-Allow-Origin'] = origin if origin in ['http://localhost:8100', 'file://', 'null'] else ''
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
userComment = db.Table('user-comment',
	db.Column('user_id', db.String(8), db.ForeignKey('user.id'), nullable=False),
	db.Column('comment_id', db.Integer, db.ForeignKey('comment.id'), nullable=False)
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
	comments = db.relationship('Comment', backref='cmter', lazy='dynamic')

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
	op_id = db.Column(db.String(8), db.ForeignKey('user.id'), default=lambda: current_user.id, nullable=False)
	time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	image = db.Column(db.String())
	places = db.relationship('Place', secondary=postPlace, backref=db.backref('posts', lazy='dynamic'))
	subjects = db.relationship('Subject', secondary=postSubject, backref=db.backref('posts', lazy='dynamic'))
	people = db.relationship('User', secondary=userPost, backref=db.backref('taggedPost', lazy='dynamic'))
	comments = db.relationship('Comment', backref='post', lazy='dynamic')

class Place(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(), unique=True, nullable=False)

class Subject(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(), unique=True, nullable=False)

class Comment(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
	user_id = db.Column(db.String(8), db.ForeignKey('user.id'), nullable=False)
	time = db.Column(db.DateTime, default=datetime.utcnow(), nullable=False)
	content = db.Column(db.String(), nullable=False)
	people = db.relationship('User', secondary=userComment, backref=db.backref('taggedComment', lazy='dynamic'))

def postGetPost(item):
	item['hasImage'] = True if item['image'] else False
	diff = datetime.utcnow()-datetime.strptime(item['time'], '%Y-%m-%dT%H:%M:%S.%f')

	year = int(diff.days/365)
	month = int(diff.days/30)
	day = int(diff.days)
	hour = int(diff.seconds/3600)
	minute = int(diff.seconds/60)
	item['ago'] = ("%d year%s" % (year, 's' if year > 1 else '')) if year else ("%d month%s" % (month, 'es' if month > 1 else '')) if month else ("%d day%s" % (day, 's' if day > 1 else '')) if day else ("%d hour%s" % (hour, 's' if hour > 1 else '')) if hour else ("%d min%s" % (minute, 's' if minute > 1 else '')) if minute else "Just now"
	item['now'] = not (year or month or day or hour) and minute < 6
	return item

def postGetSinglePost(result, **kw):
	result = postGetPost(result)

def postGetManyPost(result, **kw):
	result['objects'] = list(map(postGetPost, result['objects']))

def parsePosting(data, **kw):
	if not current_user.is_authenticated:
		raise ProcessingException(description='Login first!', code=401)

	data['id'] = None

manager.create_api(User, methods=['POST', 'DELETE'])
manager.create_api(User, methods=['GET'], exclude_columns=['password', 'posts.op_id', 'posts.op.password'])

manager.create_api(Post, methods=['GET'], exclude_columns=['op.password', 'op_id'], postprocessors={'GET_SINGLE': [postGetSinglePost], 'GET_MANY': [postGetManyPost]})
manager.create_api(Post, methods=['POST'], include_columns=['id', 'content'], preprocessors={'POST': [parsePosting]})


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
	app.secret_key = "N$KFgm*^wrKpN_x4$wnv#+vj-tU6Rh8Z"
	app.config['SESSION_TYPE'] = 'filesystem'
	app.run(debug=True, host='0.0.0.0')