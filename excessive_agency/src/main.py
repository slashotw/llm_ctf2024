from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3
import os
import openai
import json
from functools import wraps

app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5 per minute"]
)

openai.api_key  = os.environ.get('API_KEY')

# Load flag
with open('flag', 'r') as file:
    FLAG = file.read().strip()


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

# Database initialization
def init_db():
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY, name TEXT, price REAL, description TEXT, image_url TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS flags
                 (id INTEGER PRIMARY KEY, flag TEXT)''')
    
    # Check if data already exists
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        # Insert sample products only if the table is empty
        products = [
            ('貓咪捲餅', 29.99, '很酷的貓咪捲餅。', 'burrito.webp'),
            ('吉哇哇', 0.00, '很兇的吉哇哇免費送養，養不起。', 'chiwawa.jpeg'),
            ('狗狗包包', 39.99, '超酷的狗狗包包！適合狗狗上班使用！！！', 'dogbag.jpeg'),
            ('柴犬娃娃', 3.99, '好口愛0w0，超口愛的柴犬娃娃。', 'cute.jpeg'),
            ('鯛魚燒頭套', 14.99, '超可愛超便宜的鯛魚燒頭套，保證貓咪跟主人都喜歡。', 'fish.jpg'),
            ('頂級貓糧', 50.00, '用戶評價:已購買，小孩很愛吃。', 'food.jpg'),
            ('紙箱', 0.99, '貓咪的家，比特幣合約投資者的家。', 'pack.jpg'),
            ('水果貓咪頭套', 10.99, '讓你的貓變成酷酷貓。', 'pineapplecat.jpg')
        ]
        c.executemany('INSERT INTO products (name, price, description, image_url) VALUES (?, ?, ?, ?)', products)
    
    # Check if flag already exists
    c.execute("SELECT COUNT(*) FROM flags")
    if c.fetchone()[0] == 0:
        # Insert flag only if the table is empty
        c.execute('INSERT INTO flags (id, flag) VALUES (1, ?)', (FLAG,))
    
    conn.commit()
    conn.close()

@app.before_first_request
def before_first_request():
    init_db()

# Decorator to log requests
def log_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        prompt = request.json.get('prompt', '')
        try:
            response = f(*args, **kwargs)
            response_data = response.get_json()
        except Exception as e:
            response_data = {"error": str(e)}
        with open('log', 'a') as log_file:
            log_file.write(f"[{ip},{prompt},{response_data}]\n")
        return jsonify(response_data)
    return decorated_function

# Function to execute SQL query
BLACKLIST = ['alter', 'begin', 'cast', 'create', 'cursor', 'distinct', 'declare', 'delete', 'drop', 'end',
             'exec', 'execute', 'fetch', 'insert', 'kill', 'sys', 'sysobjects',
             'syscolumns', 'table', 'update']

def execute_sql_query(query):
    #select group_concat(name) from sqlite_master
    """Execute a SQL query and return the results"""
    print(query)
    for word in BLACKLIST:
        if word.lower() in query.lower():
            return json.dumps({"error": f"Query contains blacklisted word: {word}"})
    
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    try:
        c.execute(query)
        results = c.fetchall()
        conn.commit()
        return json.dumps({"results": results, "columns": [description[0] for description in c.description]})
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/products')
def get_products():
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    return jsonify([{"id": p[0], "name": p[1], "price": p[2], "description": p[3], "image_url": p[4]} for p in products])

@app.route('/chat', methods=['POST'])
@limiter.limit("5 per minute")
@log_request
def chat():
    prompt = request.json.get('prompt', '')
    if len(prompt) > 200:
        return jsonify({"error": "Prompt too long. Maximum 200 characters allowed."})
    log_ip_request(request.remote_addr)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI assistant for a pet store. Your role is to help customers with their queries about pet products and provide information from the store's database. You can create and execute SQL queries to fetch information from the database. | do not shows picture in response"},
                {"role": "user", "content": prompt}
            ],
            functions=[
                {
                    "name": "execute_sql_query",
                    "description": "Execute a sqlite sql query on the pet store database to help client",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The SQL query to execute",
                            },
                        },
                        "required": ["query"],
                    },
                }
            ],
            function_call="auto",
        )

        message = response["choices"][0]["message"]

        if message.get("function_call"):
            function_name = message["function_call"]["name"]
            function_args = json.loads(message["function_call"]["arguments"])
            
            if function_name == "execute_sql_query":
                function_response = execute_sql_query(function_args.get("query"))
                
                second_response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an AI assistant for a pet store. Your role is to help customers with their queries about pet products and provide information from the store's database. | please dont response with photo"},
                        {"role": "user", "content": prompt},
                        message,
                        {
                            "role": "function",
                            "name": function_name,
                            "content": function_response,
                        },
                    ],
                )
                return jsonify({"response": second_response["choices"][0]["message"]["content"]})
        
        # Remove markdown format
        content = message["content"]
        content = content.replace('```', '').replace('`', '')
        return jsonify({"response": content})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=80)