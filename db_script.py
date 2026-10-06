from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client['co2db']
enterprises_collection = db['enterprises']

def insert_document(collection, data):
    return collection.insert_one(data).inserted_id

def find_document(collection, elements, multiple=False):
    if multiple:
        results = collection.find(elements)
        return [r for r in results]
    else:
        return collection.find_one(elements)

def update_document(collection, query_elements, new_values):
    collection.update_one(query_elements, {'$set': new_values})

def delete_document(collection, query):
    collection.delete_one(query)

if __name__ == "__main__":
    enterprises_collection.delete_many({})

    zaporizhstal = {
        "name": "Zaporizhstal",
        "industry": "Metallurgy",
        "co2_emissions_tons": 4500000,
        "city": "Zaporizhzhia"
    }
    motor_sich = {
        "name": "Motor Sich",
        "industry": "Mechanical Engineering",
        "co2_emissions_tons": 120000,
        "city": "Zaporizhzhia"
    }
    dneprospetsstal = {
        "name": "Dneprospetsstal",
        "industry": "Metallurgy",
        "co2_emissions_tons": 950000,
        "city": "Zaporizhzhia"
    }
    zaporozhkoks = {
        "name": "Zaporozhkoks",
        "industry": "Chemical Industry",
        "co2_emissions_tons": 1800000,
        "city": "Zaporizhzhia"
    }
    ztr = {
        "name": "Zaporozhtransformator",
        "industry": "Electrical Engineering",
        "co2_emissions_tons": 45000,
        "city": "Zaporizhzhia"
    }

    zap_id = insert_document(enterprises_collection, zaporizhstal)
    print(f"add {zaporizhstal['name']}: {zap_id}")

    mot_id = insert_document(enterprises_collection, motor_sich)
    print(f"add {motor_sich['name']}: {mot_id}")

    dss_id = insert_document(enterprises_collection, dneprospetsstal)
    print(f"add {dneprospetsstal['name']}: {dss_id}")

    zk_id = insert_document(enterprises_collection, zaporozhkoks)
    print(f"add {zaporozhkoks['name']}: {zk_id}")

    ztr_id = insert_document(enterprises_collection, ztr)
    print(f"add {ztr['name']}: {ztr_id}")

    result = find_document(enterprises_collection, {'name': 'Zaporizhstal'})
    print(f"find result: {result}")

    update_document(enterprises_collection, {'_id': zap_id}, {'co2_emissions_tons': 4200000})
    updated_result = find_document(enterprises_collection, {'_id': zap_id})
    print(f"updated result: {updated_result}")

    delete_document(enterprises_collection, {'_id': mot_id})
    deleted_check = find_document(enterprises_collection, {'_id': mot_id})
    print(f"find result after deletion: {deleted_check}")