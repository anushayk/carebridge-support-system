import sqlite3
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

NUM_CUSTOMERS = 100
NUM_TICKETS   = 300
DB_PATH       = "data/apple_support.db"

APPLE_PRODUCTS = [
    "iPhone 15 Pro", "iPhone 15", "iPhone 14 Pro Max", "iPhone 14",
    "iPhone 13", "iPhone SE (3rd gen)",
    'MacBook Pro 14" M3', 'MacBook Pro 16" M3', "MacBook Air M2",
    "MacBook Air M1", "Mac mini M2", 'iMac 24" M3',
    'iPad Pro 12.9"', 'iPad Pro 11"', "iPad Air (5th gen)",
    "iPad (10th gen)", "iPad mini (6th gen)",
    "Apple Watch Ultra 2", "Apple Watch Series 9", "Apple Watch SE",
    "AirPods Pro (2nd gen)", "AirPods (3rd gen)", "AirPods Max",
    "Apple TV 4K", "HomePod (2nd gen)", "HomePod mini",
    "Apple Pencil (2nd gen)", "Magic Keyboard", "Magic Mouse",
]

ISSUE_TYPES = [
    "Hardware Defect", "Software Bug", "Battery Issue", "Screen Damage",
    "Refund Request", "AppleCare Claim", "Account Access", "iCloud Storage",
    "App Store Billing", "Trade-In Query", "Repair Status",
    "Shipping & Delivery", "Accessory Compatibility", "Data Recovery",
    "Warranty Inquiry",
]

CHANNELS          = ["Phone", "Chat", "Email", "In-Store", "Apple Support App"]
STATUSES          = ["Open", "In Progress", "Pending Customer", "Resolved", "Escalated", "Closed"]
PRIORITIES        = ["Low", "Medium", "High", "Critical"]
LOYALTY_TIERS     = ["Standard", "Silver", "Gold", "Platinum"]
PREFERRED_DEVICES = ["iPhone", "Mac", "iPad", "Apple Watch", "Multi-device"]

RESOLUTION_TEMPLATES = {
    "Hardware Defect":        "Device inspected at Genius Bar. {action} under warranty.",
    "Software Bug":           "Remote diagnostics performed. {action} resolved the issue.",
    "Battery Issue":          "Battery health checked at {pct}%. {action} recommended.",
    "Screen Damage":          "Screen damage assessed. {action} scheduled.",
    "Refund Request":         "Refund of ${amount} processed to original payment method.",
    "AppleCare Claim":        "AppleCare claim #{claim} filed. Replacement {action}.",
    "Account Access":         "Identity verified. Apple ID access {action}.",
    "iCloud Storage":         "Storage plan reviewed. Customer {action} to {plan} plan.",
    "App Store Billing":      "Charge of ${amount} reviewed. {action} applied.",
    "Trade-In Query":         "Trade-in value of ${amount} quoted for device.",
    "Repair Status":          "Repair #{claim} updated. Device {action}.",
    "Shipping & Delivery":    "Order #{claim} traced. Package {action}.",
    "Accessory Compatibility": "Compatibility confirmed for {action}.",
    "Data Recovery":          "Data recovery {action}. iCloud backup recommended.",
    "Warranty Inquiry":       "Warranty status confirmed. Coverage {action} until {date}.",
}

RESOLUTION_FILLERS = {
    "action": [
        "replaced", "repaired", "restored", "upgraded", "credited",
        "refunded", "expedited", "approved", "restored successfully",
        "dispatched", "renewed",
    ],
    "pct":    [str(x) for x in range(45, 95, 5)],
    "amount": [str(random.randint(5, 1299)) for _ in range(20)],
    "claim":  [str(random.randint(100000, 999999)) for _ in range(20)],
    "plan":   ["50 GB", "200 GB", "2 TB"],
    "date":   [
        (datetime.now() + timedelta(days=random.randint(30, 730))).strftime("%B %d, %Y")
        for _ in range(20)
    ],
}


def random_resolution(issue_type, status):
    if status not in ("Resolved", "Closed"):
        return None
    template = RESOLUTION_TEMPLATES.get(issue_type, "Issue reviewed and {action}.")
    result = template
    for key, values in RESOLUTION_FILLERS.items():
        placeholder = "{" + key + "}"
        if placeholder in result:
            result = result.replace(placeholder, random.choice(values))
    return result


def random_date(start_days_ago, end_days_ago=0):
    delta = random.randint(end_days_ago, start_days_ago)
    return (datetime.now() - timedelta(days=delta)).strftime("%Y-%m-%d %H:%M:%S")


