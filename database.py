# Коректні імпорти
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key,
    Encoding,
    PublicFormat,
    PrivateFormat,
    NoEncryption
)
import hashlib
import sqlite3
import time

def init_db():
    conn = sqlite3.connect('CNUCoin.db')
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS CNUCoinMemberTable
                    (CNUCoinID INTEGER PRIMARY KEY AUTOINCREMENT,
                     PPhQL1CKey TEXT NOT NULL,
                     Tshiner INTEGER DEFAULT 0,
                     Balance REAL DEFAULT 100.0)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS PrivateTable
                    (CNUCoinID INTEGER PRIMARY KEY,
                     PrivateKey TEXT NOT NULL,
                     FOREIGN KEY(CNUCoinID) REFERENCES CNUCoinMemberTable(CNUCoinID))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS TransactionTable
                    (TAID INTEGER PRIMARY KEY AUTOINCREMENT,
                     CNUCoinID INTEGER,
                     TADate TEXT,
                     FromAddr INTEGER,
                     ToAddr INTEGER,
                     TASum REAL,
                     TAMash TEXT,
                     Nonce INTEGER,
                     TAApproved INTEGER DEFAULT 0,
                     TASign TEXT,
                     FOREIGN KEY(CNUCoinID) REFERENCES CNUCoinMemberTable(CNUCoinID))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS BlockChainTable
                    (HlineTID INTEGER PRIMARY KEY AUTOINCREMENT,
                     DateTime TEXT,
                     BlockChainHash TEXT,
                     Nonce INTEGER,
                     BlockSign TEXT)''')
    
    conn.commit()
    conn.close()

def register_user(is_miner=False, initial_balance=100.0):
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    public_key = private_key.public_key()
    
    pem_public = public_key.public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    pem_private = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption()
    ).decode('utf-8')
    
    conn = sqlite3.connect('CNUCoin.db')
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO CNUCoinMemberTable (PPhQL1CKey, Tshiner, Balance) VALUES (?, ?, ?)",
                   (pem_public, 1 if is_miner else 0, initial_balance))
    user_id = cursor.lastrowid
    
    cursor.execute("INSERT INTO PrivateTable VALUES (?, ?)",
                   (user_id, pem_private))
    
    conn.commit()
    conn.close()
    return user_id

def create_transaction(sender_id, receiver_id, amount):
    conn = sqlite3.connect('CNUCoin.db')
    cursor = conn.cursor()
    
    # Check balance
    cursor.execute("SELECT Balance FROM CNUCoinMemberTable WHERE CNUCoinID=?", (sender_id,))
    sender_balance = cursor.fetchone()[0]
    
    if sender_balance < amount:
        conn.close()
        raise ValueError("Недостатньо коштів!")
    
    # Get last block
    cursor.execute("SELECT BlockChainHash, Nonce FROM BlockChainTable ORDER BY HlineTID DESC LIMIT 1")
    last_block = cursor.fetchone()
    prev_hash, prev_nonce = last_block if last_block else ("0", 0)
    
    # Prepare transaction data
    transaction_data = f"{sender_id}{receiver_id}{amount}{prev_hash}{prev_nonce}"
    ta_hash = hashlib.sha256(transaction_data.encode()).hexdigest()
    
    # Get private key
    cursor.execute("SELECT PrivateKey FROM PrivateTable WHERE CNUCoinID=?", (sender_id,))
    private_key_pem = cursor.fetchone()[0]
    private_key = load_pem_private_key(private_key_pem.encode(), password=None)
    
    # Sign transaction
    signature = private_key.sign(
        transaction_data.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    ).hex()
    
    # Add transaction
    cursor.execute('''INSERT INTO TransactionTable 
                    (CNUCoinID, TADate, FromAddr, ToAddr, TASum, TAMash, Nonce, TASign)
                    VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)''',
                 (sender_id, sender_id, receiver_id, amount, ta_hash, prev_nonce, signature))
    
    # Update balances
    cursor.execute("UPDATE CNUCoinMemberTable SET Balance = Balance - ? WHERE CNUCoinID=?", (amount, sender_id))
    cursor.execute("UPDATE CNUCoinMemberTable SET Balance = Balance + ? WHERE CNUCoinID=?", (amount, receiver_id))
    
    conn.commit()
    conn.close()
    return ta_hash

def mine_block(difficulty=2):
    """Функція майнінгу з Proof-of-Work"""
    conn = sqlite3.connect('CNUCoin.db')
    cursor = conn.cursor()
    
    # Get unapproved transactions
    cursor.execute("SELECT TAMash FROM TransactionTable WHERE TAApproved=0")
    transactions = [tx[0] for tx in cursor.fetchall()]
    
    if not transactions:
        conn.close()
        return False
    
    # Get last block
    cursor.execute("SELECT BlockChainHash, Nonce FROM BlockChainTable ORDER BY HlineTID DESC LIMIT 1")
    last_block = cursor.fetchone()
    prev_hash, prev_nonce = last_block if last_block else ("0", 0)
    
    target = '0' * difficulty
    nonce = 0
    start_time = time.time()
    
    while True:
        block_data = f"{prev_hash}{''.join(transactions)}{nonce}"
        block_hash = hashlib.sha256(block_data.encode()).hexdigest()
        
        if block_hash.startswith(target):
            # Add new block
            cursor.execute('''INSERT INTO BlockChainTable 
                            (DateTime, BlockChainHash, Nonce)
                            VALUES (datetime('now'), ?, ?)''',
                         (block_hash, nonce))
            
            # Mark transactions as approved
            cursor.execute("UPDATE TransactionTable SET TAApproved=1 WHERE TAApproved=0")
            
            conn.commit()
            conn.close()
            print(f"Блок знайдено! Nonce: {nonce}, час: {time.time()-start_time:.2f} сек")
            return True
        
        nonce += 1
        if nonce % 100000 == 0:  # Progress indicator
            print(f"Перевірено {nonce} значень...")

def verify_transaction(sender_id, transaction_data, signature):
    """Перевірка підпису транзакції"""
    conn = sqlite3.connect('CNUCoin.db')
    cursor = conn.cursor()
    
    try:
        # Get public key
        cursor.execute("SELECT PPhQL1CKey FROM CNUCoinMemberTable WHERE CNUCoinID=?", (sender_id,))
        public_key_pem = cursor.fetchone()[0]
        public_key = load_pem_public_key(public_key_pem.encode())
        
        # Verify signature
        public_key.verify(
            bytes.fromhex(signature),
            transaction_data.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        print(f"Помилка перевірки: {e}")
        return False
    finally:
        conn.close()