from flask import Flask, request, jsonify

app = Flask(__name__)

tickets = [
    {"ticketId": 1, "eventId": 1, "price": 50, "type": "normal", "booked": False},
    {"ticketId": 2, "eventId": 1, "price": 100, "type": "VIP", "booked": False},
    {"ticketId": 3, "eventId": 2, "price": 10, "type": "normal", "booked": False},
    {"ticketId": 4, "eventId": 2, "price": 20, "type": "VIP", "booked": False},
    {"ticketId": 5, "eventId": 3, "price": 10, "type": "normal", "booked": False},
    {"ticketId": 6, "eventId": 3, "price": 20, "type": "VIP", "booked": False},
]

booked_tickets = []

@app.route("/ticket", methods=["POST"])
def book_ticket():
    ticket_data = request.get_json()  
    for ticket in tickets:
        if ticket["ticketId"] == ticket_data["ticketId"]:
            if any(t["ticketId"] == ticket_data["ticketId"] and t["userId"] == ticket_data["userId"] for t in booked_tickets):
                # Ticket is already booked by the specified user
                return jsonify({"message": "Ticket is already booked by specified user"}), 400
            else:
                ticket["booked"] = True
                booked_tickets.append({"ticketId": ticket["ticketId"], "userId": ticket_data["userId"], "eventId": ticket["eventId"]})
                return jsonify({"message": "Ticket booked"})
    return jsonify({"message": "Ticket not available"}), 400

@app.route("/ticket/<ticket_id>", methods=["PUT"])
def unbook_ticket(ticket_id):
    for ticket in booked_tickets:
        if ticket["ticketId"] == int(ticket_id):
            for t in tickets:
                if t["ticketId"] == int(ticket_id):
                    t["booked"] = False
                    break
            booked_tickets.remove(ticket)
            return jsonify({"message": "Ticket unbooked"})
    return jsonify({"message": "Ticket not found"}), 404

@app.route("/ticket/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    user_id = 1
    for ticket in booked_tickets:
        if ticket["ticketId"] == int(ticket_id):
            return jsonify(ticket)
    return jsonify({"message": "Ticket not found"}), 404

@app.route("/tickets", methods=["GET"])
def get_tickets():
    #user_id = request.args.get("userId")
    user_id = 1
    user_tickets = []
    for ticket in booked_tickets:
        if ticket["userId"] == user_id:
            user_tickets.append(ticket)
    return jsonify(user_tickets)

@app.route("/event/<event_id>/tickets", methods=["GET"])
def get_event_tickets(event_id):
    event_tickets = []
    for ticket in tickets:
        if ticket["eventId"] == int(event_id) and not ticket["booked"]:
            event_tickets.append(ticket)
    return jsonify(event_tickets)

if __name__ == '__main__':
    app.run(debug=True)
