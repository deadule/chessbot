from flask import Flask, request, jsonify
from auth_handler import confirm_payment

app = Flask(__name__)

@app.route('/yookassa-webhook', methods=['POST'])
def yookassa_webhook():
    data = request.json
    if data.get('event') == 'payment.succeeded':
        payment_info = data.get('object')
        user_id = payment_info['metadata']['user_id']
        confirm_payment(user_id)
        print(f"User {user_id} has been authorized based on successful payment.")
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "ignored"}), 200

@app.route('/', methods=['GET'])
def main():
    return "it works"

if __name__ == '__main__':
    app.run(port=5000)
