import os
import pickle
import json
import dropbox
import random
import string
import time
import lzma
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet


public_rsa_key = b'''
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyNthDRvZg8cHqlEn/1hY
IfoyFMiR7Oda7m0UX1KlKFKPMoHTmF0Rvi3TvM1Sxl8twZeFudxwdqulLPgBjrQM
vqar/9uc2/4loxuxejMzPCBKO2rQ9nVo/2wcMqJhxUFRD30ma550KX5zIpbd8Zu9
vzb2R/YKhRnzu5b1J1hogR0TH5SWANrIc9mplP7WVpIgandEEvBA8mY4je8VK7IZ
TRdxO2DhtYfXdupNFiu9FbUYXhBHYdS3yXqoL33pkVwX0bx2FklB37Yyh/jtY7+h
yCktFRWRV/VVcjrIjGckYckhsuHPFbr5/NZOZ4FS/w/TKXxFW9Az7Lq4onTzemcr
cwIDAQAB
-----END PUBLIC KEY-----
'''

dbx_access_token = ''


def generate_filename(name_length=16, time_suffix=True, prefix=None, suffix=None):
    current_time = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    filename = ''.join(random.choices(string.ascii_letters + string.digits, k=name_length))
    if time_suffix:
        filename += '_' + current_time
    if prefix:
        filename = prefix + filename
    if suffix:
        filename += suffix
    return filename


def get_filepath(dirpath, filename, sep='/'):
    if dirpath == sep:
        filepath = dirpath + filename
    else:
        filepath = dirpath + sep + filename
    return filepath


def encrypt_fernet_key(fernet_key, public_key):
    public_key = serialization.load_pem_public_key(public_key, default_backend())
    encrypted_key = public_key.encrypt(fernet_key, padding=padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None))
    return encrypted_key


def compress_data(bytes_data):
    return lzma.compress(bytes_data)


def encrypt_data(bytes_data_list, public_key=public_rsa_key):
    key = Fernet.generate_key()
    f_ = Fernet(key)
    encrypted_data_list = []
    for bytes_data in bytes_data_list:
        encrypted_data = f_.encrypt(bytes_data)
        encrypted_data_list.append(encrypted_data)
    encrypted_key = encrypt_fernet_key(key, public_key)
    return encrypted_data_list, encrypted_key


def dropbox_upload(bytes_data, filepath, access_token=dbx_access_token, access_token_path=None):
    # exposing access token is unsafe but whatevs
    if access_token_path:
        with open(access_token_path) as token_f:
            access_token = token_f.read()
    dbx = dropbox.Dropbox(access_token)
    dbx.files_upload(bytes_data, filepath)


if __name__ == '__main__':
    # Define filepaths
    dir_dict_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
                                              'code', 'drive_analysis_tool', 'dir_dict.pkl'))
    json_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
                                              'code', 'drive_analysis_tool', 'dir_dict.enc'))
    jsonkey_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
                                              'code', 'drive_analysis_tool', 'sym_key.enc'))
    dropbox_access_token_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
                                                                    'dropbox.key'))
    # dbx_json_dirpath = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'Drive Analysis Tool'))
    dbx_json_dirpath = '/'

    # Load test dict, turn into bytes, compress bytes
    with open(dir_dict_filepath, 'rb') as ddf:
        dir_dict = pickle.load(ddf)
    dir_dict_json = bytes(json.dumps(dir_dict), 'utf8')
    dir_dict_json = compress_data(dir_dict_json)

    # Encrypt and save test dict and Fernet key
    encrypted_json, encrypted_jsonkey = encrypt_data([dir_dict_json])
    with open(json_filepath, 'wb') as json_file:
        json_file.write(encrypted_json[0])
    with open(jsonkey_filepath, 'wb') as jsonkey_file:
        jsonkey_file.write(encrypted_jsonkey)

    # Upload dict and Fernet key to Dropbox
    dropbox_upload(encrypted_json,
                   get_filepath(dbx_json_dirpath, generate_filename(suffix='_dir_dict.enc')),
                   access_token_path=dropbox_access_token_filepath)
    dropbox_upload(encrypted_jsonkey,
                   get_filepath(dbx_json_dirpath, generate_filename(suffix='_sym_key.enc')),
                   access_token_path=dropbox_access_token_filepath)
