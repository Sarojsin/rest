from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, hash_token
from app.models.identity import Restaurant, RestaurantMembership, RestaurantSettings, User
from app.models.menu import MenuCategory, MenuItem
from app.models.tables import RestaurantTable, TableQrCode

DEMO_QR_TOKENS = {
    "T1": "table-harbor-1-alpha",
    "T2": "table-harbor-2-bravo",
    "T3": "table-harbor-3-charlie",
    "T4": "table-harbor-4-delta",
    "T5": "table-harbor-5-echo",
    "T6": "table-harbor-6-foxtrot",
}

STAFF = [
    ("owner@harbor.example", "HarborOwner!1", "Maya Chen", "owner"),
    ("manager@harbor.example", "HarborManager!1", "Luis Ortega", "manager"),
    ("waiter@harbor.example", "HarborWaiter!1", "Priya Shah", "waiter"),
    ("kitchen@harbor.example", "HarborKitchen!1", "Jonah Blake", "kitchen"),
    ("cashier@harbor.example", "HarborCashier!1", "Elena Rossi", "cashier"),
]

MENU = [
    (
        "Starters",
        "Shareable plates to begin",
        [
            ("Harbor Chowder", "Clam chowder with fennel and rye crumbs", 900, "S"),
            ("Citrus Olives", "Warm olives, orange, rosemary", 600, "O"),
            ("Garden Salad", "Seasonal greens, lemon vinaigrette", 800, "G"),
        ],
    ),
    (
        "Mains",
        "Kitchen classics",
        [
            ("Grilled Sea Bass", "Charred lemon, herb oil, potatoes", 2400, "B"),
            ("Herb Roast Chicken", "Pan jus, market vegetables", 1900, "C"),
            ("Mushroom Risotto", "Arborio rice, parmesan, thyme", 1700, "R"),
            ("Harbor Burger", "Cheddar, pickles, fries", 1600, "H"),
        ],
    ),
    (
        "Drinks",
        "Soft drinks and house pours",
        [
            ("Sparkling Water", "Bottle", 350, "W"),
            ("House Lemonade", "Mint and citrus", 450, "L"),
            ("Espresso", "Double shot", 400, "E"),
        ],
    ),
    (
        "Desserts",
        "Finish the table",
        [
            ("Olive Oil Cake", "Citrus glaze", 800, "K"),
            ("Chocolate Pot", "Sea salt, cream", 850, "P"),
        ],
    ),
]


def seed_if_empty(db: Session) -> None:
    existing = db.scalar(select(func.count()).select_from(Restaurant))
    if existing:
        return

    restaurant = Restaurant(
        name="Harbor Table",
        slug="harbor-table",
        timezone="America/Los_Angeles",
        currency_code="USD",
        status="ACTIVE",
    )
    db.add(restaurant)
    db.flush()
    db.add(
        RestaurantSettings(
            restaurant_id=restaurant.id,
            locale="en-US",
            tax_rate_bps=1000,
            receipt_header="Harbor Table",
            receipt_footer="Thank you for dining with us",
            qr_ordering_enabled=True,
            online_payments_enabled=False,
        )
    )

    for email, password, name, role in STAFF:
        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=name,
            status="ACTIVE",
        )
        db.add(user)
        db.flush()
        db.add(
            RestaurantMembership(
                restaurant_id=restaurant.id,
                user_id=user.id,
                role=role,
                status="ACTIVE",
            )
        )

    for index, code in enumerate(["T1", "T2", "T3", "T4", "T5", "T6"], start=1):
        table = RestaurantTable(
            restaurant_id=restaurant.id,
            table_code=code,
            display_name=f"Table {index}",
            seating_capacity=4 if index < 6 else 6,
            status="ACTIVE",
            sort_order=index,
        )
        db.add(table)
        db.flush()
        raw = DEMO_QR_TOKENS[code]
        db.add(
            TableQrCode(
                restaurant_id=restaurant.id,
                table_id=table.id,
                token_hash=hash_token(raw),
                token_preview=raw,
                status="ACTIVE",
            )
        )

    for cat_index, (name, description, items) in enumerate(MENU, start=1):
        category = MenuCategory(
            restaurant_id=restaurant.id,
            name=name,
            description=description,
            display_order=cat_index,
            status="PUBLISHED",
        )
        db.add(category)
        db.flush()
        for item_index, (item_name, item_desc, price, emoji) in enumerate(items, start=1):
            db.add(
                MenuItem(
                    restaurant_id=restaurant.id,
                    category_id=category.id,
                    name=item_name,
                    description=item_desc,
                    current_price_minor=price,
                    currency_code="USD",
                    status="PUBLISHED",
                    display_order=item_index,
                    image_emoji=emoji,
                )
            )
    db.commit()
