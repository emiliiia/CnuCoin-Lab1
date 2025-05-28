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
import sqlite3
import datetime
import random
import os
import hashlib
import time

# Ініціалізація бази даних
def init_db():
    DB_PATH = os.path.abspath('cnucoin.db')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Створення таблиць
    tables = [
        '''CREATE TABLE IF NOT EXISTS CnuCoinMembersTable (
            CNUCoinID INTEGER PRIMARY KEY,
            PublicKey TEXT NOT NULL,
            IsMiner BOOLEAN NOT NULL DEFAULT 0
        )''',
        
        '''CREATE TABLE IF NOT EXISTS PrivateTable (
            CNUCoinID INTEGER PRIMARY KEY,
            PrivateKey TEXT NOT NULL,
            PublicKey TEXT NOT NULL,
            FOREIGN KEY (CNUCoinID) REFERENCES CnuCoinMembersTable(CNUCoinID)
        )''',
        
        '''CREATE TABLE IF NOT EXISTS EWalletTable (
            CNUCoinID INTEGER,
            TransactionDate DATETIME NOT NULL,
            FromAddress INTEGER,
            ToAddress INTEGER NOT NULL,
            Amount REAL,  
            FOREIGN KEY (CNUCoinID) REFERENCES CnuCoinMembersTable(CNUCoinID)
        )''',
        
        '''CREATE TABLE IF NOT EXISTS TransactionsTable (
            CNUCoinID INTEGER,
            TransactionDateTime DATETIME NOT NULL,
            TADNum INTEGER PRIMARY KEY AUTOINCREMENT,
            FromAddress INTEGER NOT NULL,
            ToAddress INTEGER NOT NULL,
            TAHash TEXT,
            Nonce INTEGER,
            TApproved BOOLEAN DEFAULT 0,
            Assign TEXT,
            ASum REAL,  
            FOREIGN KEY (CNUCoinID) REFERENCES CnuCoinMembersTable(CNUCoinID)
        )''',
        
        '''CREATE TABLE IF NOT EXISTS BlockChainTable (
            MineID INTEGER,
            DateTime DATETIME NOT NULL,
            BlockChainHash TEXT,
            Nonce INTEGER,
            Blockssign TEXT,
            FOREIGN KEY (MineID) REFERENCES CnuCoinMembersTable(CNUCoinID)
        )'''
    ]
    
    for table in tables:
        cursor.execute(table)
    
    # Ініціалізація BlockChainTable
    cursor.execute('SELECT COUNT(*) FROM BlockChainTable')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
        INSERT INTO BlockChainTable (MineID, DateTime, BlockChainHash, Nonce, Blockssign)
        VALUES (0, datetime('now'), '0', 0, '0')
        ''')
    
    conn.commit()
    conn.close()

def generate_user(is_miner=False):
    # Генерування ключів RSA
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    public_key = private_key.public_key()
    
    # Серіалізація ключів
    private_pem = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption()
    ).decode('utf-8')
    
    public_pem = public_key.public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    # Генерування CNUCoinID як хешу публічного ключа
    public_key_bytes = public_pem.encode('utf-8')
   
    # Генеруємо CNUCoinID як 32-бітне число (8 символів MD5 у hex)
    md5_hash = hashlib.md5(public_key_bytes).hexdigest()
    cnu_coin_id = int(md5_hash[:8], 16)  # Обмежуємо до 8 символів (32 біти)

    # Збереження в базу даних
    conn = sqlite3.connect('cnucoin.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO CnuCoinMembersTable (CNUCoinID, PublicKey, IsMiner)
    VALUES (?, ?, ?)
    ''', (cnu_coin_id, public_pem, is_miner))
    
    cursor.execute('''
    INSERT INTO PrivateTable (CNUCoinID, PrivateKey, PublicKey)
    VALUES (?, ?, ?)
    ''', (cnu_coin_id, private_pem, public_pem))
    
    # Нарахування початкових коштів (100 CNUCoin)
    cursor.execute('''
    INSERT INTO EWalletTable (CNUCoinID, TransactionDate, FromAddress, ToAddress, Amount)
    VALUES (?, ?, 0, ?, 100.0)
    ''', (cnu_coin_id, datetime.datetime.now(), cnu_coin_id))
    
    conn.commit()
    conn.close()
    
    return cnu_coin_id


