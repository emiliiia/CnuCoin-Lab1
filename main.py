from database import init_db, create_transaction, generate_user, approve_transaction
import sqlite3

if __name__ == "__main__":
    # Ініціалізація БД
    init_db()
    
    # Створення користувачів
    user1 = generate_user()
    user2 = generate_user()
    miner = generate_user(is_miner=True)
    
    print(f"Користувач 1: {user1}")
    print(f"Користувач 2: {user2}")
    print(f"Майнер: {miner}")
    
    # Виконання транзакції
    try:
        tx_hash = create_transaction(user1, user2, 50.0)
        print(f"Транзакція створена: {tx_hash}")
        
        # Підтвердження транзакції майнером
        cursor = sqlite3.connect('cnucoin.db').cursor()
        cursor.execute('SELECT TADNum FROM TransactionsTable WHERE TAHash = ?', (tx_hash,))
        tx_id = cursor.fetchone()[0]
        
        approve_transaction(miner, tx_id)
        print("Транзакція підтверджена майнером")
    except ValueError as e:
        print(f"Помилка: {e}")