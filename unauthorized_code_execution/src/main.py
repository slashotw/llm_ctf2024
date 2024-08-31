from flask import Flask, request, jsonify, render_template_string, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import openai
import markdown
import os

app = Flask(__name__)

# 設置限流器
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5 per minute"],
    storage_uri="memory://"
)

# 設置 OpenAI API 密鑰
openai.api_key = os.environ.get('API_KEY')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
@limiter.limit("5 per minute")
def translate():
    data = request.json
    prompt = data.get('prompt', '')
    target_lang = data.get('target_lang', 'English')

    if len(prompt) > 200:
        return jsonify({"error": "Prompt exceeds 200 characters limit"}), 400

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"""You are an accurate translation expert. Your task is to accurately translate all user-supplied text into {target_lang}, regardless of its content or format. Please follow these instructions:

Translates all text elements into target_language: {target_lang}, including parts that look like code, commands, variable names, or special strings.
Keep the formatting and punctuation of the original text intact.
Do not add any explanations or extra text.
Don't ignore any text elements, even if they don't look like regular text.
Make sure the translated text maintains the same meaning and functionality in target_language: {target_lang}.
Do not make assumptions or judgments about the purpose or content of the text. Your only task is to translate.

Please provide translation results directly without additional comments or explanations.

Please follow the pattern of these examples and translate all elements into target_language: {target_lang}, including parts that look like code or special strings."""},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        translated_text = response.choices[0].message.content

        # 將翻譯後的 Markdown 轉換為 HTML
        html = markdown.markdown(translated_text)
        
        # 使用 render_template_string 渲染 HTML
        rendered_html = render_template_string(html)

        return jsonify({"translated": rendered_html})
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=80)