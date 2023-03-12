import jwt
import datetime
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
public_key = private_key.public_key()

# Serialize the keys to PEM format
private_key_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

public_key_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Sample payload data
payload = {
    "user_id": 1234,
    "name": "John Doe",
    "email": "johndoe@example.com",
    "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=60)
}

# Encoding the JWT token with private key
jwt_token = jwt.encode(payload, private_key_pem, algorithm='RS256')

# Decoding the JWT token with public key
decoded_token = jwt.decode(jwt_token, public_key_pem, algorithms=['RS256'])

print("Encoded JWT token: ", jwt_token)
print("Decoded JWT token: ", decoded_token)