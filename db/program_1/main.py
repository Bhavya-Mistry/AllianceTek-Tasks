from flask import Flask, request, jsonify
from database import SessionLocal, engine
from models import User, Base

app = Flask(__name__)

Base.metadata.create_all(bind=engine)

@app.route("/postuser", methods=["POST"])
def postuser():
    db = SessionLocal()

    data = request.json

    user = User(
        name=data["name"],
        email=data["email"],
        age=data["age"]
    )

    db.add(user)

    db.commit()

    db.refresh(user)

    db.close()


    return jsonify(
        {
            "message":"User created",
            "id":user.id
        }
    )


@app.route("/getusers", methods=["GET"])
def getuser():
    db=SessionLocal()

    users= db.query(User).all()

    db.close()

    result=[]
    
    for user in users:
        result.append(
            {
                "id":user.id,
                "name":user.name,
                "email":user.email,
                "age":user.age
            }
        )

    return jsonify(result)


if __name__=="__main__":
    app.run(debug=True)