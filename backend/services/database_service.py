import sqlite3
import json
from backend.database.connection import get_connection
def get_dataset_byid(dataset_id):
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM datasets
            WHERE dataset_id = ?;
        """, (dataset_id,))

        result = cursor.fetchone()

        return result

    finally:
        cursor.close()
        sqliteConnection.close()

def get_all_datasets():
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM datasets;
        """)

        result = cursor.fetchall()
        
        cursor.close()

        return result

    except sqlite3.Error as error:
        print("Error occurred -", error)

    finally:
        if sqliteConnection:
            sqliteConnection.close()
            print("SQLite Connection closed")

# print(get_dataset_byid(1),type(get_dataset_byid(1)))

def get_user_byid(user_id):
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM users
            WHERE user_id = ?;
        """, (user_id,))

        result = cursor.fetchone()
        
        cursor.close()

        return result

    finally:
        if sqliteConnection:
            sqliteConnection.close()
            print("SQLite Connection closed")




def get_all_users():
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:

        cursor.execute("""
            SELECT *
            FROM users;
        """)

        result = cursor.fetchall()
        
        cursor.close()

        return result

    finally:
        if sqliteConnection:
            sqliteConnection.close()
            print("SQLite Connection closed")



def get_experiment_byid(experiment_id):
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM experiments
            WHERE experiment_id = ?;
        """, (experiment_id,))

        result = cursor.fetchone()
        cursor.close()

        return result

    finally:
        if sqliteConnection:
            sqliteConnection.close()


def get_all_experiments():
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM experiments;
        """)

        result = cursor.fetchall()
        cursor.close()

        return result

    finally:
        if sqliteConnection:
            sqliteConnection.close()

def get_model_byid(model_id):
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM models
            WHERE model_id = ?;
        """, (model_id,))

        result = cursor.fetchone()
        cursor.close()

        return result

    finally:
        if sqliteConnection:
            sqliteConnection.close()




def get_all_models():
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM models;
        """)

        result = cursor.fetchall()
        cursor.close()

        return result

    finally:
        if sqliteConnection:
            sqliteConnection.close()

      
           
def add_user(name, email, phone):
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (name, email, phone)
            VALUES (?, ?, ?);
        """, (name, email, phone))

        new_user_id = cursor.lastrowid
        sqliteConnection.commit()

        return new_user_id

    finally:
        cursor.close()
        sqliteConnection.close()


def add_dataset(name, rows, cols, added_by):
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute("""
            INSERT INTO datasets (name, rows, cols, added_by)
            VALUES (?, ?, ?, ?);
        """, (name, rows, cols, added_by))

        new_dataset_id = cursor.lastrowid
        sqliteConnection.commit()

        return new_dataset_id

    finally:
        cursor.close()
        sqliteConnection.close()

def add_experiment(algorithm, split, parameters, results, dataset_id, user_id,target,features):
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute("""
            INSERT INTO experiments (
                algorithm,
                split,
                parameters,
                results,
                dataset_id,
                user_id,
                target,
                features
            )
            VALUES (?, ?, ?, ?, ?, ?,?,?);
        """, (
            algorithm,
            split,
            json.dumps(parameters),
            json.dumps(results),
            dataset_id,
            user_id,
            target,
            json.dumps(features)

        ))

        new_experiment_id = cursor.lastrowid
        sqliteConnection.commit()

        return new_experiment_id

    finally:
        cursor.close()
        sqliteConnection.close()

def add_model(artifact_path, experiment_id):  
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute("""
            INSERT INTO models (
                artifact_path,
                experiment_id
            )
            VALUES (?, ?);
        """, (
            artifact_path,
            experiment_id))

        new_model_id = cursor.lastrowid
        sqliteConnection.commit()

        return new_model_id

    finally:
        cursor.close()
        sqliteConnection.close()




def update_user_db(user_id, changes):
    set_parts = []

    for field in changes:
        set_parts.append(f"{field} = ?")

    set_clause = ", ".join(set_parts)

    values = list(changes.values())
    values.append(user_id)
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute(f"""
            UPDATE  users
            SET {set_clause} ,updated_at = CURRENT_TIMESTAMP
            WHERE user_id=?;
        """,values)
        updated_rows = cursor.rowcount

        sqliteConnection.commit()

        return updated_rows
    finally:
        cursor.close()
        sqliteConnection.close()


def update_dataset_db(dataset_id, changes):
    set_parts = []

    for field in changes:
        set_parts.append(f"{field} = ?")

    set_clause = ", ".join(set_parts)

    values = list(changes.values())
    values.append(dataset_id)

    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()
    try:
        cursor.execute(
            f"""
            UPDATE datasets
            SET {set_clause}
            WHERE dataset_id = ?;
            """,
            values
        )

        updated_rows = cursor.rowcount
        sqliteConnection.commit()

        return updated_rows

    finally:
        cursor.close()
        sqliteConnection.close()





def delete_user_db(user_id):
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute(f"""
            DELETE  FROM users
            WHERE user_id=?
        """,(user_id,))
        deleted_rows = cursor.rowcount
        sqliteConnection.commit()

        return deleted_rows
    finally:
        cursor.close()
        sqliteConnection.close()

def delete_dataset_db(dataset_id):
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()

    try:
        cursor.execute("""
            DELETE FROM datasets
            WHERE dataset_id = ?;
        """, (dataset_id,))

        deleted_rows = cursor.rowcount
        sqliteConnection.commit()

        return deleted_rows

    finally:
        cursor.close()
        sqliteConnection.close()


def delete_experiment_db(experiment_id):
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()
    try:
        cursor.execute("""
            DELETE FROM experiments
            WHERE experiment_id = ?;
        """, (experiment_id,))

        deleted_rows = cursor.rowcount
        sqliteConnection.commit()

        return deleted_rows
    finally:
        cursor.close()
        sqliteConnection.close()


def delete_modle_db(model_id):
    sqliteConnection = get_connection()
    cursor = sqliteConnection.cursor()
    try:
        cursor.execute("""
            DELETE FROM models
            WHERE model_id = ?;
        """, (model_id,))

        deleted_rows = cursor.rowcount
        sqliteConnection.commit()

        return deleted_rows
    finally:
        cursor.close()
        sqliteConnection.close()