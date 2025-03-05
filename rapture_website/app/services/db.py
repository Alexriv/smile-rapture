from pymongo import MongoClient

# Replace <username>, <password>, and <cluster-url> with your Atlas credentials
mongo_client = MongoClient("mongodb+srv://pablotest:rapture2025@smilelab-rapture.g4m2g.mongodb.net/")

# Connect to the "user_db" database
db = mongo_client["user_db"]

# Define collections
config_collection = db["config"]
user_collection = db["users"]
experiment_collection = db["experiments"]

# Functions to delete data (for testing purposes)
def delete_all_users():
    """
    Deletes all documents from the 'users' collection.
    """
    user_collection.delete_many({})
    print("All users deleted.")

def delete_all_experiments():
    """
    Deletes all documents from the 'experiments' collection.
    """
    experiment_collection.delete_many({})
    print("All experiments deleted.")

def delete_all_configs():
    """
    Deletes all documents from the 'config' collection.
    """
    config_collection.delete_many({})
    print("All configs deleted.")

# Uncomment for testing purposes only
# delete_all_users()
# delete_all_experiments()
# delete_all_configs()
