from flask import Flask,render_template,request,url_for,redirect
from pickle import load
import sqlite3
import numpy as np
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin,LoginManager, login_user, login_required, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField
from wtforms.validators import InputRequired,Length,ValidationError
from flask_bcrypt import Bcrypt

app = Flask(__name__)
db_fert = sqlite3.connect("fertilizeDB.db",check_same_thread=False)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "paraproj"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model,UserMixin):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(20),nullable=False,unique=True)
    phonenum = db.Column(db.String(14),nullable=False,unique=True)
    password = db.Column(db.String(80),nullable=False)

class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    phonenum = StringField(validators=[InputRequired(), Length(min=13, max=14)], render_kw={"placeholder": "Phonenumber"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError('That username already exists. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/login',methods=['GET','POST'])
def login():
    global ans,name,error
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return render_template('index.html', user_name = user.username)
                #return redirect(url_for('analyze'))
        else:
            error = "Username or Password is incorrect"
            return render_template('login.html', form=form, error=error)
    return render_template('login.html',form=form)

@app.route('/register',methods=['POST','GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, phonenum=form.phonenum.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html',form=form)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@login_required
@app.route('/analyze')
def analyze():
    return render_template("main.html")

@app.route('/output',methods=['POST','GET'])
def output():
    if request.method=='POST':
        soil = request.form['soil']
        n = request.form['nitrogen']
        p = request.form['phosphorus']
        k = request.form['potassium']
        temperature = request.form['temperature']
        humidity = request.form['humidity']
        ph = request.form['ph']
        rainfall = request.form['rainfall']
        data = [np.array([n,p,k,temperature,humidity,ph,rainfall],dtype=float)]
        predict = prediction(data)
        cursor = db_fert.execute(f'''SELECT CONTEXT,VIDEO,PROC FROM FERT WHERE CROP_NAME="{predict}"''')
        send = cursor.fetchall()
        return render_template("output.html",predict = predict, content=send[0][0] , recommend =send[0][1],link=send[0][2])

@app.route('/fertile/<predict>')
def fertile(predict):
    cursor = db_fert.execute(f'''SELECT PRIMARY_FERT,CONTENT,LINK FROM FERT WHERE CROP_NAME="{predict}"''')
    send = cursor.fetchall()
    return render_template('fertilizer.html',predict = predict, fertilizer= send[0][0],
                           content = send[0][1], link=send[0][2])

@app.route("/fertilelist/<predict>")
def list(predict):
    cursor = db_fert.execute(f'SELECT * FROM FERTILIZE')
    fertilize = cursor.fetchall()
    return render_template('fertilizerlist.html',predict=predict,fertilizer=fertilize)

@app.route('/forecast/<predict>',methods=['POST','GET'])
def forecast(predict):
    if request.method=='POST':
        acre = request.form['acre']
        values = db_fert.execute(f'''SELECT PRICE,YIELD FROM FORECAST WHERE CROP_NAME="{predict}"''')
        values = values.fetchall()
        current = int(values[0][0])/100
        earn = values[0][0] * values[0][1]
        sales = np.round(float(acre) * earn,2)
        return render_template('forecast.html', predict=predict,flag=True, current= current,yields= values[0][1],
                               earn= earn, sales= sales)
    elif request.method=='GET':
        return render_template('forecast.html',predict = predict, flag= False)

@app.route('/tools/<predict>')
def tools(predict):
    cursor = db_fert.execute(f'SELECT * FROM TOOLS')
    tools = cursor.fetchall()
    return render_template('tools.html',predict=predict,tools=tools)

def prediction(data):
    fertilizer = "fert.pkl"
    label = ["Rice", "Maize", 'Jute', 'Cotton', 'Coconut', 'Papaya', 'Orange', 'Apple', 'Muskmelon', 'Watermelon',
             'Grapes', 'Mango', 'Banana', 'Pomegranate', 'Lentil', 'Blackgram', 'Mungbean', 'Mothbeans',
             'Pigeonpeas', 'Kidneybeans', 'Chickpea', 'Coffee']
    model = load(open(fertilizer, 'rb'))
    pred = model.predict(data)
    return label[pred[0]]

if __name__== '__main__':
    app.run()