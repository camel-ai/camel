from camel.storages.vectordb_storages import VectorDBQuery, VectorRecord
from camel.storages.vectordb_storages.pgvector import PgVectorStorage, PgVectorDistance
import psycopg2

def init_database():
    # 连接到默认的 postgres 数据库来创建新数据库
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="postgres",
        user="postgres",
        password="postgres"
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        cur.execute("DROP DATABASE IF EXISTS vectordb")
        cur.execute("CREATE DATABASE vectordb")
    except psycopg2.Error as e:
        print(f"Database creation error: {e}")
    finally:
        cur.close()
        conn.close()

    # 连接到新创建的数据库并启用扩展
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="vectordb",
        user="postgres",
        password="postgres"
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.close()
    conn.close()

# 初始化数据库
init_database()

# 测试向量
test_records = [
    VectorRecord(
        vector=[1.0, 0.0, 0.0],
        id="vec1",
        payload={"description": "unit vector along x"}
    ),
    VectorRecord(
        vector=[0.0, 1.0, 0.0],
        id="vec2",
        payload={"description": "unit vector along y"}
    ),
    VectorRecord(
        vector=[0.0, 0.0, 1.0],
        id="vec3",
        payload={"description": "unit vector along z"}
    ),
    VectorRecord(
        vector=[1.0, 1.0, 1.0],
        id="vec4",
        payload={"description": "diagonal vector"}
    ),
]

# 测试不同的距离度量
distances = [
    (PgVectorDistance.L2, "L2距离"),
    (PgVectorDistance.INNER_PRODUCT, "内积"),
    (PgVectorDistance.COSINE, "余弦距离"),
    (PgVectorDistance.L1, "L1距离")
]

for distance, name in distances:
    # 初始化存储实例
    storage = PgVectorStorage(
        vector_dim=3,
        connection_params={
            "host": "localhost",
            "port": 5432,
            "database": "vectordb",
            "user": "postgres",
            "password": "postgres"
        },
        table_name=f"test_vectors_{distance}",
        distance=distance
    )

    # 添加向量
    storage.add(test_records)

    # 执行查询
    query_vector = [1.0, 0.0, 0.0]
    results = storage.query(
        VectorDBQuery(
            query_vector=query_vector,
            top_k=2
        )
    )

    print(f"\n{name} 查询结果:")
    for result in results:
        print(f"ID: {result.record.id}")
        print(f"相似度: {result.similarity}")

    # 清理数据
    storage.clear()