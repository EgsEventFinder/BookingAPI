from flask import Flask, jsonify, request, url_for
from flask_mysqldb import MySQL
from apscheduler.schedulers.background import BackgroundScheduler
import yaml
import datetime
import jwt
import secrets
import stripe


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

stripe.api_key = db['stripe_api_key']

mysql = MySQL(app)

key = secrets.token_hex(32)
key_expiration = datetime.datetime.now() + datetime.timedelta(minutes=30)
    
scheduler = BackgroundScheduler()

scheduler.start()

@scheduler.scheduled_job('interval', minutes=15)
def is_key_expired():
    global key, key_expiration

    if datetime.datetime.now() >= key_expiration:   
        key = secrets.token_hex(32)
        key_expiration = datetime.datetime.now() + datetime.timedelta(minutes=30)
        print('Key expired. New key generated.')
        
@app.before_first_request
def setup():
    create_tables()
    is_key_expired()

@app.route("/ticket", methods=["POST"])
def book_ticket():

    try:
        booking_data = request.get_json()
        print("Booking data -> ", booking_data)
        required_fields = ["user_id", "event_id", "price", "ticket_type", "event_name"]
        for field in required_fields:
            if field not in booking_data:
                return jsonify({"message": f"{field} is missing"}), 400
        
        user_id = booking_data["user_id"]
        event_id = booking_data["event_id"]
        ticket_price = booking_data["price"]
        ticket_type = booking_data["ticket_type"]
        event_name = booking_data["event_name"]

        session = create_session(event_name, ticket_type, event_id, ticket_price, user_id)
        
        return jsonify({
            "session_url": session.url,
            "session_id": session.id
        }), 200
    
    except Exception as e:
        return jsonify({"message": f"Error booking ticket: {e}"}), 500

@app.route("/ticket/cancel", methods=["GET"])
def cancel():
    return jsonify({
        "message": "Payment was canceled by the user."
    }), 200

@app.route("/ticket/success", methods=["GET", "POST"])
def success():
    try:
        if request.method == "GET":
            session_id = request.args.get("session_id")

            return jsonify({"message": "Payment was successful"})
        
        elif request.method == "POST":

            session_id = request.args.get("session_id")
            session = stripe.checkout.Session.retrieve(session_id)

            payment_intent_id = session.payment_intent
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            event_id = session.metadata.get("event_id")
            ticket_price = session.metadata.get("ticket_price")
            ticket_type = session.metadata.get("ticket_type")
            user_id = session.metadata.get("user_id")
            booking_date = datetime.datetime.now()

            if payment_intent.status == "succeeded":    

                with mysql.connection.cursor() as cur:
                    query = "INSERT INTO ticket(event_id, price, type, user_id, booking_date) VALUES (%s, %s, %s, %s, %s)"
                    cur.execute(query, (event_id, ticket_price, ticket_type, user_id, booking_date,))
                    mysql.connection.commit()

                    ticket_id = cur.lastrowid
            
                return jsonify({
                    "message": "Ticket booked",
                    "ticket_id": ticket_id,
                    "user_id": user_id,
                    "event_id": event_id,
                    "price": ticket_price,
                    "type": ticket_type,
                    "booking_date": format_date(booking_date)
                }),200
        
            else:
                return jsonify({
                    "message": "Payment failed.",
                }), 402
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"message": f"Error: {e}"}), 500

@app.route("/ticket/<ticket_id>", methods=["DELETE"])
def unbook_ticket(ticket_id):
    try:
        booking_data = request.get_json()

        if "user_id" not in booking_data:
            raise ValueError("User ID is missing")

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
    except ValueError as e:
        return jsonify({"message": f"Invalid query parameter: {e}"}), 400
    
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"message": f"Error unbooking ticket: {e}"}), 500

@app.route("/ticket/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    try:
        user_id = request.args.get("user_id", type=int)
        if user_id is None:
            raise ValueError("User ID is missing")
        
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
                "booking_date": format_date(booking_date)
            })
        
    except ValueError as e:
        return jsonify({"message": f"Invalid query parameter: {e}"}), 400
    
    except Exception as e:
        return jsonify({"message": f"Error getting user ticket: {e}"}), 500

