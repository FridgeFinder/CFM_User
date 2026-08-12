"""Username generation utilities."""
import random


class UsernameGenerator:
    """Generate unique, validation-compliant usernames."""

    CHARSET = '0123456789'
    SUFFIX_LENGTH = 4
    MAX_ATTEMPTS = 10

    ADJECTIVES = [
        "Active", "Agile", "Alive", "Ally", "Amber", "Aqua", "Ardent", "Astral", "Azure", "Beaming",
        "Bliss", "Blithe", "Blue", "Bold", "Brave", "Bright", "Brisk", "Calm", "Care", "Caring",
        "Civic", "Clean", "Clever", "Common", "Cool", "Cosmic", "Cozy", "Crimson", "Crisp", "Cute",
        "Daring", "Dark", "Dazzle", "Dear", "Defiant", "Divine", "Dynamic", "Eager", "Earthy", "Eco",
        "Elite", "Epic", "Equal", "Fair", "Fancy", "Fast", "Fierce", "Fine", "Firm", "Flashy",
        "Free", "Fresh", "Glow", "Glowing", "Gold", "Golden", "Grand", "Gray", "Great", "Green",
        "Guiding", "Happy", "Hardy", "Heal", "Healing", "Hearty", "Honest", "Humble", "Impact", "Indigo",
        "Jade", "Jolly", "Just", "Kin", "Kind", "Kinship", "Light", "Linked", "Live", "Lively",
        "Local", "Loyal", "Lucid", "Lucky", "Magic", "Mega", "Mellow", "Mighty", "Modest", "Mutual",
        "Neon", "New", "Nice", "Nimble", "Noble", "Onyx", "Open", "Peer", "Pink", "Plum",
        "Polite", "Primal", "Proud", "Pure", "Purple", "Radical", "Rare", "Ready", "Rebel", "Resilient",
        "Rich", "Rising", "Robust", "Rooted", "Rose", "Rosy", "Ruby", "Rustic", "Sacred", "Shared",
        "Sharp", "Shiny", "Smart", "Smooth", "Social", "Soft", "Solar", "Solid", "Spark", "Spicy",
        "Stellar", "Strong", "Suave", "Sunny", "Super", "Sweet", "Swift", "Tender", "Tidy", "Tough",
        "True", "Trust", "United", "Valiant", "Vibrant", "Vivid", "Warm", "Wild", "Wise", "Zesty"
    ]

    FOOD_NOUNS = [
        "Acai", "Agave", "Almond", "Amaranth", "Anise", "Apple", "Apricot", "Arugula", "Avocado", "Banana",
        "Barley", "Basil", "Bean", "Berry", "BokChoy", "Cabbage", "Cacao", "Camote", "Carrot", "Cashew",
        "Cassava", "Celery", "Chard", "Chayote", "Cherry", "Chili", "Chive", "Chufa", "Cilantro", "Citrus",
        "Clove", "Coconut", "Corn", "Cowpea", "Cumin", "Currant", "Date", "Dill", "Elder", "Endive",
        "Fennel", "Fig", "Flax", "Garlic", "Ginger", "Gourd", "Grains", "Grape", "Guava", "Hazel",
        "Herb", "Honey", "Jack", "Jicama", "Kale", "Kiwi", "Kumquat", "Leek", "Lemon", "Lentil",
        "Lime", "Lucuma", "Lychee", "Mango", "Manoomin", "Maple", "Melon", "Millet", "Mint", "Moki",
        "Moringa", "Mustard", "Nopal", "Nut", "Nutmeg", "Oat", "Oca", "Okra", "Olive", "Onion",
        "Paprika", "Papaya", "Parsley", "Pea", "Peach", "Peanut", "Pear", "Pecan", "Pepper", "Persimon",
        "Pickle", "Pinyon", "Plum", "Quinoa", "Radish", "Raisin", "Rice", "Romaine", "Rye", "Saffron",
        "Sage", "Salad", "Seed", "Sesame", "Shallot", "Sorghum", "Sprout", "Squash", "Sumac", "Tamarind",
        "Taro", "Teosinte", "Thyme", "Tomato", "Truffle", "Tepary", "Turnip", "Ube", "Vanilla", "Walnut",
        "Wheat", "Yam", "Yuca"
    ]

    def __init__(self, repository):
        self.repository = repository

    def _generate_candidate(self, suffix_length: int) -> str:
        """Generate a candidate username using adjective+noun+numeric suffix."""
        adjective = random.choice(self.ADJECTIVES)
        noun = random.choice(self.FOOD_NOUNS)
        suffix = ''.join(random.choice(self.CHARSET) for _ in range(suffix_length))
        return f'{adjective}{noun}-{suffix}'

    def generate_unique_username(self, max_attempts: int = MAX_ATTEMPTS) -> str:
        """Generate an available username or raise RuntimeError if exhausted."""
        for _ in range(max_attempts):
            candidate = self._generate_candidate(self.SUFFIX_LENGTH)
            if self.repository.is_username_available(candidate):
                return candidate

        for _ in range(max_attempts):
            candidate = self._generate_candidate(self.SUFFIX_LENGTH + 2)
            if self.repository.is_username_available(candidate):
                return candidate

        raise RuntimeError('Unable to generate an available username')
