from flask import Flask, jsonify, request
from flask_mysqldb import MySQL
import yaml
import datetime
import random

app = Flask(__name__)

db = yaml.load(open('db.yaml'), Loader=yaml.Loader)
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(app)
 
def create_databases():
    
    with mysql.connection.cursor() as cur:
        try:
            query = """CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id INT AUTO_INCREMENT PRIMARY KEY,
                    ticket_number INT,
                    event_id INT,
                    price INT,
                    type VARCHAR(50) CHECK (type IN ('VIP', 'normal')),
                    booked BOOL,
                    UNIQUE (ticket_number, event_id)
                );
                """
            cur.execute(query)
        
            query = """CREATE TABLE IF NOT EXISTS booked_tickets (
                    booking_id INT AUTO_INCREMENT PRIMARY KEY,
                    ticket_id INT,
                    user_id INT,
                    booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
                    UNIQUE (ticket_id)
                );
                """
            cur.execute(query)
            mysql.connection.commit()
    
        except:
            mysql.connection.rollback()
            return jsonify({"message": "Error creating tables"}), 500

        finally:
            cur.close()

@app.route("/", methods=["GET"])
def create_tickets():
    
    create_databases()
    num_events = 3
    num_tickets = 20

    with mysql.connection.cursor() as cur:
        try:
            for event_id in range(1, 4):
                
                query = "SELECT MAX(ticket_number) FROM tickets WHERE event_id = %s"
                
                cur.execute(query, (event_id,))
                result = cur.fetchone()
                
                max_ticket_number = result[0] if result[0] else 0
                
                for i in range(1, 11):
                    ticket_number = max_ticket_number + i
                    #price = random.randint(10, 40)
                    price = 10 
                    query = "INSERT INTO tickets (ticket_number, event_id, price, type, booked) VALUES (%s, %s, %s, %s, %s)"
                    cur.execute(query, (ticket_number, event_id, price, 'normal', 0))
                
                for i in range(1, 11):
                    ticket_number = max_ticket_number + i + 10
                    #price = random.randint(60, 100)
                    price = 50 
                    query = "INSERT INTO tickets (ticket_number, event_id, price, type, booked) VALUES (%s, %s, %s, %s, %s)"
                    cur.execute(query, (ticket_number, event_id, price, 'VIP', 0))

            mysql.connection.commit()
            return jsonify({"message": "Tickets created"})

        except:
            mysql.connection.rollback()
            return jsonify({"message": "Error creating tickets"}), 500

        finally:
            cur.close()


@app.route("/ticket", methods=["POST"])
def book_ticket():

    booking_data = request.get_json()
    user_id = booking_data["user_id"]
    event_id = booking_data["event_id"]
    ticket_type = booking_data["ticket_type"]

    with mysql.connection.cursor() as cur:
        try:
            
            cur.execute("SELECT ticket_id FROM tickets WHERE event_id = %s AND booked = %s AND type = %s ORDER BY ticket_number LIMIT 1", (event_id, 0, ticket_type))
            ticket = cur.fetchone()
            ticket_id = ticket[0]

            if ticket is None:
                return None
            
            cur.execute("UPDATE tickets SET booked = %s WHERE ticket_id = %s", (1,ticket_id,))
            booking_date = datetime.datetime.now()
            cur.execute("INSERT INTO booked_tickets (ticket_id, user_id, booking_date) VALUES (%s, %s, %s)", (ticket_id, user_id, booking_date))

            mysql.connection.commit()

            return jsonify({"message": "Ticket booked"})

        except:
            mysql.connection.rollback()
            return jsonify({"message": "Error booking ticket"}), 500

        finally:
            cur.close()

