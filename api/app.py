from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
import yaml

app = Flask(__name__)

db = yaml.load(open('db.yaml'))
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']
 
mysql = MySQL(app)

@app.route("/")
def home():
    '''
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO booked_tickets (ticketId, userId, eventId) VALUES (%s, %s, %s)", (1, 1, 1))
    mysql.connection.commit()
    '''
    return jsonify({"message": "Success"})

@app.route("/ticket", methods=["POST"])
def book_ticket():
    cur = mysql.connection.cursor()

    ticket_data = request.get_json()
    ticket_id = ticket_data["ticketId"]
    user_id = ticket_data["userId"]

    if not isinstance(ticket_id, int) or not isinstance(user_id, int):
        return jsonify({"message": "Invalid input: ticketId and userId must be integers"}), 400

    cur.execute("SELECT * FROM tickets WHERE ticketId=%s", (ticket_id,))
    ticket = cur.fetchone()

    if ticket is None:
        return jsonify({"message": "Ticket not available"}), 400

    cur.execute("SELECT * FROM booked_tickets WHERE ticketId=%s AND userId=%s", (ticket_id, user_id))
    existing_booking = cur.fetchone()

    if existing_booking is not None:
        return jsonify({"message": "Ticket is already booked by specified user"}), 400

    cur.execute("INSERT INTO booked_tickets (ticketId, userId, eventId) VALUES (%s, %s, %s)", (ticket_id, user_id, ticket["eventId"]))
    mysql.connection.commit()

    return jsonify({"message": "Ticket booked"})

@app.route("/ticket/<ticket_id>", methods=["PUT"])
def unbook_ticket(ticket_id):
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM booked_tickets WHERE ticketId=%s", (ticket_id,))
    booking = cur.fetchone()

    if booking is None:
        return jsonify({"message": "Ticket not found"}), 404

    cur.execute("DELETE FROM booked_tickets WHERE ticketId=%s", (ticket_id,))
    mysql.connection.commit()

    return jsonify({"message": "Ticket unbooked"})

@app.route("/ticket/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM booked_tickets WHERE ticketId=%s", (ticket_id,))
    booking = cur.fetchone()

    if booking is None:
        return jsonify({"message": "Ticket not found"}), 404

    return jsonify(booking)

@app.route("/tickets", methods=["GET"])
def get_tickets():

    user_id = 1
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    offset = (page - 1) * limit
    
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM booked_tickets WHERE userId=%s LIMIT %s, %s", (user_id, offset, limit))
    user_tickets = cur.fetchall()

    return jsonify(user_tickets)

@app.route("/event/<event_id>/tickets", methods=["GET"])
def get_event_tickets(event_id):
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM ticket WHERE eventId=%s", (event_id))
    event_tickets = cur.fetchall()
    return jsonify(event_tickets)

'''
@app.route("/tickets/<event_id>", methods=["GET"])
def get_event_tickets(event_id):
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM booked_tickets WHERE eventId=%s", (event_id,))
    result = cur.fetchone()
    count = result[0]

    return jsonify({"count": count})
'''
if __name__ == '__main__':
    app.run(debug=True)

