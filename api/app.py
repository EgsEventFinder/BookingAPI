from flask import Flask, jsonify, request
from flask_mysqldb import MySQL
import yaml
import datetime

app = Flask(__name__)

db = yaml.load(open('db.yaml'), Loader=yaml.Loader)
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(app)
 
@app.route("/ticket", methods=["POST"])
def book_ticket():
    ticket_data = request.get_json()
    id = ticket_data["id"]
    user_id = ticket_data["userId"]
    
    with mysql.connection.cursor() as cur:
        try:
            cur.execute("SELECT * FROM tickets WHERE id=%s AND booked=False", (id,))
            ticket = cur.fetchone()

            if ticket is None:
                return jsonify({"message": "Ticket not available or already booked"}), 400
            
            booking_date = datetime.date.today()
            cur.execute("INSERT INTO booked_tickets (id, bookingDate, userId) VALUES (%s, %s, %s)", (id, booking_date, user_id))

            cur.execute("UPDATE tickets SET booked=True WHERE id=%s", (id,))
            mysql.connection.commit()

            return jsonify({"message": "Ticket booked"})

        except:
            mysql.connection.rollback()
            return jsonify({"message": "Error booking ticket"}), 500

        finally:
            cur.close()

@app.route("/ticket/<id>", methods=["PUT"])
def unbook_ticket(id):
    with mysql.connection.cursor() as cur:
        try:
            cur.execute("SELECT * FROM booked_tickets WHERE id=%s", (id,))
            booking = cur.fetchone()

            if booking is None:
                return jsonify({"message": "Ticket not found"}), 404

            cur.execute("DELETE FROM booked_tickets WHERE id=%s", (id,))

            cur.execute("UPDATE tickets SET booked=False WHERE id=%s", (id,))
            mysql.connection.commit()

            return jsonify({"message": "Ticket unbooked"})

        except:
            mysql.connection.rollback()
            return jsonify({"message": "Error unbooking ticket"}), 500

        finally:
            cur.close()

@app.route("/ticket/<id>", methods=["GET"])
def get_ticket(id):
    user_id = 1
    
    with mysql.connection.cursor() as cur:
        try:
            query = """
                SELECT b.bookingDate, t.price, t.eventId, t.type FROM booked_tickets as b 
                    INNER JOIN tickets as t ON b.id = t.id WHERE b.id = %s AND b.userId = %s
            """
            cur.execute(query,(id,user_id,))
            booking = cur.fetchone()

            if booking is None:
                return jsonify({"message": "Ticket not found"}), 404

            return jsonify(booking)

        except:
            return jsonify({"message": "Error getting ticket"}), 500
        
        finally:
            cur.close()

@app.route("/tickets", methods=["GET"])
def get_tickets():
    user_id = 1
    
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    offset = (page - 1) * limit
    
    with mysql.connection.cursor() as cur:
        try:
            query = """
                SELECT b.bookingDate, t.price, t.eventId, t.type FROM booked_tickets as b 
                INNER JOIN tickets as t ON b.id = t.id WHERE b.userId = %s LIMIT %s, %s"
            """
            cur.execute(query,(user,offset,limit,))
            user_tickets = cur.fetchall()

            return jsonify(user_tickets)

        except:
            return jsonify({"message": "Error getting user tickets"}), 500

        finally:
            cur.close()

@app.route("/event/<event_id>/tickets", methods=["GET"])
def get_event_tickets(event_id):
    with mysql.connection.cursor() as cur:
        try:
            cur.execute("SELECT * FROM tickets WHERE eventId=%s and booked=False", (event_id,))
            event_tickets = cur.fetchall()

            return jsonify(event_tickets)

        except:
            return jsonify({"message": "Error getting event tickets"}), 500

        finally:
            cur.close()


@app.route("/tickets/<event_id>", methods=["GET"])
def get_number_event_tickets(event_id):
    with mysql.connection.cursor() as cur:
        try:
            query = """
                SELECT COUNT(*) AS num_booked_tickets FROM tickets 
                    INNER JOIN booked_tickets ON tickets.id = booked_tickets.id 
                        WHERE tickets.eventId = %s AND tickets.booked = True
            """
            cur.execute(query,(event_id))
            result = cur.fetchone()
            count = result[0]

            return jsonify({"count": count})

        except:
            return jsonify({"message": "Error getting event tickets"}), 500

        finally:
            cur.close()

if __name__ == '__main__':
    app.run(debug=True)

