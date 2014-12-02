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

INSTAGRAM_KEY = "24b4667c7f25489eadf5b21ee0807af9"
INSTAGRAM_SECRET = "253c56d2f3b744feb9d77fdbd6d988a2"
INSTAGRAM_REDIRECT = "http://localhost:5000/instagram/oauth"

