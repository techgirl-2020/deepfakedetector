import pika
import json
import pymysql
import time
import os

"""
Detection Log Worker
--------------------
Consumes 'detection_logs' messages from RabbitMQ and saves them 
to the 'user_db' MySQL database for persistent audit trails.
"""
print("Worker Service starting...")

# Wait for RabbitMQ and DB to be ready during container startup
time.sleep(10)

# Connect to MySQL to save logs
def get_db_connection():
    return pymysql.connect(
        host='user-db',
        user='root',
        password='root1234',
        database='user_db',
        charset='utf8mb4'
    )

# Create logs table if it doesn't exist
def setup_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detection_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            username VARCHAR(150),
            image_name VARCHAR(255),
            result VARCHAR(10),
            confidence FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()
    print("Database table ready!")

# Save log to MySQL
def save_log(data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO detection_logs 
            (user_id, username, image_name, result, confidence)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data.get('user_id'),
            data.get('username'),
            data.get('image_name'),
            data.get('result'),
            data.get('confidence')
        ))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Log saved: {data.get('username')} - {data.get('result')}")
    except Exception as e:
        print(f"Error saving log: {e}")

# Process each message from RabbitMQ
def process_message(ch, method, properties, body):
    try:
        data = json.loads(body)
        print(f"Received message: {data}")
        save_log(data)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag)

# Connect to RabbitMQ and start listening
def start_worker():
    setup_database()

    credentials = pika.PlainCredentials('admin', 'admin1234')
    parameters = pika.ConnectionParameters(
        host='rabbitmq',
        port=5672,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )

    while True:
        try:
            print("Connecting to RabbitMQ...")
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            channel.queue_declare(queue='detection_logs', durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue='detection_logs',
                on_message_callback=process_message
            )

            print("Worker is listening for messages!")
            channel.start_consuming()

        except Exception as e:
            print(f"Connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == '__main__':
    start_worker()