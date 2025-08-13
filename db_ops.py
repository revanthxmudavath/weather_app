import json
from db import get_conn

# CREATE
def save_request(location_key, label, start, end, units, data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO weather_requests (location_key, location_label, start_date, end_date, units, data_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (location_key, label, start, end, units, json.dumps(data)))
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return rid

# READ
def list_requests():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, location_label, start_date, end_date, units FROM weather_requests ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_requests(req_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, location_key, location_label, start_date, end_date, units, data_json FROM weather_requests WHERE id = ?", (req_id,))
    row = cur.fetchone()
    conn.close()
    return row

# UPDATE
def update_request(req_id, start, end, new_data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE weather_requests SET start_date = ?, end_date = ?, data_json = ?
        WHERE id = ?
    """, (start, end, json.dumps(new_data), req_id))
    conn.commit()
    conn.close()

# DELETE
def delete_request(req_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM weather_requests WHERE id = ?", (req_id,))
    conn.commit()
    conn.close()