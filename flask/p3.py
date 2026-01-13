from flask import Flask, request, make_response


app = Flask(__name__)

@app.route("/hello")
def hello():
    return "Heloooowwww", 201


@app.route("/hellowww")
def helloww():
    response = make_response("hi")
    response.status_code=202
    response.headers['content-type'] = 'applicarion/etc'
    return response


@app.route("/greet/<name>")
def greet(name):
    return f"Hello {name}"



@app.route("/add/<int:num1>/<int:num2>")
def add(num1,num2):
    return f"{num1}+{num2} = {num1+num2}"



@app.route("/handle_url_params")
def handle_prarams():
    # return str(request.args)
    if "greetings" in request.args.keys() and "name" in request.args.keys():

        greetings = request.args.get("greetings")
        name = request.args.get("name")
        return f"{greetings },{name}"
    
    else:

        return "some parameters are missing" 


if __name__=="__main__":
    app.run(debug=True)