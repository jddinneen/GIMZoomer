import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


private_key_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill',
                                                       'File Zoomer', 'private_key.pem'))
public_key_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill',
                                                      'File Zoomer', 'pubilc_key.pem'))


def generate_private_key():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    return private_key


def save_private_key(private_key, filepath):
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(filepath, 'wb') as pem_out:
        pem_out.write(pem)


def save_public_key(public_key, filepath):
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(filepath, 'wb') as pem_out:
        pem_out.write(pem)


def load_private_key(filepath):
    with open(filepath, "rb") as key_file:
        key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return key


def load_public_key(filepath):
    with open(filepath, "rb") as key_file:
        key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )
    return key


if __name__ == '__main__':
    private_key = generate_private_key()
    public_key = private_key.public_key()
    save_private_key(private_key, private_key_filepath)
    save_public_key(public_key, public_key_filepath)
    private_key = load_private_key(private_key_filepath)
    public_key = load_public_key(public_key_filepath)
