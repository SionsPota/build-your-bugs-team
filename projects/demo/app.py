import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from model import Evaluator, Polisher

load_dotenv()

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/grade_and_polish", methods=["POST"])
def grade_and_polish():
    """
    请求体示例:
    {
        "answer": "...学生作文...",
        "question_file": "test.yaml"   # 可选，默认 test.yaml
    }
    """
    data = request.get_json(silent=True) or {}
    answer = data.get("answer")
    question_file = data.get("question_file", "test.yaml")

    if not answer:
        return jsonify({"error": "field 'answer' is required"}), 400

    try:
        evaluator = Evaluator(question_file=question_file)
        comment = evaluator.generate_response(answer)

        polisher = Polisher(answer, comment)
        polished_answer = polisher.generate_response()

        return jsonify({
            "comment": comment,
            "polished_answer": polished_answer
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
