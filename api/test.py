from flask import Flask, request, jsonify, url_for
from flask_mail import Mail, Message
import jwt
import secrets
from datetime import datetime, timedelta, date
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp-mail.outlook.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'eventFinderUA@outlook.com'
app.config['MAIL_PASSWORD'] = 'UaDETIegs'

tickets = [
    {"ticket_id":1, "ticket_number": 1, "event_id": 1, "price": 50, "type": "normal", "booked": True},
    {"ticket_id":2, "ticket_number": 2, "event_id": 1, "price": 100, "type": "VIP", "booked": True},
    {"ticket_id":3, "ticket_number": 1, "event_id": 2, "price": 10, "type": "normal", "booked": False},
    {"ticket_id":4, "ticket_number": 2, "event_id": 2, "price": 20, "type": "VIP", "booked": False},
    {"ticket_id":5, "ticket_number": 1, "event_id": 3, "price": 10, "type": "normal", "booked": False},
    {"ticket_id":6, "ticket_number": 2, "event_id": 3, "price": 20, "type": "VIP", "booked": False},
]

booked_tickets = [
    {"booking_id": 1, "ticket_id": 1, "user_id": 1, "booking_date": "2022, 3, 7"},
    {"booking_id": 2, "ticket_id": 2, "user_id": 1, "booking_date": "2022, 3, 7"},
]

key = secrets.token_hex(32)
key_expiration = datetime.now() + timedelta(minutes=30)

mail = Mail(app)

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('interval', minutes=15)
def is_key_expired():
    global key, key_expiration
    if datetime.now() >= key_expiration:
        # if the key is expired, generate a new key and update the expiration time
        key = secrets.token_hex(32)
        key_expiration = datetime.now() + timedelta(minutes=30)
        print('Key expired. New key generated.')

# start the scheduler
scheduler.start()

is_key_expired()

@app.route("/ticket", methods=["POST"])
def book_ticket():
    ticket_data = request.get_json()
    for ticket in tickets:
        if ticket["ticket_id"] == ticket_data["ticket_id"]:
            if any(t["ticket_id"] == ticket_data["ticket_id"] and t["user_id"] == ticket_data["user_id"] for t in booked_tickets):
                # Ticket is already booked by the specified user
                return jsonify({"message": "Ticket is already booked by specified user"}), 400
            else:
                ticket["booked"] = True
                booking_id = len(booked_tickets) + 1  
                booking_date = date.today()  
                booked_tickets.append({"booking_id": booking_id, "ticket_id": ticket["ticket_id"], "user_id": ticket_data["user_id"], "booking_date": booking_date})
                print(booked_tickets)
                return jsonify({"message": "Ticket booked"})
    return jsonify({"message": "Ticket not available"}), 400

@app.route("/ticket/<ticket_id>", methods=["PUT"])
def unbook_ticket(ticket_id):
    for ticket in booked_tickets:
        if ticket["ticket_id"] == int(ticket_id):
            for t in tickets:
                if t["ticket_id"] == int(ticket_id):
                    t["booked"] = False
                    break
            booked_tickets.remove(ticket)
            return jsonify({"message": "Ticket unbooked"})
    return jsonify({"message": "Ticket not found"}), 404

@app.route("/ticket/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    user_id = 1 # or request.args.get("user_id")
    for booking in booked_tickets:
        if booking["ticket_id"] == int(ticket_id) and booking["user_id"] == user_id:
            
            ticket = next((t for t in tickets if t["ticket_id"] == int(ticket_id)), None)
            if ticket:
               
                user_ticket = {
                    "event_id": ticket["event_id"],
                    "price": ticket["price"],
                    "type": ticket["type"],
                    "booking_date": booking["booking_date"]
                }
            
                return jsonify(user_ticket)
    return jsonify({"message": "Ticket not found"}), 404

@app.route("/tickets", methods=["GET"])
def get_tickets():
    user_id = 2 # or request.args.get("user_id")
    user_tickets = []
    for booking in booked_tickets:
        if booking["user_id"] == user_id:
            
            ticket = next((t for t in tickets if t["ticket_id"] == booking["ticket_id"]), None)
            if ticket:
                
                user_ticket = {
                    "event_id": ticket["event_id"],
                    "price": ticket["price"],
                    "type": ticket["type"],
                    "booking_date": booking["booking_date"]
                }
                
                user_tickets.append(user_ticket)
    return jsonify(user_tickets)


@app.route('/ticket/<ticket_id>/trade', methods=['GET'])
def sell_ticket(ticket_id):
    seller_id = 1 # Replace with actual seller ID
    seller_email = "miguel.angelo.tavares@hotmail.com"
    buyer_id = 2 # Replace with actual buyer ID
    buyer_email = "buyer@example.com"
    ticket = next((t for t in tickets if t['ticket_id'] == int(ticket_id)), None)
    if not ticket:
        return jsonify({'message': 'Ticket not found'}), 404

    if (key_expiration - datetime.now()) < timedelta(minutes=5):
        token_expiration = key_expiration
    else:
        token_expiration = datetime.now() + timedelta(minutes=5)

    payload = {
        'seller_id': seller_id,
        #'seller_email': seller_email,
        'buyer_id': buyer_id,
        #'buyer_email': buyer_email,
    }

    secret_token = jwt.encode(payload, key , algorithm='HS256')

    sell_url = url_for('complete_trade', ticket_id=ticket_id, token=secret_token, _external=True)

    message = Message(subject='Ticket sold',
                      sender='eventFinderUA@outlook.com',
                      recipients=[seller_email],
                      body=f'Your {ticket["type"]} ticket (#{ticket["ticket_number"]}) for event #{ticket["event_id"]} has been sold to {buyer_email} for ${ticket["price"]} $. Click here to complete the sale: {sell_url}')
    mail.send(message)

    return jsonify({'success': True})


# use the key in your complete_sale function
@app.route('/ticket/<ticket_id>/complete_trade/<token>', methods=['GET'])
def complete_trade(ticket_id, token):
    try:
        if key is None:
             return jsonify({'message': 'Key not found'})

        decoded_token = jwt.decode(secret_token, key, algorithms=['HS256'])
      
        sellerId = decoded_token['seller_id']
        buyerId = decoded_token['buyer_id']
        for booked_ticket in booked_tickets:
            if booked_ticket['ticket_id'] == int(ticket_id) and booked_ticket['user_id'] == seller_id:
                booked_ticket['user_id'] = buyer_id
                break

        return jsonify({'message': 'Ticket sale completed'})
    except:
        return jsonify({'message': 'Invalid or expired token'}), 401

if __name__ == '__main__':
    app.run(debug=True)
