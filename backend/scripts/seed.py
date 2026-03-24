import sys
import os  # noqa: E402 — needed for sys.path before app imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import random
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.constants import DATABASE_URL

# Import Base and all models so metadata is populated
from app.database import Base  # noqa: E402
import app.models  # noqa: F401, E402
from app.models.user import User
from app.models.preferences import (
    ObjectivePreferences,
    SubjectivePreferences,
    NegotiationPreferences,
    NotificationPreferences,
)
from app.models.apartment import NeighborInfo, Apartment
from app.models.match import Match
from app.models.notification import Notification


engine = create_async_engine(DATABASE_URL, echo=False)
session_factory = async_sessionmaker(engine, expire_on_commit=False)

# ---------------------------------------------------------------------------
# Static seed data
# ---------------------------------------------------------------------------

NEIGHBORHOODS = [
    ("SoHo", "Trendy cast-iron architecture, high-end boutiques, and a vibrant arts scene."),
    ("Williamsburg", "Hipster haven with rooftop bars, vintage shops, and stunning Manhattan views."),
    ("Bushwick", "Gritty-cool artist enclave famous for massive street murals and underground music."),
    ("Upper West Side", "Classic brownstones, proximity to Central Park, and a family-friendly vibe."),
    ("Astoria", "Diverse Queens neighborhood with excellent dining, green parks, and affordable rents."),
    ("Harlem", "Rich cultural heritage, soul-food restaurants, jazz clubs, and Renaissance architecture."),
    ("Lower East Side", "Historic immigrant neighborhood turned nightlife hub with dim-sum spots and galleries."),
    ("Park Slope", "Tree-lined streets, Prospect Park access, and a laid-back Brooklyn family atmosphere."),
    ("Midtown", "The beating heart of Manhattan: skyscrapers, corporate offices, and iconic landmarks."),
    ("Crown Heights", "Caribbean-influenced community with gorgeous brownstones and a rising food scene."),
]

USERS = [
    ("Marcus Rivera", "+1 (212) 555-0192"),
    ("Priya Patel", "+1 (718) 555-0347"),
    ("Jordan Kim", "+1 (646) 555-0581"),
    ("Aaliyah Thompson", "+1 (347) 555-0764"),
    ("Connor Walsh", "+1 (929) 555-0913"),
]

# Deterministic objective preferences per user (index matches USERS).
# Each is intentionally broad enough to match many of the 500 apartments.
USER_OBJ_PREFS = [
    # Marcus Rivera — young professional, 1-bed, trendy Manhattan/Brooklyn
    {
        "bedroom_type": "1b",
        "neighborhoods": ["SoHo", "Williamsburg", "Lower East Side"],
        "min_budget": 2400,
        "max_budget": 3800,
        "lease_length_months": 12,
        "laundry": [],
        "parking": [],
        "pets": False,
        "work_lat": 40.7580,
        "work_lon": -73.9855,
        "commute_method": "transit",
        "max_commute_minutes": 30,
    },
    # Priya Patel — budget-conscious, studio, Queens + affordable Brooklyn
    {
        "bedroom_type": "studio",
        "neighborhoods": ["Astoria", "Bushwick", "Crown Heights"],
        "min_budget": 1800,
        "max_budget": 2600,
        "lease_length_months": 12,
        "laundry": [],
        "parking": [],
        "pets": False,
        "work_lat": 40.7484,
        "work_lon": -73.9967,
        "commute_method": "transit",
        "max_commute_minutes": 45,
    },
    # Jordan Kim — family, 2-bed, upper Manhattan + Brooklyn
    {
        "bedroom_type": "2b",
        "neighborhoods": ["Upper West Side", "Park Slope", "Astoria"],
        "min_budget": 3200,
        "max_budget": 4800,
        "lease_length_months": 12,
        "laundry": [],
        "parking": [],
        "pets": True,
        "work_lat": 40.7282,
        "work_lon": -74.0776,
        "commute_method": "bike",
        "max_commute_minutes": 30,
    },
    # Aaliyah Thompson — mid-range, 1-bed, Harlem + Brooklyn
    {
        "bedroom_type": "1b",
        "neighborhoods": ["Harlem", "Crown Heights", "Bushwick", "Park Slope"],
        "min_budget": 2200,
        "max_budget": 3400,
        "lease_length_months": 12,
        "laundry": [],
        "parking": [],
        "pets": True,
        "work_lat": 40.7614,
        "work_lon": -73.9776,
        "commute_method": "transit",
        "max_commute_minutes": 45,
    },
    # Connor Walsh — high-budget, 3-bed, prime Manhattan
    {
        "bedroom_type": "3b",
        "neighborhoods": ["Midtown", "Upper West Side", "SoHo"],
        "min_budget": 4200,
        "max_budget": 6500,
        "lease_length_months": 12,
        "laundry": [],
        "parking": [],
        "pets": False,
        "work_lat": 40.7549,
        "work_lon": -73.9840,
        "commute_method": "drive",
        "max_commute_minutes": 20,
    },
]

