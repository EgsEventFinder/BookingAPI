from flask import Flask, jsonify, request, url_for
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
import yaml
import datetime
import jwt
import secrets
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

db = yaml.load(open('db.yaml'), Loader=yaml.Loader)
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']
app.config['MAIL_SERVER'] = 'smtp-mail.outlook.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'eventFinderUA@outlook.com'
app.config['MAIL_PASSWORD'] = 'UaDETIegs'

mysql = MySQL(app)
mail = Mail(app)

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

# start the scheduler
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
    
        except:
            mysql.connection.rollback()
            return jsonify({"message": "Error creating table"}), 500

        finally:
            cur.close()

@app.route("/", methods =["GET"])
def home():
    create_table()
    is_key_expired()

    return jsonify({"message": "Table created"}),200

@app.route("/ticket", methods=["POST"])
def book_ticket():

    booking_data = request.get_json()
    user_id = booking_data["user_id"]
    event_id = booking_data["event_id"]
    price = booking_data["price"]
    ticket_type = booking_data["ticket_type"]

    with mysql.connection.cursor() as cur:
        try:
            
            booking_date = datetime.datetime.now()          
          
            cur.execute("INSERT INTO ticket(event_id,price,type,user_id,booking_date) VALUES (%s,%s,%s,%s,%s)", (event_id, price,ticket_type,user_id,booking_date))
            mysql.connection.commit()

            return jsonify({"message": "Ticket booked"})

        except:
            mysql.connection.rollback()
            return jsonify({"message": "Error booking ticket"}), 500

        finally:
            cur.close()

@app.route("/ticket/<ticket_id>", methods=["DELETE"])
def unbook_ticket(ticket_id):

    user_id = 1
    with mysql.connection.cursor() as cur:
        try:
            cur.execute("SELECT * FROM ticket WHERE ticket_id=%s AND user_id = %s", (ticket_id,user_id,))
            booking = cur.fetchone()
          
            if booking is None:
                return jsonify({"message": "Ticket not found"}), 404

            cur.execute("DELETE FROM ticket WHERE ticket_id=%s", (ticket_id,))
    
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
                SELECT event_id, price, type, booking_date FROM ticket WHERE ticket_id = %s AND user_id = %s
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

@app.route("/ticket/user/tickets", methods=["GET"])
def get_tickets():
    user_id = 2
    
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    offset = (page - 1) * limit
    
    with mysql.connection.cursor() as cur:
        try:
            query = """
                SELECT event_id, price, type, booking_date 
                FROM ticket
                WHERE user_id = %s 
                ORDER BY booking_date DESC 
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

@app.route('/ticket/<ticket_id>/trade', methods=['GET'])
def trade_ticket(ticket_id):

    seller_id = 2
    seller_email = "miguel.angelo.tavares@hotmail.com"
    buyer_id = 1
    buyer_email = "buyer@example.com"

    with mysql.connection.cursor() as cur:
        try:
            cur.execute("SELECT * FROM ticket WHERE ticket_id=%s AND user_id = %s", (ticket_id,seller_id,))
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
            message = Message(subject='Ticket sold',
                            sender='eventFinderUA@outlook.com',
                            recipients=[seller_email],
                            body=f'Your ticket has been sold. Click here to complete the sale: {sell_url}')
            mail.send(message)
            
            
            return jsonify({'success': True})

        except:
            return jsonify({"message": "Error trading the tickets"}), 500

        finally:
            cur.close()

@app.route('/ticket/<ticket_id>/complete_trade/<token>', methods=['GET'])
def complete_trade(ticket_id, token):

    with mysql.connection.cursor() as cur:
        try:
            decoded_token = jwt.decode(token, key, algorithms=['HS256'])
            expiration_timestamp = decoded_token['exp']
            current_timestamp = datetime.datetime.now().timestamp()
            if current_timestamp >= expiration_timestamp:
                raise Exception("Token has expired")

            seller_id = decoded_token['seller_id']
            buyer_id = decoded_token['buyer_id']
            cur.execute("UPDATE ticket SET user_id=%s WHERE ticket_id=%s AND user_id = %s", (buyer_id,ticket_id,seller_id))
            mysql.connection.commit()
    
            return jsonify({'message': 'Ticket sale completed'})

        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except:
            return jsonify({'message': 'Invalid token'}), 401

'''
@app.route("/tickets/<event_id>", methods=["GET"])
def get_number_event_tickets(event_id):
    with mysql.connection.cursor() as cur:
        try:
            cur.execute("SELECT COUNT(*) FROM ticket WHERE event_id = %s",(event_id))
            result = cur.fetchone()
            count = result[0]

            return jsonify({"Number of booked tickets": count})

        except:
            return jsonify({"message": "Error getting event tickets"}), 500

        finally:
            cur.close()
'''
if __name__ == '__main__':
    app.run(debug=True)

