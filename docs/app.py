from flask import Flask, send_from_directory
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "Welcome to the docs directory. Available files:<br>" + "<br>".join(
        f'<a href="/{file}">{file}</a>' for file in os.listdir('.') if file.endswith('.html')
    )

@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    app.run(debug=True)