# Deterministic subjective preferences per user (index matches USERS).
USER_SUBJ_PREFS = [
    # Marcus Rivera
    {
        "priority_focus": "features",
        "image_labels": ["modern", "bright", "open-kitchen"],
        "neighborhood_labels": ["trendy", "walkable", "artsy"],
    },
    # Priya Patel
    {
        "priority_focus": "price",
        "image_labels": ["cozy", "natural-light", "renovated"],
        "neighborhood_labels": ["diverse", "vibrant", "community-oriented"],
    },
    # Jordan Kim
    {
        "priority_focus": "location",
        "image_labels": ["spacious", "hardwood-floors", "natural-light"],
        "neighborhood_labels": ["family-friendly", "quiet", "safe"],
    },
    # Aaliyah Thompson
    {
        "priority_focus": "features",
        "image_labels": ["exposed-brick", "hardwood-floors", "cozy"],
        "neighborhood_labels": ["artsy", "cultural", "historic"],
    },
    # Connor Walsh
    {
        "priority_focus": "price",
        "image_labels": ["luxury", "city-views", "high-ceilings"],
        "neighborhood_labels": ["upscale", "well-connected", "safe"],
    },
]

IMAGE_LABELS_POOL = [
    "bright", "modern", "open-kitchen", "hardwood-floors", "high-ceilings",
    "cozy", "minimalist", "industrial", "renovated", "natural-light",
    "spacious", "city-views", "exposed-brick", "loft-style", "luxury",
]

# Apartment image keyword pools for loremflickr.com.
# Each entry targets a distinct room/style so apartments get varied photo sets.
APARTMENT_IMAGE_KEYWORDS = [
    "apartment,interior,modern",
    "living,room,sofa,cozy",
    "kitchen,modern,clean,bright",
    "bedroom,minimal,white",
    "bathroom,modern,tiles",
    "studio,loft,urban,nyc",
    "dining,room,contemporary",
    "home,interior,design",
    "open,kitchen,apartment",
    "hardwood,floors,bright,room",
]

NOTIFICATION_MESSAGES = [
    ("match", "New match found: {apt} in {hood} is a 94% match for your preferences."),
    ("price_drop", "Price drop alert: {apt} in {hood} dropped from ${old} to ${new}/mo."),
    ("negotiation", "Your agent completed a negotiation for {apt}. New offer: ${price}/mo."),
    ("match", "3 new apartments matching your criteria appeared in {hood} today."),
    ("price_drop", "Weekend deal: {apt} in {hood} is now ${new}/mo — act fast!"),
    ("negotiation", "Counter-offer received for {apt}. Review and respond before Friday."),
    ("match", "Based on your preferences, you may love this new listing in {hood}."),
    ("price_drop", "{apt} in {hood} has been reduced by $200/mo. View details now."),
]

# Price ranges by bedroom type (min, max)
PRICE_RANGES = {
    "studio": (1800, 2800),
    "1b": (2400, 3800),
    "2b": (3200, 5000),
    "3b": (4200, 6000),
    "4plus": (5000, 6500),
}

BEDROOM_TYPES = list(PRICE_RANGES.keys())

# Approximate NYC coordinates per neighborhood (lat, lon)
NEIGHBORHOOD_COORDS = {
    "SoHo": (40.7233, -74.0030),
    "Williamsburg": (40.7081, -73.9571),
    "Bushwick": (40.6942, -73.9213),
    "Upper West Side": (40.7870, -73.9754),
    "Astoria": (40.7721, -73.9302),
    "Harlem": (40.8116, -73.9465),
    "Lower East Side": (40.7157, -73.9863),
    "Park Slope": (40.6681, -73.9800),
    "Midtown": (40.7549, -73.9840),
    "Crown Heights": (40.6694, -73.9445),
}

NEGOTIATION_STYLES = ["polite", "professional", "assertive", "friendly"]
COMMUTE_METHODS = ["drive", "transit", "bike"]
LAUNDRY_OPTIONS = [["in_unit"], ["on_site"], ["in_unit", "on_site"], []]
PARKING_OPTIONS = [["garage"], ["street"], ["garage", "street"], []]


def rand_id() -> str:
    return str(uuid.uuid4())


def rand_date_future(days_min: int = 15, days_max: int = 120) -> date:
    return date.today() + timedelta(days=random.randint(days_min, days_max))


