import datetime as dt
import config
import forms
import os

from flask import Flask, render_template, redirect, request, flash, abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_ckeditor import CKEditor

from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_gravatar import Gravatar
from functools import wraps


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
# OLD app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)


# GRAVATAR SETUP FOR USER COMMENTS
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False,
                    use_ssl=False, base_url=None)


##CONNECT TO DB
# NEW app.config (PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL",  "sqlite:///blog.db")
# OLD app.config (SQLite) app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLE
class BlogPost(db.Model):
    # TO CREATE TABLE IN THE MAIN.DB
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    # SET FOREIGN KEY FOR THIS FIELD, ID FROM THE USERS TABLE
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # DEFINE THE RELATION WITH THE USERS TABLE
    author = relationship("User", back_populates="posts")
    # DEFINE THE RELATIONSHIP WITH THE COMMENTS TABLE
    comments = relationship("Comment", back_populates="parent_post")
    
    img_url = db.Column(db.String(250), nullable=False)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    # TO SET FOREIGN KEYS
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # DEFINE THE RELATIONSHIPS WITH THE OTHER TABLES
    parent_post = relationship("BlogPost", back_populates="comments")
    comment_author = relationship("User", back_populates="comments")

    text = db.Column(db.Text, nullable=False)

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    # DEFINE THE RELATIONSHIP WITH THE BLOG_POSTS TABLE
    posts = relationship("BlogPost", back_populates="author")
    # DEFINE THE RELATION WITH COMMENTS TABLE
    comments = relationship("Comment", back_populates="comment_author")
# db.create_all()
# db.session.commit()


login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # ADMIN IS THE FIRST ENTRY IN THE USERS TABLE
        # IF NOT ADMIN, ABORT THE REQUEST
        if not current_user.is_authenticated or current_user. id != 1:
            return abort(403)
        # IF AMIN, CONTINUTE TO THE REQUESTED ROUTE
        return func(*args, **kwargs)
    return wrapper


def get_current_year():
    """Returns the current year as INT."""
    return dt.datetime.now().year


def get_current_date():
    """Returns the current date as a STR."""
    return dt.datetime.now().strftime("%B %d, %Y")


@app.route('/')
def home():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, year=get_current_year(), logged_in=current_user.is_authenticated)


@app.route("/post/<int:index>", methods=["GET", "POST"])
def show_post(index):
    # requested_post = BlogPost.query.get(index)
    comment_form = forms.CommentForm()
    blog_post = BlogPost.query.get(index)
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            # ALERT USER TO LOG IN OR REGISTER TO COMMENT
            flash("You need to login or register to comment.")
            return redirect("/login")

        new_comment = Comment(
            text=comment_form.comment.data,
            comment_author=current_user,
            parent_post=blog_post
        )
        db.session.add(new_comment)
        db.session.commit()
        # CLEAR THE COMMENT FIELD AFTER
        comment_form.comment.data = ""

    if blog_post:
        return render_template("post.html", post=blog_post, form=comment_form, year=get_current_year(), logged_in=current_user.is_authenticated)

    # IF SUCH POST ID DOES NOT EXIST
    return redirect("/")


@app.route("/about")
def about():
    return render_template("about.html", year=get_current_year(), logged_in=current_user.is_authenticated)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        mimeMessage = config.MIMEMultipart()
        mimeMessage["from"] = "pauagawin21@gmail.com"
        mimeMessage["to"] = request.form["email"]
        mimeMessage["subject"] = f"{config.SUBJECT_TEXT}To: {mimeMessage['to']} From: {mimeMessage['from']}"
        emailMsg = f"{request.form['message']}"
        mimeMessage.attach(config.MIMEText(emailMsg, "plain"))
        # mimeMessage.attach(MIMEText(emailMsg, "plain"))
        raw_string = config.base64.urlsafe_b64encode(mimeMessage.as_bytes()).decode()
        # raw_string = base64.urlsafe_b64encode(mimeMessage.as_bytes()).decode()

        email_response = config.service.users().messages().send(userId='me', body={"raw": raw_string}).execute()
        # email_response = service.users().messages().send(userId='me', body={"raw": raw_string}).execute()
        print(email_response)
        
    return render_template("contact.html", year=get_current_year(), logged_in=current_user.is_authenticated)


# DECORATOR FOR ADMIN USER ONLY
@app.route("/add", methods=["GET", "POST"])
@admin_only
def add_post():
    form = forms.CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            date=get_current_date(),
            body=form.body.data,
            author=current_user,
            img_url=form.img_url.data
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect("/")
    return render_template("make-post.html", heading="New Post", form=form, year=get_current_year(), logged_in=current_user.is_authenticated)


@app.route("/edit/<int:index>", methods=["GET", "POST"])
@admin_only
def edit_post(index):
    post = BlogPost.query.get(index)
    if post:
        form = forms.CreatePostForm(
            title=post.title,
            subtitle=post.subtitle,
            img_url=post.img_url,
            author=current_user,
            body=post.body
        )
        if form.validate_on_submit():
            post.title = form.title.data
            post.subtitle = form.subtitle.data
            post.body = form.body.data
            #post.author = form.author.data
            post.img_url = form.img_url.data
            db.session.commit()

            return redirect(f"/post/{post.id}")
        return render_template("make-post.html", heading="Edit Post", form=form, year=get_current_year(), logged_in=current_user.is_authenticated)
    return redirect("/")


@app.route("/delete/<int:index>", methods=["GET", "POST"])
@admin_only
def delete_post(index):
    cafe = BlogPost.query.get(index)
    if cafe:
        db.session.delete(cafe)
        db.session.commit()
    return redirect("/")


# USER REGISTRATION AND LOGIN
@app.route("/register", methods=["GET", "POST"])
def register():
    register_form = forms.RegisterForm()
    if register_form.validate_on_submit():
        # CHECK IF EMAIL IS ALREADY IN DB
        found_user = User.query.filter_by(email=register_form.email.data).first()
        if found_user:
            # SET MESSAGE TO DISPLAY AND REDIRECT TO LOGIN PAGE
            flash("You've already signed up with that email, log in instead.")
            return redirect("/login")
        
        else:
            password_hash = generate_password_hash(password=register_form.password.data, method="pbkdf2:sha256", salt_length=8)
            new_user = User(
                name=register_form.name.data,
                email=register_form.email.data,
                password=password_hash,
            )
            db.session.add(new_user)
            db.session.commit()
            # LOG IN AS THE NEW USER AND GO BACK TO HOME
            login_user(new_user)
            return redirect("/")
    return render_template("/register.html", form=register_form, year=get_current_year(), logged_in=current_user.is_authenticated)


@app.route("/login", methods=["GET", "POST"])
def login():
    login_form = forms.LoginForm()
    if login_form.validate_on_submit():
        # TO FIND THE EMAIL USER IN THE DB
        found_user = User.query.filter_by(email=login_form.email.data).first()
        if found_user:
            # TO VERIFIY THE PASSWORD
            verified = check_password_hash(pwhash=found_user.password, password=login_form.password.data)
            if verified:
                # USE THE FLASK LOGIN MANAGER TO LOGIN
                login_user(found_user)
                return redirect("/")

            # IF INCORRECT PASSWORD
            else:
                flash("Password is incorrect, please try again")
                return redirect("/login")

        # IF EMAIL DOES NOT EXIST IN DB
        else:
            flash("User does not exist, try to register instead.")
            return redirect("/register")
    return render_template("login.html", form=login_form, year=get_current_year(), logged_in=current_user.is_authenticated)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


if __name__ == "__main__":
    app.run()