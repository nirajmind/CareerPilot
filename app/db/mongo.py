from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)

db = client["careerpilot"]
mock_interview_collection = db["mock_interview_evaluations"]
user_collection = db["users"]
user_collection.create_index("email", unique=True)
resume_collection = db["resumes"]
jd_collection = db["job_descriptions"]
analysis_collection = db["analysis_results"]