def rand_subset(pool: list, min_n: int = 1, max_n: int = 4) -> list:
    k = random.randint(min_n, max_n)
    return random.sample(pool, min(k, len(pool)))


async def seed(db: AsyncSession) -> None:
    # Drop and recreate all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Tables reset.")

    # --- Neighborhoods ---
    neighborhood_objs: list[NeighborInfo] = []
    for name, desc in NEIGHBORHOODS:
        obj = NeighborInfo(id=rand_id(), name=name, description=desc)
        db.add(obj)
        neighborhood_objs.append(obj)
    await db.commit()
    print(f"Inserted {len(neighborhood_objs)} neighborhoods.")

    # Build a lookup by name for use in preference seeding below.
    neighborhood_by_name = {n.name: n for n in neighborhood_objs}

    # --- Users ---
    user_objs: list[User] = []
    for name, phone in USERS:
        obj = User(id=rand_id(), name=name, phone=phone, created_at=datetime.utcnow())
        db.add(obj)
        user_objs.append(obj)
    await db.commit()
    print(f"Inserted {len(user_objs)} users.")

    # --- Apartments (500: 50 per neighborhood × 10 neighborhoods) ---
    # image_labels left empty so Agent 1 can analyze them.
    apartment_objs: list[Apartment] = []
    apt_count = 0
    per_neighborhood = 50
    for neighbor in neighborhood_objs:
        lat_base, lon_base = NEIGHBORHOOD_COORDS[neighbor.name]
        for i in range(per_neighborhood):
            bedroom = random.choice(BEDROOM_TYPES)
            price_min, price_max = PRICE_RANGES[bedroom]
            # Round price to nearest 50
            price = round(random.randint(price_min, price_max) / 50) * 50
            apt_id = rand_id()
            num_images = random.randint(3, 5)
            images = [
                f"https://loremflickr.com/800/600/{random.choice(APARTMENT_IMAGE_KEYWORDS)}?lock={apt_count * 10 + j}"
                for j in range(num_images)
            ]
            apt = Apartment(
                id=apt_id,
                name=f"{neighbor.name} {bedroom.upper()} #{random.randint(1, 99)}{chr(random.randint(65, 70))}",
                bedroom_type=bedroom,
                latitude=round(lat_base + random.uniform(-0.015, 0.015), 6),
                longitude=round(lon_base + random.uniform(-0.015, 0.015), 6),
                price=price,
                neighbor_id=neighbor.id,
                move_in_date=rand_date_future(7, 120),
                lease_length_months=random.choice([6, 12, 18, 24]),
                laundry=random.choice(LAUNDRY_OPTIONS),
                parking=random.choice(PARKING_OPTIONS),
                pets=random.choice([True, False]),
                host_phone=f"+1 (212) 555-{random.randint(1000, 9999)}",
                host_email=f"host{apt_count + 1}@rentolistings.nyc",
                images=images,
                image_labels=[],  # left empty for Agent 1 to fill
                created_at=datetime.utcnow(),
            )
            db.add(apt)
            apartment_objs.append(apt)
            apt_count += 1
    await db.commit()
    print(f"Inserted {len(apartment_objs)} apartments.")

    # --- Objective Preferences (one per user, deterministic so matches are guaranteed) ---
    for user, prefs in zip(user_objs, USER_OBJ_PREFS):
        selected_ids = [
            neighborhood_by_name[name].id
            for name in prefs["neighborhoods"]
            if name in neighborhood_by_name
        ]
        obj = ObjectivePreferences(
            id=rand_id(),
            user_id=user.id,
            bedroom_type=prefs["bedroom_type"],
            selected_areas=selected_ids,
            min_budget=prefs["min_budget"],
            max_budget=prefs["max_budget"],
            move_in_date=rand_date_future(90, 180),
            move_out_date=None,
            lease_length_months=prefs["lease_length_months"],
            laundry=prefs["laundry"],
            parking=prefs["parking"],
            pets=prefs["pets"],
            work_latitude=prefs["work_lat"],
            work_longitude=prefs["work_lon"],
            commute_method=prefs["commute_method"],
            max_commute_minutes=prefs["max_commute_minutes"],
        )
        db.add(obj)
    await db.commit()
    print(f"Inserted {len(user_objs)} objective preference records.")

    # --- Subjective Preferences (one per user, deterministic) ---
    for user, prefs in zip(user_objs, USER_SUBJ_PREFS):
        obj = SubjectivePreferences(
            id=rand_id(),
            user_id=user.id,
            priority_focus=prefs["priority_focus"],
            image_labels=prefs["image_labels"],
            neighborhood_labels=prefs["neighborhood_labels"],
        )
        db.add(obj)
    await db.commit()
    print(f"Inserted {len(user_objs)} subjective preference records.")

    # --- Negotiation Preferences (one per user) ---
    negotiable_pool = [
        "rent_price", "move_in_date", "lease_length", "deposit",
        "parking_fee", "pet_fee", "utilities", "application_fee",
    ]
    goals_pool = ["save_money", "stay_flexible", "live_better", "fit_lifestyle", "hassle_free"]
    for user in user_objs:
        obj = NegotiationPreferences(
            id=rand_id(),
            user_id=user.id,
            enable_automation=True,  # enabled for all users so Agent 3 can be tested
            negotiable_items=rand_subset(negotiable_pool, 2, 4),
            goals=rand_subset(goals_pool, 1, 3),
            max_rent=random.randint(3000, 6000),
            max_deposit=random.randint(3000, 8000),
            latest_move_in_date=rand_date_future(30, 90),
            min_lease_months=random.choice([6, 12]),
            max_lease_months=random.choice([18, 24]),
            negotiation_style=random.choice(NEGOTIATION_STYLES),
        )
        db.add(obj)
    await db.commit()
    print(f"Inserted {len(user_objs)} negotiation preference records.")

    # --- Notification Preferences (one per user) ---
    notif_types_pool = ["match", "price_drop", "negotiation"]
    for user in user_objs:
        obj = NotificationPreferences(
            id=rand_id(),
            user_id=user.id,
            enable_notifications=True,
            auto_scheduling=random.choice([True, False]),
            notification_types=rand_subset(notif_types_pool, 2, 4),
            frequency=random.choice(["realtime", "daily", "weekly"]),
        )
        db.add(obj)
    await db.commit()
    print(f"Inserted {len(user_objs)} notification preference records.")

    # --- Matches (100, no duplicate user-apartment pairs) ---
    match_pairs: set[tuple[str, str]] = set()
    match_objs: list[Match] = []
    attempts = 0
    while len(match_objs) < 100 and attempts < 2000:
        attempts += 1
        user = random.choice(user_objs)
        apt = random.choice(apartment_objs)
        pair = (user.id, apt.id)
        if pair in match_pairs:
            continue
        match_pairs.add(pair)
        score = round(random.uniform(0.55, 0.99), 2)
        match = Match(
            id=rand_id(),
            user_id=user.id,
            apartment_id=apt.id,
            status=random.choice(["not_started", "in_progress", "completed"]),
            commute_minutes=random.randint(10, 60),
            match_score=score,
            match_reasoning=(
                f"This apartment scores {score:.0%} based on budget fit, "
                f"location preference, and style compatibility."
            ),
            created_at=datetime.utcnow(),
        )
        db.add(match)
        match_objs.append(match)
    await db.commit()
    print(f"Inserted {len(match_objs)} matches.")

    # --- Notifications (20) ---
    apt_name_map = {a.id: a.name for a in apartment_objs}
    hood_map = {n.id: n.name for n in neighborhood_objs}
    apt_neighbor_map = {a.id: a.neighbor_id for a in apartment_objs}
    for i in range(20):
        user = random.choice(user_objs)
        apt = random.choice(apartment_objs)
        apt_name = apt_name_map[apt.id]
        hood = hood_map.get(apt_neighbor_map.get(apt.id, ""), "NYC")
        notif_type, template = random.choice(NOTIFICATION_MESSAGES)
        old_price = apt.price + random.randint(100, 400)
        new_price = apt.price
        content = template.format(
            apt=apt_name,
            hood=hood,
            old=old_price,
            new=new_price,
            price=new_price,
            date=(date.today() + timedelta(days=random.randint(3, 14))).strftime("%B %d"),
        )
        notif = Notification(
            id=rand_id(),
            user_id=user.id,
            timestamp=datetime.utcnow(),
            content=content,
            type=notif_type,
            read=random.choice([True, False]),
        )
        db.add(notif)
    await db.commit()
    print("Inserted 20 notifications.")

    print("\nSeed complete.")
    print(f"  Users:         {len(user_objs)}")
    print(f"  Neighborhoods: {len(neighborhood_objs)}")
    print(f"  Apartments:    {len(apartment_objs)}")
    print(f"  Obj. prefs:    {len(user_objs)}")
    print(f"  Subj. prefs:   {len(user_objs)}")
    print(f"  Neg. prefs:    {len(user_objs)}")
    print(f"  Notif. prefs:  {len(user_objs)}")
    print(f"  Matches:       {len(match_objs)}")
    print(f"  Notifications: 20")


async def main() -> None:
    async with session_factory() as db:
        await seed(db)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
