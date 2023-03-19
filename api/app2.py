from flask import Flask, jsonify, request, url_for
from flask_mysqldb import MySQL
import yaml
import datetime
import jwt
import secrets
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

with open("db.yaml", "r") as stream:
    try:
        db = yaml.safe_load(stream)
    except yaml.YAMLError as e:
        print(e)

app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(app)

key = secrets.token_hex(32)
key_expiration = datetime.datetime.now() + datetime.timedelta(minutes=30)
    
scheduler = BackgroundScheduler()

@scheduler.scheduled_job('interval', minutes=15)
def is_key_expired():
    global key, key_expiration

    if datetime.datetime.now() >= key_expiration:   
        key = secrets.token_hex(32)
        key_expiration = datetime.datetime.now() + datetime.timedelta(minutes=30)
        print('Key expired. New key generated.')

scheduler.start()

def create_table():
    
    with mysql.connection.cursor() as cur:
        try:
        
            query = """CREATE TABLE IF NOT EXISTS ticket (
                    ticket_id INT AUTO_INCREMENT PRIMARY KEY,                   
                    event_id INT NOT NULL,
                    price INT NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    user_id INT NOT NULL,
                    booking_date DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            cur.execute(query)
            mysql.connection.commit()
    
        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"message": f"Error creating ticket table: {e}"}), 500

@app.route("/", methods =["GET"])
def home():
    create_table()
    is_key_expired()

    return jsonify({"message": "Table created"}),200

@app.route("/ticket", methods=["POST"])
def book_ticket():

    try:
        
        booking_data = request.get_json()

        required_fields = ["user_id", "event_id", "price", "ticket_type"]
        for field in required_fields:
            if field not in booking_data:
                return jsonify({"message": f"{field} is missing"}), 400

        user_id = booking_data["user_id"]
        event_id = booking_data["event_id"]
        price = booking_data["price"]
        ticket_type = booking_data["ticket_type"]

        with mysql.connection.cursor() as cur:
        
            booking_date = datetime.datetime.now()
            query = "INSERT INTO ticket(event_id, price, type, user_id, booking_date) VALUES (%s, %s, %s, %s, %s)"
            cur.execute(query, (event_id, price, ticket_type, user_id, booking_date))
            mysql.connection.commit()

            ticket_id = cur.lastrowid
        
            return jsonify({
                "message": "Ticket booked",
                "ticket_id": ticket_id,
                "user_id": user_id,
                "event_id": event_id,
                "price": price,
                "type": ticket_type,
                "booking_date": booking_date.strftime("%Y-%m-%d %H:%M")
            })

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"message": f"Error booking ticket: {e}"}), 500


@app.route("/ticket/<ticket_id>", methods=["DELETE"])
def unbook_ticket(ticket_id):
    try:
        booking_data = request.get_json()

        if "user_id" not in booking_data:
            return jsonify({"message": "User ID is missing"}), 400

        user_id = booking_data["user_id"]

        with mysql.connection.cursor() as cur:
            query = "SELECT * FROM ticket WHERE ticket_id=%s AND user_id=%s"
            cur.execute(query, (ticket_id, user_id))
            booking = cur.fetchone()

            if booking is None:
                return jsonify({"message": "Ticket not found"}), 404

            query = "DELETE FROM ticket WHERE ticket_id=%s"
            cur.execute(query, (ticket_id,))
            mysql.connection.commit()

            return jsonify({"message": "Ticket unbooked"})

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"message": f"Error unbooking ticket: {e}"}), 500

@app.route("/ticket/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    
    booking_data = request.get_json()

    if "user_id" not in booking_data:
        return jsonify({"message": "User ID is missing"}), 400

    user_id = booking_data["user_id"]

    with mysql.connection.cursor() as cur:
        query = """
            SELECT event_id, price, type, booking_date FROM ticket WHERE ticket_id = %s AND user_id = %s LIMIT 1
        """
        cur.execute(query, (ticket_id, user_id))

        ticket = cur.fetchone()

        if ticket is None:
            return jsonify({"message": "Ticket not found"}), 404

        event_id, price, ticket_type, booking_date = ticket
   
        return jsonify({
            "event_id": event_id,
            "price": price,
            "type": ticket_type,
            "booking_date": booking_date.strftime("%Y-%m-%d %H:%M")
        })
        

@app.route("/ticket/user/tickets", methods=["GET"])
def get_tickets():

    try:
        booking_data = request.get_json()

        if "user_id" not in booking_data:
            return jsonify({"message": "User ID is missing"}), 400

        user_id = booking_data.get("user_id")
    
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 10, type=int)

        with mysql.connection.cursor() as cur:
           
            query = """
                SELECT event_id, price, type, booking_date 
                FROM ticket
                WHERE user_id = %s 
                ORDER BY booking_date DESC 
                LIMIT %s,%s
            """
            cur.execute(query, (user_id, (page - 1) * limit, limit))
            user_tickets = cur.fetchall()

            if not user_tickets:
                return jsonify({"message": "No tickets found for this user ID."}), 404

            formatted_tickets = []
            for ticket in user_tickets:
                event_id, price, ticket_type, booking_date = ticket
                formatted_ticket = {
                    "event_id": event_id,
                    "price": price,
                    "type": ticket_type,
                    "booking_date": booking_date.strftime("%Y-%m-%d %H:%M")
                }
                formatted_tickets.append(formatted_ticket)

            return jsonify({
                "tickets": formatted_tickets
            })

    except ValueError:
        return jsonify({"message": "Invalid page or limit parameter."}), 400

    except Exception as e:
        return jsonify({"message": f"Error getting user tickets: {e}"}), 500

@app.route('/ticket/<ticket_id>/trade', methods=['GET'])
def trade_ticket(ticket_id):

    try:
        trade_data = request.get_json()
        required_fields = ["seller_id", "seller_email", "buyer_id", "buyer_email"]
        for field in required_fields:
            if field not in trade_data:
                return jsonify({"message": f"{field} is missing"}), 400

        seller_id = trade_data["seller_id"]
        seller_email = trade_data["seller_email"]
        buyer_id = trade_data["buyer_id"]
        buyer_email = trade_data["buyer_email"]
 
        with mysql.connection.cursor() as cur:
            query = """
                SELECT event_id, price, type, booking_date  FROM ticket WHERE ticket_id=%s AND user_id = %s
            """
            cur.execute(query, (ticket_id,seller_id,))
            ticket = cur.fetchone()
            if ticket is None:
                return jsonify({'message': 'Ticket not found'}), 404
            
            if (key_expiration - datetime.datetime.now()) < datetime.timedelta(minutes=5):
                token_expiration = key_expiration
            else:
                token_expiration = datetime.datetime.now() + datetime.timedelta(minutes=5)
            
            payload = {
                'seller_id': seller_id,
                'seller_email': seller_email,
                'buyer_id': buyer_id,
                'buyer_email': buyer_email,
                'exp': token_expiration
            }
           
            token = jwt.encode(payload, key , algorithm='HS256')
      
            sell_url = url_for('complete_trade', ticket_id=ticket_id, token=token, _external=True)
           
            event_id, price, ticket_type, booking_date = ticket
    
            return jsonify({
                "url": sell_url,
                "ticket": {
                    "event_id": event_id,
                    "price": price,
                    "type": ticket_type,
                    "booking_date": booking_date.strftime("%Y-%m-%d %H:%M")
                },
                'seller_id': seller_id,
                'seller_email': seller_email,
                'buyer_id': buyer_id,
                'buyer_email': buyer_email,
            })

    except Exception as e:
        return jsonify({"message": "Error trading the tickets: {e}"}), 500

@app.route('/ticket/<ticket_id>/complete_trade/<token>', methods=['GET'])
def complete_trade(ticket_id, token):

    try:
        decoded_token = jwt.decode(token, key, algorithms=['HS256'])
        expiration_timestamp = decoded_token.get('exp')
        current_timestamp = datetime.datetime.now().timestamp()

        if current_timestamp >= expiration_timestamp:
            raise jwt.ExpiredSignatureError('Token has expired')

        seller_id = decoded_token.get('seller_id')
        buyer_id = decoded_token.get('buyer_id')

        with mysql.connection.cursor() as cur:
            query = """
                UPDATE ticket SET user_id=%s WHERE ticket_id=%s AND user_id=%s
            """
            cur.execute(query,(buyer_id, ticket_id, seller_id))
            mysql.connection.commit()

        return jsonify({'message': 'Ticket sale completed'})

    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token has expired. Please generate a new one.'}), 401

    except jwt.exceptions.DecodeError:
        return jsonify({'message': 'Invalid token format. Please provide a valid token.'}), 401

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': f'Error completing the ticket sale: {e}'}), 500

if __name__ == '__main__':
    app.run(debug=True)