def create_tables(conn):
    conn.executescript("""
        DROP TABLE IF EXISTS support_tickets;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            customer_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name              TEXT    NOT NULL,
            email             TEXT    NOT NULL UNIQUE,
            phone             TEXT,
            city              TEXT,
            country           TEXT,
            apple_id          TEXT    NOT NULL UNIQUE,
            account_since     TEXT,
            preferred_device  TEXT,
            loyalty_tier      TEXT,
            total_purchases   INTEGER,
            applecare_member  INTEGER
        );

        CREATE TABLE support_tickets (
            ticket_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id         INTEGER NOT NULL,
            product             TEXT    NOT NULL,
            issue_type          TEXT    NOT NULL,
            description         TEXT,
            channel             TEXT,
            priority            TEXT,
            status              TEXT,
            created_at          TEXT,
            updated_at          TEXT,
            resolved_at         TEXT,
            resolution_summary  TEXT,
            satisfaction_rating INTEGER,
            agent_name          TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );
    """)
    conn.commit()


def generate_customers(n):
    customers = []
    for _ in range(n):
        name     = fake.name()
        apple_id = f"{name.lower().replace(' ', '.')}{random.randint(1, 99)}@icloud.com"
        customers.append({
            "name":             name,
            "email":            fake.unique.email(),
            "phone":            fake.phone_number(),
            "city":             fake.city(),
            "country":          random.choice(["USA", "Canada", "UK", "Australia", "Germany", "France", "Japan"]),
            "apple_id":         apple_id,
            "account_since":    random_date(3650, 180),
            "preferred_device": random.choice(PREFERRED_DEVICES),
            "loyalty_tier":     random.choices(LOYALTY_TIERS, weights=[50, 25, 15, 10])[0],
            "total_purchases":  random.randint(1, 40),
            "applecare_member": random.choice([0, 0, 1]),
        })
    return customers


def generate_tickets(n, customer_ids):
    tickets = []
    for _ in range(n):
        status     = random.choices(STATUSES, weights=[10, 15, 10, 35, 5, 25])[0]
        issue_type = random.choice(ISSUE_TYPES)
        created    = random_date(730, 1)
        created_dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        updated_dt = created_dt + timedelta(hours=random.randint(1, 72))
        updated    = updated_dt.strftime("%Y-%m-%d %H:%M:%S")

        resolved = None
        if status in ("Resolved", "Closed"):
            resolved_dt = updated_dt + timedelta(hours=random.randint(1, 48))
            resolved    = resolved_dt.strftime("%Y-%m-%d %H:%M:%S")

        satisfaction = None
        if status in ("Resolved", "Closed"):
            satisfaction = random.choices([1, 2, 3, 4, 5], weights=[5, 8, 15, 35, 37])[0]

        product = random.choice(APPLE_PRODUCTS)
        tickets.append({
            "customer_id":         random.choice(customer_ids),
            "product":             product,
            "issue_type":          issue_type,
            "description":         f"Customer reported {issue_type.lower()} with their {product}. {fake.sentence(nb_words=12)}",
            "channel":             random.choice(CHANNELS),
            "priority":            random.choices(PRIORITIES, weights=[30, 40, 20, 10])[0],
            "status":              status,
            "created_at":          created,
            "updated_at":          updated,
            "resolved_at":         resolved,
            "resolution_summary":  random_resolution(issue_type, status),
            "satisfaction_rating": satisfaction,
            "agent_name":          fake.name(),
        })
    return tickets


def main():
    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)

    customers = generate_customers(NUM_CUSTOMERS)
    conn.executemany("""
        INSERT INTO customers
            (name, email, phone, city, country, apple_id, account_since,
             preferred_device, loyalty_tier, total_purchases, applecare_member)
        VALUES
            (:name, :email, :phone, :city, :country, :apple_id, :account_since,
             :preferred_device, :loyalty_tier, :total_purchases, :applecare_member)
    """, customers)
    conn.commit()

    customer_ids = [row[0] for row in conn.execute("SELECT customer_id FROM customers")]

    tickets = generate_tickets(NUM_TICKETS, customer_ids)
    conn.executemany("""
        INSERT INTO support_tickets
            (customer_id, product, issue_type, description, channel, priority,
             status, created_at, updated_at, resolved_at, resolution_summary,
             satisfaction_rating, agent_name)
        VALUES
            (:customer_id, :product, :issue_type, :description, :channel, :priority,
             :status, :created_at, :updated_at, :resolved_at, :resolution_summary,
             :satisfaction_rating, :agent_name)
    """, tickets)
    conn.commit()
    conn.close()

    print(f"Database created at {DB_PATH}")
    print(f"  customers:       {NUM_CUSTOMERS} rows")
    print(f"  support_tickets: {NUM_TICKETS} rows")


if __name__ == "__main__":
    main()
