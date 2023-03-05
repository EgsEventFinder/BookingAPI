from flask import Flask, request, jsonify

app = Flask(__name__)

tickets = [
    {"ticketId": 1, "userId": None, "eventId": 1, "price": 50, "type":"VIP"},
    {"ticketId": 2, "userId": None, "eventId": 2, "price": 100, "type":"VIP"},
    {"ticketId": 3, "userId": 1, "eventId": 3, "price": 10, "type":"Normal"},
    {"ticketId": 4, "userId": 1, "eventId": 4, "price": 20, "type":"Normal"},
    
]

@app.route("/ticket", methods=["POST"])
def book_ticket():
    ticket_data = request.get_json()
    
    for ticket in tickets:
        print(ticket)
        print(ticket_data)
        print(ticket["ticketId"] == ticket_data["ticketId"] and ticket["userId"] is None)
        if ticket["ticketId"] == ticket_data["ticketId"] and ticket["userId"] is None:
            ticket["userId"] = ticket_data["userId"]
            return jsonify({"message": "Ticket booked"})
    return jsonify({"message": "Ticket not available"}), 400

@app.route("/ticket/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    user_id = 1
    for ticket in tickets:
        if ticket["ticketId"] == int(ticket_id) and ticket["userId"] == user_id:
            return jsonify(ticket)
    return jsonify({"message": "Ticket not found"}), 404

@app.route("/tickets", methods=["GET"])
def get_tickets():
    #user_id = request.args.get("userId")
    user_id = 1
    user_tickets = []
    for ticket in tickets:
        if ticket["userId"] == user_id:
            user_tickets.append(ticket)
    return jsonify(user_tickets)

@app.route("/ticket/<ticket_id>", methods=["PUT"])
def unbook_ticket(ticket_id):
    print(ticket_id)
    for ticket in tickets:
        if ticket["ticketId"] == int(ticket_id) and ticket["userId"] is not None:
            ticket["userId"] = None
            return jsonify({"message": "Ticket unbooked"})
    return jsonify({"message": "Ticket not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
