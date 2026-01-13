from flask import Flask, render_template

app = Flask(__name__, template_folder='templates')



@app.route("/")
def index():
    myvalue= "bhavya"
    myresults= 10+20
    mylist = [10,20,30]
    return render_template("p1.html", mylist=mylist)


if __name__=="__main__":
    app.run(debug=True)