@app.route("/ticket/<ticket_id>", methods=["PUT"])
def unbook_ticket(ticket_id):
    with mysql.connection.cursor() as cur:
        try:
            cur.execute("SELECT * FROM booked_tickets WHERE ticket_id=%s", (ticket_id,))
            booking = cur.fetchone()
          
            if booking is None:
                return jsonify({"message": "Ticket not found"}), 404

            cur.execute("DELETE FROM booked_tickets WHERE ticket_id=%s", (ticket_id,))
    
            cur.execute("UPDATE tickets SET booked=%s WHERE ticket_id=%s", (0,ticket_id,))
            mysql.connection.commit()

            return jsonify({"message": "Ticket unbooked"})

        except:
            mysql.connection.rollback()
            return jsonify({"message": "Error unbooking ticket"}), 500

        finally:
            cur.close()

@app.route("/ticket/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    user_id = 1

    with mysql.connection.cursor() as cur:
        try:
            query = """
                SELECT t.event_id, t.price, t.type, b.booking_date FROM booked_tickets as b 
                    INNER JOIN tickets as t ON b.ticket_id = t.ticket_id WHERE b.ticket_id = %s AND b.user_id = %s
            """
            cur.execute(query,(ticket_id,user_id,))
            ticket = cur.fetchone()
            
            if ticket is None:
                return jsonify({"message": "Ticket not found"}), 404

            event_id, price, ticket_type, booking_date = ticket
            user_ticket = {
                "event_id": event_id,
                "price": price,
                "type": ticket_type,
                "booking_date": booking_date.strftime("%Y-%m-%d %H:%M")
            }

            return jsonify(user_ticket)

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
                SELECT t.event_id, t.price, t.type, b.booking_date 
                FROM booked_tickets AS b 
                INNER JOIN tickets AS t ON t.ticket_id = b.ticket_id 
                WHERE b.user_id = %s 
                ORDER BY b.booking_date DESC 
                LIMIT %s,%s
            """
            cur.execute(query, (user_id, offset, limit))
            user_tickets = cur.fetchall()

            user_tickets_list = []
            for ticket in user_tickets:
                event_id, price, ticket_type, booking_date = ticket
                user_ticket = {
                    "event_id": event_id,
                    "price": price,
                    "type": ticket_type,
                    "booking_date": booking_date.strftime("%Y-%m-%d %H:%M")
                }
                user_tickets_list.append(user_ticket)

            return jsonify(user_tickets_list)

        except:
            return jsonify({"message": "Error getting user tickets"}), 500

        finally:
            cur.close()

@app.route("/event/<event_id>/tickets", methods=["GET"])
def get_event_tickets(event_id):

    
    with mysql.connection.cursor() as cur:
        try:
            cur.execute(
                "SELECT type, price FROM tickets WHERE event_id=%s AND booked=%s GROUP BY type, price",
                (event_id, 0)
            )
            event_tickets = cur.fetchall()

            ticket_info = []
            for ticket_type, ticket_price in event_tickets:
                if any(ticket["type"] == ticket_type for ticket in ticket_info):
                    [ticket["prices"].append(ticket_price) for ticket in ticket_info if ticket["type"] == ticket_type]
                else:
                    ticket_info.append({
                        "type": ticket_type,
                        "event_id": event_id,
                        "prices": [ticket_price]
                    })

            ticket_info = [{    
                "type": ticket["type"],
                "event_id": ticket["event_id"],
                "prices": ticket["prices"][0] if len(ticket["prices"]) == 1 else ticket["prices"]
            } for ticket in ticket_info]

            return jsonify(ticket_info)

        except:
            return jsonify({"message": "Error getting event tickets"}), 500

        finally:
            cur.close()


@app.route("/tickets/<event_id>", methods=["GET"])
def get_number_event_tickets(event_id):
    with mysql.connection.cursor() as cur:
        try:
            cur.execute("SELECT COUNT(*) FROM tickets WHERE event_id = %s AND booked = %s",(event_id,0))
            result = cur.fetchone()
            count = result[0]

            return jsonify({"count": count})

        except:
            return jsonify({"message": "Error getting event tickets"}), 500

        finally:
            cur.close()

if __name__ == '__main__':
    app.run(debug=True)

