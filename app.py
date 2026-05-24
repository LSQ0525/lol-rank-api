from flask import Flask, Response

app = Flask(__name__)

@app.route("/")
def home():
    return Response("API is running", mimetype="text/plain")

@app.route("/krrank")
def krrank():
    return Response("KR route is working", mimetype="text/plain")