def create_transaction(from_id, to_id, amount):
    conn = sqlite3.connect('cnucoin.db')
    cursor = conn.cursor()
    
    # Перевірка балансу
    cursor.execute('''
    SELECT SUM(Amount) FROM EWalletTable 
    WHERE ToAddress = ? AND CNUCoinID = ?
    ''', (from_id, from_id))
    balance = cursor.fetchone()[0] or 0
    
    cursor.execute('''
    SELECT SUM(Amount) FROM EWalletTable 
    WHERE FromAddress = ? AND CNUCoinID = ?
    ''', (from_id, from_id))
    spent = cursor.fetchone()[0] or 0
    
    available = balance - spent
    if available < amount:
        raise ValueError("Недостатньо коштів для транзакції")
    
    # Отримання приватного ключа відправника
    cursor.execute('''
    SELECT PrivateKey FROM PrivateTable WHERE CNUCoinID = ?
    ''', (from_id,))
    private_key_pem = cursor.fetchone()[0]
    
    private_key = load_pem_private_key(
        private_key_pem.encode('utf-8'),
        password=None
    )
    
    # Отримання останнього хешу блокчейну
    cursor.execute('SELECT BlockChainHash, Nonce FROM BlockChainTable ORDER BY DateTime DESC LIMIT 1')
    last_block = cursor.fetchone()
    block_chain_hash = last_block[0] if last_block else '0'
    nonce = last_block[1] if last_block else 0
    
    # Створення транзакції
    transaction_data = {
        'from': from_id,
        'to': to_id,
        'amount': amount,
        'block_chain_hash': block_chain_hash,
        'nonce': nonce,
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    # Хешування транзакції
    transaction_str = f"{from_id}{to_id}{amount}{block_chain_hash}{nonce}"
    transaction_hash = hashlib.md5(transaction_str.encode('utf-8')).hexdigest()
    
    # Підпис транзакції
    signature = private_key.sign(
        transaction_hash.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    # Збереження транзакції
    cursor.execute('''
    INSERT INTO TransactionsTable (
        CNUCoinID, TransactionDateTime, FromAddress, ToAddress, 
        TAHash, Nonce, TApproved, Assign, ASum
    )
    VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
    ''', (
        from_id,
        datetime.datetime.now(),
        from_id,
        to_id,
        transaction_hash,
        random.randint(0, 2**32),
        signature.hex(),
        amount  # Додаємо суму транзакції
    ))
    
    # Оновлення BlockChainTable
    new_block_chain_hash = hashlib.md5((block_chain_hash + transaction_hash).encode('utf-8')).hexdigest()
    
    cursor.execute('''
    INSERT INTO BlockChainTable (MineID, DateTime, BlockChainHash, Nonce, Blockssign)
    VALUES (?, ?, ?, ?, ?)
    ''', (
        from_id,
        datetime.datetime.now(),
        new_block_chain_hash,
        random.randint(0, 2**32),  # Новий Nonce
        signature.hex()
    ))
    
    conn.commit()
    conn.close()
    
    return transaction_hash

def approve_transaction(miner_id, transaction_id):
    conn = sqlite3.connect('cnucoin.db')
    cursor = conn.cursor()
    
    # Перевірка майнера
    cursor.execute('SELECT IsMiner FROM CnuCoinMembersTable WHERE CNUCoinID = ?', (miner_id,))
    is_miner = cursor.fetchone()[0]
    if not is_miner:
        raise ValueError("Тільки майнери можуть підтверджувати транзакції")
    
    # Отримання даних транзакції (тепер з ASum)
    cursor.execute('''
    SELECT FromAddress, ToAddress, ASum FROM TransactionsTable WHERE TADNum = ?
    ''', (transaction_id,))
    from_addr, to_addr, amount = cursor.fetchone()
    
    if amount is None:
        raise ValueError("Сума транзакції не визначена")
    
    # Оновлення статусу транзакції
    cursor.execute('UPDATE TransactionsTable SET TApproved = 1 WHERE TADNum = ?', (transaction_id,))
    
    # Додавання запису до гаманця
    cursor.execute('''
    INSERT INTO EWalletTable (CNUCoinID, TransactionDate, FromAddress, ToAddress, Amount)
    VALUES (?, ?, ?, ?, ?)
    ''', (to_addr, datetime.datetime.now(), from_addr, to_addr, amount))
    
    conn.commit()
    conn.close()

def mine_block(miner_id):
    conn = sqlite3.connect('cnucoin.db')
    cursor = conn.cursor()
    
    # 1. Отримання першої непідтвердженої транзакції
    cursor.execute('''
    SELECT TADNum, FromAddress, ToAddress, ASum, TAHash 
    FROM TransactionsTable 
    WHERE TApproved = 0 
    ORDER BY TransactionDateTime ASC 
    LIMIT 1
    ''')
    transaction = cursor.fetchone()
    
    if not transaction:
        return "Немає транзакцій для підтвердження"
    
    tad_num, from_addr, to_addr, asum, ta_hash = transaction
    
    # 2. Отримання останнього хешу блокчейну
    cursor.execute('SELECT BlockChainHash, Nonce FROM BlockChainTable ORDER BY DateTime DESC LIMIT 1')
    last_block = cursor.fetchone()
    block_chain_hash = last_block[0] if last_block else '0'
    nonce = 0
    
    # 3. Підбір Nonce (майнінг)
    start_time = time.time()
    while True:
        data = f"{ta_hash}{block_chain_hash}{nonce}".encode()
        new_hash = hashlib.sha256(data).hexdigest()
        
        if new_hash.startswith('0'):  # Умова складності
            break
        nonce += 1
    
    mining_time = time.time() - start_time
    
    # 4. Запис нового блоку
    cursor.execute('''
    INSERT INTO BlockChainTable (MineID, DateTime, BlockChainHash, Nonce)
    VALUES (?, ?, ?, ?)
    ''', (miner_id, datetime.datetime.now(), new_hash, nonce))
    
    # 5. Підтвердження транзакції
    cursor.execute('UPDATE TransactionsTable SET TApproved = 1 WHERE TADNum = ?', (tad_num,))
    
    # 6. Винагорода майнеру (1 CNUCoin)
    cursor.execute('''
    INSERT INTO EWalletTable (CNUCoinID, TransactionDate, FromAddress, ToAddress, Amount)
    VALUES (?, ?, 0, ?, 1.0)
    ''', (miner_id, datetime.datetime.now(), miner_id))
    
    conn.commit()
    conn.close()
    
    return {
        'transaction_id': tad_num,
        'new_block_hash': new_hash,
        'nonce': nonce,
        'mining_time': f"{mining_time:.2f} сек"
    }