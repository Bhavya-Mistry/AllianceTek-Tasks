from flask import Flask, render_template, request, redirect, url_for

app_name = Flask(__name__)

@app_name.route("/", methods=["GET"])
def welcome():
    return "root"

@app_name.route("/welcome", methods=["GET"])
def index():
    return "<h1>welcome</h1>"



#variable rule
@app_name.route("/success/<int:score>")
def success(score):
    return "Person has passed and the score is: "+str(score)

@app_name.route("/fail/<int:score>")
def fail(score):
    return "Person has failed and the score is: "+str(score)



@app_name.route("/form", methods=["GET", "POST"])
def form():
    if request.method=="GET":
        return render_template("form.html")
    else:
        maths=float(request.form['maths'])
        code=float(request.form['code'])
        sci=float(request.form['sci'])

        avg_marks = (maths+code+sci)/3

        res = ""
        if avg_marks>=50:
            res = "success"
        else:
            res = "fail"

        return redirect(url_for(res, score=avg_marks))

        # return render_template("form.html", score=avg_marks)

if __name__ == "__main__":
    app_name.run(debug=True)