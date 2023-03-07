from flask import Flask, request, jsonify

from datetime import date

app = Flask(__name__)

tickets = [
    {"id":1, "ticketId": 1, "eventId": 1, "price": 50, "type": "normal", "booked": True},
    {"id":2, "ticketId": 2, "eventId": 1, "price": 100, "type": "VIP", "booked": True},
    {"id":3, "ticketId": 1, "eventId": 2, "price": 10, "type": "normal", "booked": False},
    {"id":4, "ticketId": 2, "eventId": 2, "price": 20, "type": "VIP", "booked": False},
    {"id":5, "ticketId": 1, "eventId": 3, "price": 10, "type": "normal", "booked": False},
    {"id":6, "ticketId": 2, "eventId": 3, "price": 20, "type": "VIP", "booked": False},
]

booked_tickets = [
    {"bookingId": 1, "id": 1, "userId": 1, "bookingDate": "2022, 3, 7"},
    {"bookingId": 2, "id": 2, "userId": 1, "bookingDate": "2022, 3, 7"},
]

@app.route("/ticket", methods=["POST"])
def book_ticket():
    ticket_data = request.get_json()
    for ticket in tickets:
        if ticket["id"] == ticket_data["id"]:
            if any(t["id"] == ticket_data["id"] and t["userId"] == ticket_data["userId"] for t in booked_tickets):
                # Ticket is already booked by the specified user
                return jsonify({"message": "Ticket is already booked by specified user"}), 400
            else:
                ticket["booked"] = True
                booking_id = len(booked_tickets) + 1  # generate a new booking id
                booking_date = date.today()  
                booked_tickets.append({"bookingId": booking_id, "id": ticket["id"], "userId": ticket_data["userId"], "bookingDate": booking_date})
                return jsonify({"message": "Ticket booked"})
    return jsonify({"message": "Ticket not available"}), 400

@app.route("/ticket/<id>", methods=["PUT"])
def unbook_ticket(id):
    for ticket in booked_tickets:
        if ticket["id"] == int(id):
            for t in tickets:
                if t["id"] == int(id):
                    t["booked"] = False
                    break
            booked_tickets.remove(ticket)
            return jsonify({"message": "Ticket unbooked"})
    return jsonify({"message": "Ticket not found"}), 404

@app.route("/ticket/<id>", methods=["GET"])
def get_ticket(id):
    user_id = 1
    for ticket in booked_tickets:
        if ticket["id"] == int(id):
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
