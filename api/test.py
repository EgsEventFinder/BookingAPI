import stripe
from flask import Flask, jsonify, redirect, request

stripe.api_key = "sk_test_51Mql9oBCNK7ep8avS2QCOVNOAxJBnh0rJTkw4xT58aDUoCd28Wde2n5rOmQZ05pvqn7d9nHfhxlgvNveRixwpTAF00YvqrrP4Q"

app = Flask(__name__)
'''
@app.route("/", methods=["GET"])
def stripe_test():

    try:
        
        card_token = stripe.Token.create(
            card={
                "number": "5555555555554444",
                "exp_month": 12,
                "exp_year": 2025,
                "cvc": "123"
            }
        )
       
        customer = stripe.Customer.list(email="john.doe@example.com")
    
        if customer.data:
            
            customer_id = customer.data[0].id
            sources = stripe.Customer.list_sources(
                customer_id,
                object='card'
            )
            sources = stripe.Customer.list_sources(
                customer_id,
                object='card'
            )
            existing_card = None
            for source in sources:
                if source.fingerprint == stripe.Token.retrieve(card_token.id).card.fingerprint:
                    existing_card = source
                    break
        
            if existing_card:
                card = existing_card

            else:
                card = stripe.Customer.create_source(
                    customer_id,
                    source=card_token
                )
        else:
            customer = stripe.Customer.create(
                name="John Doe",
                email="john.doe@example.com",
                source=card_token
            )
            customer_id = customer.id
            sources = stripe.Customer.list_sources(
                customer_id,
                object='card'
            )
            card = sources.data[0]

        # Charge the customer for the ticket price
        charge = stripe.Charge.create(
            amount=1000,
            currency="eur",
            description=f"Booking ticket for Miguel on event FCP vs SLB",
            customer=customer_id,
            source=card.id,
        )

        refund = stripe.Refund.create(
            charge=charge.id,
            amount=1000
        )

        #charges = stripe.Charge.list(customer=customer_id, expand=["data.refunds"]).data

        # Check if the charge was successful
        if charge.status == "succeeded":
            print("Transaction succeeded!")
            return jsonify({
                "customer_id": customer_id,
            }),200
        else:
            return jsonify({
                "Error": "Charge failed."
            }),400
    

    except Exception as e:
        return jsonify({"message": f"Error: {e}"}), 500
'''    
@app.route("/", methods=["GET"])
def checkout():
    try:
        '''
        product = stripe.Product.create(
            name='Event Registration',
        )

        # Create a Price for conference registration
        conference_price = stripe.Price.create(
            unit_amount=5000,
            currency='eur',
            product=product.id,
            metadata={
                'name': 'Conference Registration',
            },
        )
        print(conference_price)
        # Create a Price for workshop registration
        workshop_price = stripe.Price.create(
            unit_amount=2500,
            currency='eur',
            product=product.id,
            metadata={
                'name': 'Workshop Registration',
            },
        )
        price_metadata_name = "Conference Registration"
        # Retrieve a list of Prices for the given Stripe Product
        prices = stripe.Price.list(
            product=product.id,
        ).data

        # Filter the Prices based on the metadata name
        matching_prices = [price for price in prices if price.metadata.get('name') == price_metadata_name]

        # Check if any matching Prices were found
        if matching_prices:
            # A matching Price was found
            price = matching_prices[0]
    
            print(f"Price with metadata name '{price_metadata_name}' already exists!")
        else:
            print(f"No Price with metadata name '{price_metadata_name}' was found")
            price = stripe.Price.create(
                unit_amount=1000,
                currency='eur',
                product = product.id
            )
        '''
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': 'price_1Ms1jNBCNK7ep8av6AvFB9o7',
                'quantity': 1,
            }],
            metadata = {
                "event_id": 1,
                "price": 50,
                "ticket_type": "ticket_type",
                "user_id": 2,
            },
            mode='payment',
            success_url=request.url_root + "success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.url_root + "cancel",
        )
        
        return redirect(session.url, code=303)
        
    except Exception as e:
        return jsonify({"message": f"Error: {e}"}), 500


@app.route("/success", methods=["GET"])
def success():
    try:
        
        session_id = request.args.get("session_id")
        session = stripe.checkout.Session.retrieve(session_id)
        print(session.metadata)

        event_id = session.metadata.get("event_id")
        price = session.metadata.get("price")
        ticket_type = session.metadata.get("ticket_type")
        user_id = session.metadata.get("user_id")
        payment_intent_id = session.payment_intent
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        if payment_intent.status == "succeeded":    
            # The payment was successful
            return jsonify({
                "message": "Payment succeeded!",
            }), 200
        else:
            # The payment was not successful
            return jsonify({
                "message": "Payment failed.",
                "session_id": session_id
            }), 400
    except Exception as e:
        return jsonify({"message": f"Error: {e}"}), 500


@app.route("/cancel", methods=["GET"])
def cancel():
    return jsonify({
        "message": "Payment was canceled by the user."
    }), 200

if __name__ == '__main__':
    app.run(debug=True)