@app.route("/ticket/user/tickets", methods=["GET"])
def get_tickets():

    try:
        user_id = request.args.get("user_id", type=int)

        if user_id is None:
            raise ValueError("User ID is missing")
        
        page = request.args.get("page",1, type=int)
        limit = request.args.get("limit",10, type=int)

        with mysql.connection.cursor() as cur:
           
            query = """
                SELECT ticket_id,event_id, price, type, booking_date 
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
                ticket_id, event_id, price, ticket_type, booking_date = ticket
                formatted_ticket = {
                    "ticket_id": ticket_id,
                    "event_id": event_id,
                    "price": price,
                    "type": ticket_type,
                    "booking_date": format_date(booking_date)
                }
                formatted_tickets.append(formatted_ticket)

            return jsonify({
                "tickets": formatted_tickets
            })
    except ValueError as e:
        return jsonify({"message": f"Invalid query parameter: {e}"}), 400
    
    except Exception as e:
        return jsonify({"message": f"Error getting user tickets: {e}"}), 500

@app.route('/ticket/<ticket_id>/trade', methods=['GET'])
def trade_ticket(ticket_id):

    try:
        seller_id = request.args.get("seller_id", type=int)
        seller_email = request.args.get("seller_email", type=str)
        buyer_id = request.args.get("buyer_id", type=int)
        buyer_email = request.args.get("buyer_email", type=str)

        if seller_id is None or seller_email is None or buyer_id is None or buyer_email is None:
            raise ValueError("One or more parameters are missing from the query.")
 
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
      
            trade_url = url_for('complete_trade', ticket_id=ticket_id, token=token, _external=True)
           
            event_id, price, ticket_type, booking_date = ticket
    
            return jsonify({
                "url": trade_url,
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
    except ValueError as e:
        return jsonify({"message": f"Invalid query parameter: {e}"}), 400
    
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
        trade_date = datetime.datetime.now()

        with mysql.connection.cursor() as cur:
            query = """
                UPDATE ticket SET user_id=%s, booking_date=%s WHERE ticket_id=%s AND user_id=%s
            """
            cur.execute(query,(buyer_id, trade_date, ticket_id, seller_id))
            mysql.connection.commit()

        return jsonify({'message': 'Ticket sale completed'}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token has expired. Please generate a new one.'}), 401

    except jwt.exceptions.DecodeError:
        return jsonify({'message': 'Invalid token format. Please provide a valid token.'}), 401

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': f'Error completing the ticket sale: {e}'}), 500

def create_tables():
    
    with mysql.connection.cursor() as cur:
        try:
            query_ticket = """CREATE TABLE IF NOT EXISTS ticket (
                ticket_id INT AUTO_INCREMENT PRIMARY KEY,                   
                event_id VARCHAR(50) NOT NULL,
                price INT NOT NULL,
                type VARCHAR(50) NOT NULL,
                user_id INT NOT NULL,
                booking_date DATETIME DEFAULT CURRENT_TIMESTAMP
            );"""
            
            cur.execute(query_ticket)
            mysql.connection.commit()
           
        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"message": f"Error creating tables: {e}"}), 500


def format_date(date):
    return date.strftime("%Y-%m-%d %H:%M:%S")
        
def get_product(event_name):
    product_id = None
    for product in stripe.Product.list():
        if product.name == event_name:
            print("Product Exists!!")
            product_id = product.id
            break

    if product_id is None:
        print("Product do not exist!!!")
        product = stripe.Product.create(name=event_name)
        product_id = product.id

    return product_id
    
def get_ticketType_price(event_name, ticket_type, ticket_price):

    product_id = get_product(event_name)
        
    prices = stripe.Price.list(
        product=product_id,
    ).data

    matching_prices = [price for price in prices if price.metadata.get('name') == ticket_type]

    if matching_prices:
        print("Type exists!!!")
        price = matching_prices[0]
    else:
        print("Type do not exists!!!")
        price = stripe.Price.create(
            unit_amount=ticket_price*100,
            currency='eur',
            product = product_id,
            metadata={
                'name': ticket_type,
            },
        )

    return price

def create_session(event_name, ticket_type,event_id,ticket_price, user_id):
    
    price = get_ticketType_price(event_name,ticket_type, ticket_price)
    
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': price.id,
            'quantity': 1,
        }],
        metadata = {
            "event_id": event_id,
            "ticket_price": ticket_price,
            "ticket_type": ticket_type,
            "user_id": user_id,
        },
        mode='payment',
        success_url = request.url_root + "ticket/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url = request.url_root + "ticket/cancel",
    )
    print("Session -> ", session)
    return session

if __name__ == '__main__':
    app.run(debug=True)