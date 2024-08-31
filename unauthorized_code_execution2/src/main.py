import os
import json
import uuid
import subprocess
from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import openai

app = Flask(__name__)

# Setup rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5 per minute"],
    storage_uri="memory://"
)

openai.api_key  = os.environ.get('API_KEY')

# Load flag
with open("flag", "r") as f:
    FLAG = f.read().strip()

import json
from datetime import datetime

def log_ip_request(ip_address):
    try:
        with open('ip_log.json', 'r') as f:
            log = json.load(f)
    except FileNotFoundError:
        log = {}

    if ip_address not in log:
        log[ip_address] = {"count": 0, "last_request": ""}

    log[ip_address]["count"] += 1
    log[ip_address]["last_request"] = datetime.now().isoformat()

    with open('ip_log.json', 'w') as f:
        json.dump(log, f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
@limiter.limit("5 per minute")
def query():
    prompt = request.json.get('prompt', '')
    
    if len(prompt) > 200:
        return jsonify({"error": "Prompt too long"}), 400

    try:
        log_ip_request(request.remote_addr)
        response = openai.ChatCompletion.create(
            model="gpt-4-0613",
            messages=[
                {"role": "system", "content": "您是一位數學問題解決助理。您可以建立並執行 Python 程式碼來協助解決數學問題。如果問題與數學無關，您就不會回答。"},
                {"role": "user", "content": prompt}
            ],
            functions=[{
                "name": "execute_python",
                "description": "Execute Python code",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The Python code to execute"
                        }
                    },
                    "required": ["code"]
                }
            }],
            function_call="auto"
        )

        message = response.choices[0].message

        if message.get("function_call"):
            function_name = message["function_call"]["name"]
            function_args = json.loads(message["function_call"]["arguments"])
            
            if function_name == "execute_python":
                code = function_args["code"]
                result = execute_python_code(code)
                
                second_response = openai.ChatCompletion.create(
                    model="gpt-4-0613",
                    messages=[
                        {"role": "system", "content": "您是一位數學問題解決助理。您可以建立並執行 Python 程式碼來協助解決數學問題。"},
                        {"role": "user", "content": prompt},
                        message,
                        {
                            "role": "function",
                            "name": function_name,
                            "content": result,
                        },
                    ],
                )
                
                final_response = second_response.choices[0].message.content
            else:
                final_response = "Unsupported function call"
        else:
            final_response = message.content

        # Log the interaction
        log_interaction(request.remote_addr, prompt, final_response)

        return jsonify({"response": final_response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def execute_python_code(code):
    filename = f"temp_{uuid.uuid4().hex}.py"
    with open(filename, "w") as f:
        f.write(code)
    
    try:
        result = subprocess.run(["python3", filename], capture_output=True, text=True, timeout=5)
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        output = "Execution timed out"
    finally:
        os.remove(filename)
    
    return output

def log_interaction(ip, prompt, response):
    with open("log", "a") as f:
        f.write(f"{ip},{prompt},{response}\n")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=80)