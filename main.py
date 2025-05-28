import sqlite3
from datetime import datetime
from database import init_db, generate_user, create_transaction, mine_block

def print_user_balance(user_id):
    """Функція для виводу балансу користувача"""
    conn = sqlite3.connect('cnucoin.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT SUM(CASE WHEN ToAddress = ? THEN Amount ELSE 0 END) - 
           SUM(CASE WHEN FromAddress = ? THEN Amount ELSE 0 END)
    FROM EWalletTable
    WHERE CNUCoinID = ? OR FromAddress = ? OR ToAddress = ?
    ''', (user_id, user_id, user_id, user_id, user_id))
    balance = cursor.fetchone()[0] or 0
    conn.close()
    return balance

def print_transaction_details(transaction_id):
    """Функція для виводу деталей транзакції"""
    conn = sqlite3.connect('cnucoin.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT TADNum, FromAddress, ToAddress, ASum, TAHash 
    FROM TransactionsTable 
    WHERE TADNum = ?
    ''', (transaction_id,))
    tad_num, from_addr, to_addr, amount, ta_hash = cursor.fetchone()
    
    print(f"\n1. Транзакція підтверджена: ID {tad_num}")
    print(f"   - Відправник: {from_addr} (Баланс: {print_user_balance(from_addr)} CNUCoin)")
    print(f"   - Отримувач: {to_addr} (Баланс: {print_user_balance(to_addr)} CNUCoin)")
    print(f"   - Сума: {amount} CNUCoin")
    print(f"   - Хеш транзакції: {ta_hash[:8]}...{ta_hash[-8:]}")
    conn.close()

def print_mining_results(result):
    """Функція для виводу результатів майнінгу"""
    conn = sqlite3.connect('cnucoin.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM BlockChainTable')
    block_number = cursor.fetchone()[0]
    
    print("\n2. Знайдений блок:")
    print(f"   - Номер блоку: {block_number}")
    print(f"   - Хеш: {result['new_block_hash']}")
    print(f"   - Nonce: {result['nonce']}")
    print(f"   - Час майнінгу: {result['mining_time']} сек")
    print(f"   - Блок додано до ланцюга")
    conn.close()

def print_miner_reward(miner_id):
    """Функція для виводу винагороди майнера"""
    conn = sqlite3.connect('cnucoin.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT Amount FROM EWalletTable 
    WHERE ToAddress = ? 
    ORDER BY TransactionDate DESC 
    LIMIT 1
    ''', (miner_id,))
    reward = cursor.fetchone()[0]
    print(f"\n3. Винагорода майнера:")
    print(f"   - {reward} CNUCoin (зараховано на гаманець {miner_id})")
    print(f"   - Новий баланс майнера: {print_user_balance(miner_id)} CNUCoin")
    conn.close()

def print_blockchain_stats():
    """Функція для виводу статистики блокчейну"""
    conn = sqlite3.connect('cnucoin.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM BlockChainTable')
    blocks_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM TransactionsTable WHERE TApproved = 1')
    confirmed_tx = cursor.fetchone()[0]
    
    print("\n4. Статистика блокчейну:")
    print(f"   - Всього блоків: {blocks_count}")
    print(f"   - Підтверджених транзакцій: {confirmed_tx}")
    conn.close()

if __name__ == "__main__":
    # Ініціалізація БД
    init_db()
    
    # Створення користувачів
    print("Створення користувачів...")
    user1 = generate_user()
    user2 = generate_user()
    miner = generate_user(is_miner=True)
    print(f"   - Користувач 1: {user1} (Баланс: {print_user_balance(user1)} CNUCoin)")
    print(f"   - Користувач 2: {user2} (Баланс: {print_user_balance(user2)} CNUCoin)")
    print(f"   - Майнер: {miner} (Баланс: {print_user_balance(miner)} CNUCoin)")

    # Виконання транзакції
    print("\nВиконання транзакції...")
    create_transaction(user1, user2, 50.0)
    print("   - Транзакція на 50.0 CNUCoin створена")

    # Майнінг
    print("\nПочаток майнінгу...")
    result = mine_block(miner)
    
    # Деталізований вивід
    print("\nРезультати майнінгу:")
    print("----------------------------------")
    print_transaction_details(result['transaction_id'])
    print_mining_results(result)
    print_miner_reward(miner)
    print_blockchain_stats()
    print("\nМайнінг завершено успішно!")