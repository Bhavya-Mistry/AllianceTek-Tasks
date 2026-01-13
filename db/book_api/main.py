from flask import Flask, request, jsonify
from database import SessionLocal, engine
from models import Books, Base


app = Flask(__name__)


Base.metadata.create_all(bind=engine)

app.route("/bookcreate",methods=["POST"])
def bookcreate():
    db = SessionLocal()

    data = request.json

    book = Books(
        title=data["title"],
        author=data["author"],
        pages=data["pages"]
    )


    db.add(book)

    db.commit()

    db.refresh(book)

    db.close()

    return jsonify(
        {
            "message":"user created",
            "id":book.id
        }
    )


app.route("/bookget", methods=["GET"])
def bookread():
    db = SessionLocal()

    book = db.query(Books).all()

    db.close()

    result = []

    for b in book:
        result.append(
            {
                "id":b.id,
                "title":b.title,
                "author":b.author,
                "pages": b.pages
            }
        )
    return jsonify(result)


if __name__=="__main__":
    app.run(debug=True)