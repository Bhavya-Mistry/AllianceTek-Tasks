import psycopg2

conn = psycopg2.connect(
    host="chess-db-prod.chf9zh1cnhew.us-east-2.rds.amazonaws.com",
    port=5432,
    user="chessadmin",
    password="huazLTkRgr1MHiWBkuLq",
    dbname="postgres",
)

cur = conn.cursor()
cur.execute("SELECT version();")
print(cur.fetchone())

cur.close()
conn.close()
