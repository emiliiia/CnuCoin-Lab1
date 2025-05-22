from database import init_db, register_user, create_transaction, mine_block, verify_transaction
import sqlite3

def print_database_stats():
    """Виводить статистику бази даних"""
    conn = sqlite3.connect('CNUCoin.db')
    cursor = conn.cursor()
    
    print("\n=== Статистика бази даних ===")
    
    # Users
    cursor.execute("SELECT CNUCoinID, Tshiner, Balance FROM CNUCoinMemberTable")
    users = cursor.fetchall()
    print("\nКористувачі:")
    for user in users:
        print(f"ID: {user[0]}, Майнер: {'Так' if user[1] else 'Ні'}, Баланс: {user[2]} CNUCoin")
    
    # Transactions
    cursor.execute("SELECT TAID, FromAddr, ToAddr, TASum, TAApproved FROM TransactionTable")
    transactions = cursor.fetchall()
    print("\nТранзакції:")
    for tx in transactions:
        status = "Підтверджено" if tx[4] else "Очікує"
        print(f"ID: {tx[0]}, Від: {tx[1]} → До: {tx[2]}, Сума: {tx[3]}, Статус: {status}")
    
    # Blockchain
    cursor.execute("SELECT HlineTID, BlockChainHash FROM BlockChainTable")
    blocks = cursor.fetchall()
    print("\nБлоки в ланцюгу:")
    for block in blocks:
        print(f"Блок {block[0]}: Хеш = {block[1][:16]}...")
    
    conn.close()

def main():
    # Ініціалізація БД
    init_db()
    print("=== Система CNUCoin ===")
    
    # Реєстрація користувачів
    print("\n1. Реєстрація користувачів...")
    alice = register_user(initial_balance=500.0)
    bob = register_user(initial_balance=100.0)
    miner = register_user(is_miner=True, initial_balance=0.0)
    print(f"Створено користувачів: Alice (ID: {alice}), Bob (ID: {bob}), Майнер (ID: {miner})")
    
    # Транзакція
    print("\n2. Виконання транзакції...")
    tx_amount = 150.0
    print(f"Транзакція: {alice} → {bob} ({tx_amount} CNUCoin)")
    tx_hash = create_transaction(alice, bob, tx_amount)
    print(f"Транзакція створена! Хеш: {tx_hash}")
    
    # Майнінг
    print("\n3. Майнінг блоку (складність = 2)...")
    if mine_block(difficulty=2):
        print("Майнінг успішний! Нові транзакції підтверджено.")
    else:
        print("Немає транзакцій для майнінгу")
    
    # Перевірка підпису
    print("\n4. Перевірка підпису транзакції...")
    conn = sqlite3.connect('CNUCoin.db')
    cursor = conn.cursor()
    cursor.execute("SELECT TAMash, TASign FROM TransactionTable WHERE TAID=1")
    tx_data, tx_sign = cursor.fetchone()
    print(f"Підпис транзакції: {'Валідний' if verify_transaction(alice, tx_data, tx_sign) else 'Невірний'}")
    conn.close()
    
    # Виведення статистики
    print_database_stats()

if __name__ == "__main__":
    main()