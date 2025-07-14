from tinydb import TinyDB, Query
import datetime

from app.utils.cacao_builder import generate_id

db = TinyDB("./db.json")


def get_db(model):
    return TinyDB(f"./{model}.json")


def get_table(model, name):
    database = get_db(model)
    return database.table(name)


def export(
    dependencies, result, time, tokens=None, errors=None, table="main", model=None
):
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    table = get_table(model, table)
    table.insert(
        {
            "id": generate_id(),
            "created_at": created_at,
            "dependencies": dependencies.to_dict(),
            "tokens": tokens,
            "time": time,
            "result": result,
            "errors": errors,
        }
    )


def export_result(result, model):
    table = get_table(model, "results")
    id = "result"
    table.upsert({"id": id} | result, Query().id == id)


def retrieve(dependencies, last_results=None, table="main", model=None):
    table = get_table(model, table)
    results = table.search(Query().dependencies == dependencies.to_dict())
    if last_results:
        return results[-last_results:] if results else None

    return results[0] if results else None


def remove(dependencies, table, model):
    table = get_table(model, table)
    table.remove(Query().dependencies == dependencies.to_dict())
