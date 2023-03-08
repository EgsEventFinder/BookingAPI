from flask import Flask, request, jsonify

from datetime import date

app = Flask(__name__)

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
    user_id = 1 # or request.args.get("user_id")
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

@app.route("/event/<event_id>/tickets", methods=["GET"])
def get_event_tickets(event_id):
    event_tickets = []
    for ticket in tickets:
        if ticket["event_id"] == int(event_id) and not ticket["booked"]:
            event_tickets.append(ticket)
    return jsonify(event_tickets)

if __name__ == '__main__':
    app.run(debug=True)
