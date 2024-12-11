import logging
import re
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE
from utils import get_settings, save_group_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]

# Define the replacement patterns
replacements = [
    (r"\bAuds\b", "Audios"),
    (r"\bAud\b", "Audio"),
    (r"\bOrg\b", "Original"),
    (r"\bTam\b", "Tamil"),
    (r"\bTel\b", "Telugu"),
    (r"\bHin\b", "Hindi"),
    (r"\bEng\b", "English"),
    (r"\bMal\b", "Malayalam"),
    (r"\bKan\b", "Kannada"),
    (r"\bKor\b", "Korean"),
    (r"\bChi\b", "Chinese"),
]

async def save_file(media):
    """Save file in database"""

    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = str(media.file_name)  # Directly use the file name without re.sub

    # Apply the replacements to the file name
    for pattern, replacement in replacements:
        file_name = re.sub(pattern, replacement, file_name)

    unwanted_chars = ['[', ']', '(', ')']
    for char in unwanted_chars:
        file_name = file_name.replace(char, '')
    
    file_name = ' '.join(filter(lambda x: not x.startswith('@'), file_name.split()))
    
    file = {
        'file_id': file_id,
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': media.caption.html if media.caption else None
    }

    found1 = {'file_name': file_name}
    found = {'file_id': file_id}
    
    check1 = col.find_one(found1)
    if check1:
        print(f"{file_name} is already saved.")
        return False, 0
    
    check = col.find_one(found)
    if check:
        print(f"{file_name} is already saved.")
        return False, 0
    
    if MULTIPLE_DATABASE == True:
        check3 = sec_col.find_one(found)
        if check3:
            print(f"{file_name} is already saved.")
            return False, 0
        check2 = sec_col.find_one(found1)
        if check2:
            print(f"{file_name} is already saved.")
            return False, 0
        result = db.command('dbstats')
        data_size = result['dataSize']
        if data_size > 503316480:
            try:
                sec_col.insert_one(file)
                print(f"{file_name} is successfully saved.")
                return True, 1
            except DuplicateKeyError:
                print(f"{file_name} is already saved.")
                return False, 0
        else:
            try:
                col.insert_one(file)
                print(f"{file_name} is successfully saved.")
                return True, 1
            except DuplicateKeyError:
                print(f"{file_name} is already saved.")
                return False, 0
    else:
        try:
            col.insert_one(file)
            print(f"{file_name} is successfully saved.")
            return True, 1
        except DuplicateKeyError:
            print(f"{file_name} is already saved.")
            return False, 0

def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0

    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0

            r += bytes([i])

    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")
    
