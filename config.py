import pymongo

client = pymongo.MongoClient("mongodb+srv://admin:rudenok12345@test.vfmvv.mongodb.net/?retryWrites=true&w=majority&appName=test")

db = client.numo

users = db.users