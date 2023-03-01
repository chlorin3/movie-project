import os
from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired
import requests

MOVIE_DB_API_KEY = os.environ.get("MOVIE_DB_API_KEY")
MOVIE_DB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
MOVIE_DB_DETAILS_URL = "https://api.themoviedb.org/3/movie"


app = Flask(__name__)
app.config['SECRET_KEY'] = 'myverysecretkey'
Bootstrap(app)

# create db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movie-collection.db'
db = SQLAlchemy(app)


# create table
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    year = db.Column(db.Integer)
    description = db.Column(db.String(250), nullable=False)
    rating = db.Column(db.Float, nullable=True)
    ranking = db.Column(db.Integer, nullable=True)
    review = db.Column(db.String(250), nullable=True)
    img_url = db.Column(db.String(250), nullable=False)


with app.app_context():
    db.create_all()


class EditForm(FlaskForm):
    new_rating = FloatField("Your Rating Out of 10 e.g. 7.5", validators=[DataRequired()])
    new_review = StringField("Your Review", validators=[DataRequired()])
    submit = SubmitField("Done")


class AddForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")


@app.route("/")
def home():
    # select all movies and order them by rating
    all_movies = Movie.query.order_by(Movie.rating).all()

    # rank movies according to their rating
    for i in range(len(all_movies)):
        all_movies[i].ranking = len(all_movies) - i

    # commit changes
    db.session.commit()
    return render_template("index.html", movies=all_movies)


@app.route("/edit", methods=["GET", "POST"])
def edit():
    """Edit rating and review"""
    form = EditForm()
    movie_id = request.args.get("id")
    movie = Movie.query.get(movie_id)

    # if POST
    if form.validate_on_submit():
        movie.rating = form.new_rating.data
        movie.review = form.new_review.data
        db.session.commit()
        return redirect(url_for("home"))

    # if GET
    return render_template("edit.html", movie=movie, form=form)


@app.route("/delete")
def delete():
    """Delete movie from db"""
    movie_id = request.args.get("id")
    movie = Movie.query.get(movie_id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/add", methods=["GET", "POST"])
def add_movie():
    form = AddForm()
    if form.validate_on_submit():
        title = form.title.data

        parameters = {
            "api_key": MOVIE_DB_API_KEY,
            "query": title
        }
        response = requests.get(MOVIE_DB_SEARCH_URL, params=parameters)

        movies = response.json()["results"]
        return render_template("select.html", movies=movies)
    return render_template("add.html", form=form)


@app.route("/select")
def select():
    movie_id = request.args.get("id")

    if not movie_id:
        return redirect(url_for("home"))

    parameters = {
        "api_key": MOVIE_DB_API_KEY,
        "language": "en-US"
    }
    response = requests.get(f"{MOVIE_DB_DETAILS_URL}/{movie_id}", params=parameters)
    data = response.json()
    new_movie = Movie(
        title=data["title"],
        year=int(data["release_date"].split("-")[0]),
        description=data["overview"],
        img_url=f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
    )
    db.session.add(new_movie)
    db.session.commit()
    return redirect(url_for("edit", id=new_movie.id))


if __name__ == '__main__':
    app.run(debug=True)
