from enum import Enum


class BedroomType(str, Enum):
    studio = "studio"
    one_bed = "1b"
    two_bed = "2b"
    three_bed = "3b"
    four_plus = "4plus"


class LaundryType(str, Enum):
    in_unit = "in_unit"
    on_site = "on_site"


class ParkingType(str, Enum):
    garage = "garage"
    street = "street"


class CommuteMethod(str, Enum):
    drive = "drive"
    transit = "transit"
    bike = "bike"


class PriorityFocus(str, Enum):
    features = "features"
    location = "location"
    price = "price"


class NegotiationStyle(str, Enum):
    polite = "polite"
    professional = "professional"
    assertive = "assertive"
    friendly = "friendly"


class NegotiableItem(str, Enum):
    rent_price = "rent_price"
    move_in_date = "move_in_date"
    lease_length = "lease_length"
    deposit = "deposit"
    parking_fee = "parking_fee"
    pet_fee = "pet_fee"
    utilities = "utilities"
    furnishing = "furnishing"
    application_fee = "application_fee"
    promotions = "promotions"


class NegotiationGoal(str, Enum):
    save_money = "save_money"
    stay_flexible = "stay_flexible"
    live_better = "live_better"
    fit_lifestyle = "fit_lifestyle"
    hassle_free = "hassle_free"


class NotificationType(str, Enum):
    match = "match"
    price_drop = "price_drop"
    negotiation = "negotiation"


class NotificationFrequency(str, Enum):
    realtime = "realtime"
    daily = "daily"
    weekly = "weekly"


class MatchStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"


class MessageType(str, Enum):
    agent = "agent"
    host = "host"
