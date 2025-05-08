# app/config.py

DATABASE = {
    "USER": "masterlcr",
    "PASSWORD": "LcRd1804",
    "HOST": "localhost",
    "PORT": 3306,
    "NAME": "ylf_db"
}

DATABASE_URL = (
    f"mysql+pymysql://{DATABASE['USER']}:{DATABASE['PASSWORD']}"
    f"@{DATABASE['HOST']}:{DATABASE['PORT']}/{DATABASE['NAME']}"
)
