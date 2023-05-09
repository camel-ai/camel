import os

import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes

# import google.auth
# from google.auth.transport.requests import Request


class DatabaseConnection:
    def __init__(self):

        INSTANCE_CONNECTION_NAME = "camel-lm:me-central1:camel-dilemma"
        print(f"Your instance connection name is: {INSTANCE_CONNECTION_NAME}")
        DB_USER = "dkuser"
        DB_PASS = "camel230509"
        DB_NAME = "dilemma_choices"

        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = \
            "/home/ivul_kaust/camel-lm-57fc849b664b.json"

        # ip_addr = "34.18.39.52"

        # initialize Connector object
        self.connector = Connector()

        # # function to return the database connection object
        # def getconn():
        #     conn = connector.connect(INSTANCE_CONNECTION_NAME, "pymysql",
        #                              user=DB_USER, password=DB_PASS, db=DB_NAME)
        #     return conn

        # IAM database user parameter (IAM user's email before the "@" sign, mysql truncates usernames)
        # ex. IAM user with email "demo-user@test.com" would have database username "demo-user"
        # IAM_USER = current_user[0].split("@")[0]
        # IAM_USER = "ivul.kaust"
        # getconn now using IAM user and requiring no password with IAM Auth enabled
        #def getconn():
        #    conn = connector.connect(
        #        INSTANCE_CONNECTION_NAME,
        #        "pymysql",
        #        user=IAM_USER,
        #        db="",  # log in to instance but don't connect to specific database
        #        enable_iam_auth=True)
        #    return conn

        # getconn now set to private IP
        def getconn():
            conn = self.connector.connect(INSTANCE_CONNECTION_NAME, "pymysql",
                                          user=DB_USER, password=DB_PASS,
                                          db=DB_NAME, ip_type=IPTypes.PRIVATE)
            return conn

        # create connection pool with 'creator' argument to our connection object function
        self.pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=getconn,
        )

        # connect to connection pool
        # with self.pool.connect() as db_conn:
        # # create ratings table in our sandwiches database
        # db_conn.execute(
        #     sqlalchemy.text(
        #         "CREATE TABLE IF NOT EXISTS ratings "
        #         "( id SERIAL NOT NULL, name VARCHAR(255) NOT NULL, "
        #         "origin VARCHAR(255) NOT NULL, rating FLOAT NOT NULL, "
        #         "PRIMARY KEY (id));"))
        # # commit transaction (SQLAlchemy v2.X.X is commit as you go)
        # db_conn.commit()

        # # insert data into our ratings table
        # insert_stmt = sqlalchemy.text(
        #     "INSERT INTO ratings (name, origin, rating) VALUES (:name, :origin, :rating)",
        # )

        # # insert entries into table
        # db_conn.execute(
        #     insert_stmt, parameters={
        #         "name": "HOTDOG",
        #         "origin": "Germany",
        #         "rating": 7.5
        #     })
        # db_conn.execute(
        #     insert_stmt, parameters={
        #         "name": "BÀNH MÌ",
        #         "origin": "Vietnam",
        #         "rating": 9.1
        #     })
        # db_conn.execute(
        #     insert_stmt, parameters={
        #         "name": "CROQUE MADAME",
        #         "origin": "France",
        #         "rating": 8.3
        #     })

        # # commit transactions
        # db_conn.commit()

        # # query and fetch ratings table
        # results = db_conn.execute(
        #     sqlalchemy.text("SELECT * FROM ratings")).fetchall()

        # # show results
        # for row in results:
        #     print(row)

    def __del__(self):
        self.connector.close()

    def add_record(self, choice: str, left: str, right: str):
        with self.pool.connect() as db_conn:
            insert_stmt = sqlalchemy.text(
                "INSERT INTO choices (left_option, right_option, choice, date)"
                " VALUES (:opt_left, :opt_right, :choice, NOW())")
            db_conn.execute(
                insert_stmt, parameters={
                    "opt_left": left,
                    "opt_right": right,
                    "choice": choice,
                })
            db_conn.commit()
