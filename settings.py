import os

DB_CONNECTION = {
        "drivername": "postgresql",
        "kwargs": dict(
            username='instagram',
            password='instagram',
            host='localhost',
            port=5432,
            database='instagram'
            )
        }

REDIS = {
    'host': 'localhost',
    'port': 6379
}

INSTAGRAM_KEY = os.getenv("INSTAGRAM_KEY")
INSTAGRAM_SECRET = os.getenv("INSTAGRAM_SECRET")
INSTAGRAM_REDIRECT = os.getenv("INSTAGRAM_REDIRECT")

