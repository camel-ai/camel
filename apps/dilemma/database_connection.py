import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes

# import os
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = \
#     "/path/to/camel-lm-XXXXXXXXX.json"


class DatabaseConnection:
    def __init__(self):

        INSTANCE_CONNECTION_NAME = "camel-lm:me-central1:camel-dilemma"
        print(f"Instance connection name is: {INSTANCE_CONNECTION_NAME}")
        DB_USER = "dkuser"
        DB_PASS = "camel230509"
        DB_NAME = "dilemma_choices"

        self.connector = Connector()

        def getconn():
            conn = self.connector.connect(INSTANCE_CONNECTION_NAME, "pymysql",
                                          user=DB_USER, password=DB_PASS,
                                          db=DB_NAME, ip_type=IPTypes.PRIVATE)
            return conn

        self.pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=getconn,
        )

    def __del__(self):
        self.connector.close()

    def add_record(self, file_name: str, who_is_better: str):
        with self.pool.connect() as db_conn:
            insert_stmt = sqlalchemy.text(
                "INSERT INTO choices2 (file_name, who_is_better, date)"
                " VALUES (:file_name, :who_is_better, NOW())")
            db_conn.execute(
                insert_stmt, parameters={
                    "file_name": file_name,
                    "who_is_better": who_is_better,
                })
            db_conn.commit()
