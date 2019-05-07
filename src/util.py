import os


def mysql_connection_string():
    return "mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8mb4".format(
        os.getenv('MYSQL_USER'),
        os.getenv('MYSQL_PASS'),
        os.getenv('MYSQL_HOST'),
        os.getenv('MYSQL_PORT'),
        os.getenv('MYSQL_DB')
    )
