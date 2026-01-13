from flask import Flask, request, jsonify
from models import Base, Student
from database import engine, SessionLocal

app = Flask(__name__)

Base.metadata.create_all(bind=engine)


@app.route("/students", methods=["GET", "POST"])
def students():
    db = SessionLocal()

    if request.method == "GET":
        students = db.query(Student).all()
        db.close()

        result = []
        for s in students:
            result.append({
                "id": s.id,
                "name": s.name,
                "email": s.email,
                "age": s.age
            })
        return jsonify(result)

    else:
        # POST
        data = request.json

        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        required_fields = ["name", "email", "age"]

        for i in required_fields:
            if i not in data:
                return jsonify(
                    {
                        "error":f"{i} is required"
                    }
                ),400
            
        existing_student = (
            db.query(Student)
            .filter(Student.email==data["email"])
            .first()
        )    

        if existing_student:
            return jsonify(
                {
                    "error":"student already exists"
                }
            ),409

        student = Student(
            name=data["name"],
            email=data["email"],
            age=data["age"]
        )

        db.add(student)
        db.commit()
        db.refresh(student)
        db.close()

        return jsonify({
            "message": "Student created",
            "id": student.id
        }), 201


@app.route("/students/<int:id>", methods=["GET", "PUT", "DELETE"])
def student_detail(id):
    db = SessionLocal()
    student = db.query(Student).filter(Student.id == id).first()

    if not student:
        db.close()
        return jsonify({"error": "Student not found"}), 404

    # GET one student
    if request.method == "GET":
        db.close()
        return jsonify({
            "id": student.id,
            "name": student.name,
            "email": student.email,
            "age": student.age
        })

    # UPDATE student
    if request.method == "PUT":
        data = request.json

        student.name = data["name"]
        student.email = data["email"]
        student.age = data["age"]

        db.commit()
        db.close()

        return jsonify({"message": "Student updated"})

    else:
        # DELETE student
        db.delete(student)
        db.commit()
        db.close()

        return jsonify({"message": "Student deleted"})


if __name__ == "__main__":
    app.run(debug=True)
