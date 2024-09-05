import telebot
import sqlite3

# Replace 'YOUR_API_TOKEN' with your actual API token from BotFather
API_TOKEN = '7520527602:AAGOCYnKx9ZIhpsFMghvjcGpwGboMk7pPeU'
bot = telebot.TeleBot(API_TOKEN)

# Initialize the database
def init_db():
    conn = sqlite3.connect('marketplace.db')
    cursor = conn.cursor()

    # Users table (added rating and is_verified fields)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        chat_id INTEGER UNIQUE,
                        username TEXT,
                        rating REAL DEFAULT 0.0,
                        is_verified BOOLEAN DEFAULT 0
                      )''')

    # Products table (with description and category)
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER,
                        name TEXT,
                        description TEXT,
                        price TEXT,
                        category TEXT,
                        download_link TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                      )''')

    # Orders table (track payment and delivery status)
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY,
                        buyer_id INTEGER,
                        product_id INTEGER,
                        date TEXT,
                        payment_status TEXT DEFAULT 'pending',  -- pending, paid, refunded
                        delivery_status TEXT DEFAULT 'pending',  -- pending, delivered
                        FOREIGN KEY (buyer_id) REFERENCES users (id),
                        FOREIGN KEY (product_id) REFERENCES products (id)
                      )''')

    # Transactions table (to track payment)
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY,
                        buyer_id INTEGER,
                        product_id INTEGER,
                        payment_method TEXT,
                        amount TEXT,
                        date TEXT,
                        FOREIGN KEY (buyer_id) REFERENCES users (id),
                        FOREIGN KEY (product_id) REFERENCES products (id)
                      )''')

    conn.commit()
    conn.close()

# Register or update user in the database
def register_user(chat_id, username):
    conn = sqlite3.connect('marketplace.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (chat_id, username) VALUES (?, ?)", (chat_id, username))
    conn.commit()
    conn.close()

# Add a product to the marketplace
def add_product(user_id, product_name, price, description, category):
    conn = sqlite3.connect('marketplace.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (user_id, name, description, price, category) VALUES (?, ?, ?, ?, ?)", 
                   (user_id, product_name, description, price, category))
    conn.commit()
    conn.close()

# Get products from the marketplace
def get_products():
    conn = sqlite3.connect('marketplace.db')
    cursor = conn.cursor()
    cursor.execute("SELECT p.name, p.price, u.username FROM products p JOIN users u ON p.user_id = u.id")
    products = cursor.fetchall()
    conn.close()
    return products

# Get user ID by chat ID
def get_user_id(chat_id):
    conn = sqlite3.connect('marketplace.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE chat_id = ?", (chat_id,))
    user_id = cursor.fetchone()
    conn.close()
    return user_id[0] if user_id else None

# Delete a user's product
def delete_product(user_id, product_name):
    conn = sqlite3.connect('marketplace.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE user_id = ? AND name = ?", (user_id, product_name))
    conn.commit()
    conn.close()

# Place an order
def place_order(buyer_id, product_id):
    conn = sqlite3.connect('marketplace.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (buyer_id, product_id, date) VALUES (?, ?, datetime('now'))", 
                   (buyer_id, product_id))
    conn.commit()
    conn.close()

# Command: /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    register_user(message.chat.id, message.chat.username)
    welcome_message = (
        "Welcome to Black Chamber! Your one-stop digital marketplace.\n"
        "Here are some commands you can use:\n"
        "- /buy: Browse products\n"
        "- /sell: List your product\n"
        "- /myproducts: View your listed products\n"
        "- /delete: Delete a listed product\n"
        "- /order: Place an order (coming soon)\n"
        "- /profile: View your profile and listed products\n"
        "- /help: Get a list of available commands"
    )
    bot.reply_to(message, welcome_message)

# Command: /help
@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "Here's how you can use the marketplace:\n"
                          "- /buy: Browse products\n"
                          "- /sell: List your product\n"
                          "- /myproducts: View your listed products\n"
                          "- /delete: Delete a listed product\n"
                          "- /order: Place an order (coming soon)\n"
                          "- /profile: View your profile and listed products")

# Command: /sell
@bot.message_handler(commands=['sell'])
def sell_product(message):
    bot.reply_to(message, "Please enter the product name, description, price, and category (e.g., 'E-book, Great read, $10, Books'):")
    bot.register_next_step_handler(message, save_product)

def save_product(message):
    try:
        product_info = message.text.split(',')
        if len(product_info) == 4:
            product_name, description, price, category = [info.strip() for info in product_info]
            user_id = get_user_id(message.chat.id)
            if user_id:
                add_product(user_id, product_name, price, description, category)
                bot.reply_to(message, f"Your product '{product_name}' has been listed at {price.strip()} in {category} category!")
            else:
                bot.reply_to(message, "User not found in the database.")
        else:
            bot.reply_to(message, "Please use the correct format: 'Product name, description, price, category'.")
    except ValueError:
        bot.reply_to(message, "There was an error processing your request.")

# Command: /buy
@bot.message_handler(commands=['buy'])
def browse_products(message):
    products = get_products()
    if products:
        products_list = "\n".join([f"{name} for {price} (Seller: @{username})" for name, price, username in products])
        bot.reply_to(message, "Available products:\n" + products_list)
    else:
        bot.reply_to(message, "No products listed yet.")

# Command: /myproducts
@bot.message_handler(commands=['myproducts'])
def my_products(message):
    user_id = get_user_id(message.chat.id)
    if user_id:
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, price FROM products WHERE user_id = ?", (user_id,))
        products = cursor.fetchall()
        conn.close()

        if products:
            user_products = "\n".join([f"{name} for {price}" for name, price in products])
            bot.reply_to(message, "Your listed products:\n" + user_products)
        else:
            bot.reply_to(message, "You haven't listed any products yet.")
    else:
        bot.reply_to(message, "User not found in the database.")

# Command: /delete
@bot.message_handler(commands=['delete'])
def delete_product_command(message):
    bot.reply_to(message, "Please enter the product name you want to delete:")
    bot.register_next_step_handler(message, remove_product)

def remove_product(message):
    user_id = get_user_id(message.chat.id)
    if user_id:
        product_name = message.text.strip()
        delete_product(user_id, product_name)
        bot.reply_to(message, f"Your product '{product_name}' has been deleted.")
    else:
        bot.reply_to(message, "User not found in the database.")

# Command: /profile
@bot.message_handler(commands=['profile'])
def view_profile(message):
    user_id = get_user_id(message.chat.id)
    if user_id:
        conn = sqlite3.connect('marketplace.db')
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        username = cursor.fetchone()[0]
        cursor.execute("SELECT name, price FROM products WHERE user_id = ?", (user_id,))
        products = cursor.fetchall()
        conn.close()

        user_profile = f"Username: @{username}\n"
        if products:
            user_profile += "Your listed products:\n"
            user_profile += "\n".join([f"{name} for {price}" for name, price in products])
        else:
            user_profile += "You haven't listed any products yet."

        bot.reply_to(message, user_profile)
    else:
        bot.reply_to(message, "User not found in the database.")

# Start the bot
init_db()  # Initialize the database tables
bot.remove_webhook()
bot.polling()  # Start polling for messages
