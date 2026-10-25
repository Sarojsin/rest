from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, hash_token
from app.models.identity import Restaurant, RestaurantMembership, RestaurantSettings, User
from app.models.billing import PaymentMethodConfig
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
        "Momo",
        "Hand-pleated Himalayan dumplings",
        [
            (
                "Steam Momo (10 pcs)",
                "Classic steamed dumplings with tomato-sesame dip",
                25000,
                "🥟",
                "/menu/food/steam-momo.webp",
                "/menu/models/steam-momo.glb",
                "Wheat flour, cabbage, spring onion, garlic, soy sauce. "
                "Contains: gluten, soy, sesame",
            ),
            (
                "Jhol Momo (10 pcs)",
                "Dumplings in a spicy, tangy jhol broth",
                28000,
                "🍜",
                "/menu/food/jhol-momo.jpg",
                "/menu/models/bowl-soup.glb",
                "Wheat flour dumplings, tomato, sesame seeds, cilantro, chili oil. "
                "Contains: gluten, soy, sesame",
            ),
        ],
    ),
    (
        "Chowmein",
        "Wok-tossed noodles",
        [
            (
                "Veg Chowmein",
                "Stir-fried noodles with seasonal vegetables",
                22000,
                "🥬",
                "/menu/food/veg-chowmein.webp",
                "/menu/models/noodles-gl.glb",
                "Wheat noodles, cabbage, carrot, bell pepper, soy sauce. Contains: gluten, soy",
            ),
            (
                "Chicken Chowmein",
                "Stir-fried noodles with chicken and crunchy greens",
                26000,
                "🍜",
                "/menu/food/chicken-chowmein.webp",
                "",
                "Wheat noodles, chicken, egg, spring onion, soy sauce. Contains: gluten, egg, soy",
            ),
        ],
    ),
    (
        "Grills",
        "From the charcoal",
        [
            (
                "Chicken Leg Piece (4 pcs)",
                "Marinated grilled drumsticks with salad and dipping sauce",
                38000,
                "🍗",
                "/menu/food/chicken-leg-piece.jpg",
                "",
                "Chicken drumsticks, yogurt-spice marinade, lettuce salad, mint dip. "
                "Contains: dairy, mustard",
            ),
        ],
    ),
]

# Starter tenders: cash works out of the box; QR methods stay disabled at
# checkout until the owner uploads the merchant QR image.
DEFAULT_PAYMENT_METHODS = [
    ("Cash", "CASH", "", "Collect cash and count the tender before recording.", 0),
    ("eSewa", "QR", "eSewa merchant", "Scan with the eSewa app and pay the exact bill total.", 1),
    ("IME Pay", "QR", "IME Pay merchant", "Scan with the IME Pay app and pay the exact bill total.", 2),
    ("Bank Transfer", "QR", "", "Transfer to our bank account and show the receipt.", 3),
]


def seed_if_empty(db: Session) -> None:
    existing = db.scalar(select(func.count()).select_from(Restaurant))
    if existing:
        return

    restaurant = Restaurant(
        name="Harbor Table",
        slug="harbor-table",
        timezone="Asia/Kathmandu",
        currency_code="NPR",
        status="ACTIVE",
    )
    db.add(restaurant)
    db.flush()
    db.add(
        RestaurantSettings(
            restaurant_id=restaurant.id,
            locale="en-NP",
            tax_rate_bps=1300,
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
        for item_index, item in enumerate(items, start=1):
            if len(item) < 7:
                item = (*item, "", "")  # pad model_path/ingredients_text
            item_name, item_desc, price, emoji, image_path, model_path, ingredients = item
            db.add(
                MenuItem(
                    restaurant_id=restaurant.id,
                    category_id=category.id,
                    name=item_name,
                    description=item_desc,
                    current_price_minor=price,
                    currency_code="NPR",
                    status="PUBLISHED",
                    display_order=item_index,
                    image_emoji=emoji,
                    image_path=image_path,
                    model_path=model_path,
                    ingredients_text=ingredients,
                )
            )

    for label, kind, account_hint, instructions, display_order in DEFAULT_PAYMENT_METHODS:
        db.add(
            PaymentMethodConfig(
                restaurant_id=restaurant.id,
                label=label,
                kind=kind,
                account_hint=account_hint,
                instructions=instructions,
                is_active=True,
                display_order=display_order,
            )
        )
    db.commit()
