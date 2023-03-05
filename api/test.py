from flask import Flask, jsonify, request
from flask_mail import Mail, Message
import secrets
from flask_pymongo import PyMongo

app = Flask(__name__)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_password'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/ticket_db'

mongo = PyMongo(app)

@app.route("/ticket", methods=["POST"])
def book_ticket():
    ticket_data = request.get_json()
    ticket_id = mongo.db.tickets.insert_one(ticket_data).inserted_id
    return jsonify(str(ticket_id))

@app.route("/ticket/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    ticket = mongo.db.tickets.find_one({"ticketId": ticket_id})
    if ticket:
        return jsonify(ticket)
    else:
        return jsonify({"message": "Ticket not found"}), 404

@app.route("/tickets", methods=["GET"])
def get_tickets():
    user_id = request.args.get("userId")
    tickets = mongo.db.tickets.find({"userId": user_id})
    return jsonify([ticket for ticket in tickets])

@app.route("/ticket/<ticket_id>", methods=["PUT"])
def unbook_ticket(ticket_id):
    result = mongo.db.tickets.update_one({"ticketId": ticket_id}, {"$set": {"userId": None}})
    if result.modified_count == 1:
        return jsonify({"message": "Ticket unbooked"})
    else:
        return jsonify({"message": "Ticket not found"}), 404

@app.route('/ticket/<ticket_id>/sell', methods=['POST'])
def sell_ticket(ticket_id):
    
    seller_email = request.form.get('seller_email')

    secret_token = secrets.token_urlsafe(32)

    mongo.db.secret_tokens.insert_one({'ticketId': ticket_id, 'token': secret_token})

    sell_url = url_for('complete_sale', ticket_id=ticket_id, secret_token=secret_token, _external=True)

    message = Message(subject='Ticket sold',
                      recipients=[seller_email],
                      body='Your ticket has been sold. Click here to complete the sale: {}'.format(sell_url))
    mail.send(message)

    return jsonify({'success': True})

@app.route('/ticket/<ticket_id>/complete_sale/<secret_token>', methods=['GET'])
def complete_sale(ticket_id, secret_token):
    
    token_doc = mongo.db.secret_tokens.find_one({'ticketId': ticket_id, 'token': secret_token})
    if not token_doc:
        return 'Invalid or expired token'

    mongo.db.secret_tokens.delete_one({'ticketId': ticket_id, 'token': secret_token})

    result = mongo.db.tickets.update_one({'ticketId': ticket_id}, {'$set': {'userId': token_doc['buyerId']}})

    if result.modified_count == 1:
        return 'Ticket sale completed'
    else:
        return 'Failed to update ticket'

if __name__ == '__main__':
    app.run(debug=True)


