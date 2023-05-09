"""
Gradio-based web UI to explore the Camel dataset.
"""

import argparse
import random
from functools import partial
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr


def parse_arguments():
    """ Get command line arguments. """

    parser = argparse.ArgumentParser("Dilemma tool")
    parser.add_argument(
        '--data-path', type=str, default=None,
        help='Path to the folder with ZIP datasets containing JSONs')
    parser.add_argument('--share', type=bool, default=False,
                        help='Expose the web UI to Gradio')
    parser.add_argument(
        '--server-name', type=str, default="0.0.0.0",
        help='localhost for local, 0.0.0.0 (default) for public')
    parser.add_argument('--server-port', type=int, default=8080,
                        help='Port ot run the web page on')
    parser.add_argument('--inbrowser', type=bool, default=False,
                        help='Open the web UI in the default browser on lunch')
    parser.add_argument(
        '--concurrency-count', type=int, default=10,
        help='Number if concurrent threads at Gradio websocket queue. ' +
        'Increase to serve more requests but keep an eye on RAM usage.')
    args, unknown = parser.parse_known_args()
    if len(unknown) > 0:
        print("Unknown args: ", unknown)
    return args


import os

import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes

# import google.auth
# from google.auth.transport.requests import Request


def connect_db():
    INSTANCE_CONNECTION_NAME = "camel-lm:me-central1:camel-dilemma"
    print(f"Your instance connection name is: {INSTANCE_CONNECTION_NAME}")
    DB_USER = "dkuser"
    DB_PASS = "camel230509"
    DB_NAME = "dilemma_choices"

    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = \
        "/home/ivul_kaust/camel-lm-57fc849b664b.json"

    # ip_addr = "34.18.39.52"

    # initialize Connector object
    connector = Connector()

    # # function to return the database connection object
    # def getconn():
    #     conn = connector.connect(INSTANCE_CONNECTION_NAME, "pymysql",
    #                              user=DB_USER, password=DB_PASS, db=DB_NAME,
    #                              key="AIzaSyDys_eiXMOxf6aPz3AGqidlNk-oNqK7LTM")
    #     return conn

    # IAM database user parameter (IAM user's email before the "@" sign, mysql truncates usernames)
    # ex. IAM user with email "demo-user@test.com" would have database username "demo-user"
    # IAM_USER = current_user[0].split("@")[0]
    IAM_USER = "ivul.kaust"

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
        conn = connector.connect(
            INSTANCE_CONNECTION_NAME, # <PROJECT-ID>:<REGION>:<INSTANCE-NAME>
            "pymysql",
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
            ip_type=IPTypes.PRIVATE
        )
        return conn

    # create connection pool with 'creator' argument to our connection object function
    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
    )

    # connect to connection pool
    with pool.connect() as db_conn:
        # create ratings table in our sandwiches database
        db_conn.execute(
            sqlalchemy.text(
                "CREATE TABLE IF NOT EXISTS ratings "
                "( id SERIAL NOT NULL, name VARCHAR(255) NOT NULL, "
                "origin VARCHAR(255) NOT NULL, rating FLOAT NOT NULL, "
                "PRIMARY KEY (id));"))

        # commit transaction (SQLAlchemy v2.X.X is commit as you go)
        db_conn.commit()

        # insert data into our ratings table
        insert_stmt = sqlalchemy.text(
            "INSERT INTO ratings (name, origin, rating) VALUES (:name, :origin, :rating)",
        )

        # insert entries into table
        db_conn.execute(
            insert_stmt, parameters={
                "name": "HOTDOG",
                "origin": "Germany",
                "rating": 7.5
            })
        db_conn.execute(
            insert_stmt, parameters={
                "name": "BÀNH MÌ",
                "origin": "Vietnam",
                "rating": 9.1
            })
        db_conn.execute(
            insert_stmt, parameters={
                "name": "CROQUE MADAME",
                "origin": "France",
                "rating": 8.3
            })

        # commit transactions
        db_conn.commit()

        # query and fetch ratings table
        results = db_conn.execute(
            sqlalchemy.text("SELECT * FROM ratings")).fetchall()

        # show results
        for row in results:
            print(row)

    connector.close()

    print("")


def construct_ui(blocks, dataset: Any):
    """ Build Gradio UI and populate with texts from TXTs.

    Args:
        blocks: Gradio blocks
        datasets (TODO): Parsed multi-TXT dataset.

    Returns:
        None
    """

    connect_db()

    def write_db(choice: str, left: str, right: str):
        print(choice, left, right)

    gr.Markdown("## Dilemma app")
    with gr.Row():
        with gr.Column(scale=1):
            left_md = gr.Markdown("LOREM\n" "IPSUM\n")
        with gr.Column(scale=1):
            right_md = gr.Markdown("LOREM 2\n" "IPSUM 2\n")
    with gr.Row():
        left_better_bn = gr.Button("Left is better")
        not_sure_bn = gr.Button("Not sure")
        right_better_bn = gr.Button("Right is better")

    def load_random():
        return (f"txt {random.randint(1, 100)}",
                f"txt {random.randint(1, 100)}")

    def record(choise: str, left: str, right: str):
        assert choise in {'left', 'draw', 'right'}
        write_db(choise, left, right)

    left_better_bn.click(partial(record, 'left'), [left_md, right_md], None) \
        .then(load_random, None, [left_md, right_md])

    not_sure_bn.click(partial(record, 'draw'), [left_md, right_md], None) \
        .then(load_random, None, [left_md, right_md])

    right_better_bn.click(partial(record, 'right'), [left_md, right_md], None) \
        .then(load_random, None, [left_md, right_md])

    blocks.load(load_random, None, [left_md, right_md])


def construct_blocks(data_path: str):
    """ Construct Blocs app but do not launch it.

    Args:
        data_path (str): Path to the ZIP dataset with TXTs inside.

    Returns:
        gr.Blocks: Blocks instance.
    """

    print("Loading the dataset...")
    # dataset = load_dataset(data_path)
    dataset = None
    print("Dataset is loaded")

    print("Getting Dilemma web server online...")

    with gr.Blocks() as blocks:
        construct_ui(blocks, dataset)

    return blocks


def main():
    """ Entry point. """

    args = parse_arguments()

    blocks = construct_blocks(args.data_path)

    blocks.queue(args.concurrency_count) \
          .launch(share=args.share, inbrowser=args.inbrowser,
                  server_name=args.server_name, server_port=args.server_port)

    print("Exiting.")


if __name__ == "__main__":
    main()
