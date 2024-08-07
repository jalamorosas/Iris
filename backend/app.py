from flask import Flask, jsonify, request
from flask_cors import CORS

from Iris import WebAgent

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

#Getting user input from speech to text and creating selenium code to execute
@app.route('/command', methods=['POST'])
def command():
    # Get the text from the request data (text to speech)
    text = request.json.get('text')

    #Use the request text in the prompt to generate the webdriver code
    #selenium_code = prompt_engineering(text)

    #execute selenium code


#Taking in some text from content via bs4, feeding into generative ai
@app.route('/generate_text', methods=['POST'])
def generate_text():
    data = request.json
    text = data.get('text')
    print("Received text: " + text)
    webagent = WebAgent()
    response = webagent.run_voice(text)
    return jsonify(
        {
        'text': response
        }
    )
    
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5001)