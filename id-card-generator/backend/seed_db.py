"""Seed MongoDB with sample employee data directly."""
import os
from datetime import datetime
from pymongo import MongoClient

# Load .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

MONGO_URI = os.environ.get('MONGO_URI', '')
MONGO_DB = os.environ.get('MONGO_DB', 'id_card_generator')

if not MONGO_URI:
    print('ERROR: No MONGO_URI found in .env')
    exit(1)

print(f'Connecting to MongoDB...')
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
client.admin.command('ping')
print(f'Connected!')

db = client[MONGO_DB]

employees = [
    {"employee_id": "EMP-2026-0001", "name": "Rahul Sharma", "designation": "Software Engineer", "department": "IT", "blood_group": "O+", "mobile": "9876543210", "email": "rahul.sharma@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Chennai", "website": "www.acmecorp.com", "photo": "emp1.jpg"},
    {"employee_id": "EMP-2026-0002", "name": "Priya Nair", "designation": "HR Manager", "department": "HR", "blood_group": "A+", "mobile": "9988776655", "email": "priya.nair@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Bengaluru", "website": "www.acmecorp.com", "photo": "emp2.jpg"},
    {"employee_id": "EMP-2026-0003", "name": "Arjun Verma", "designation": "Finance Analyst", "department": "Finance", "blood_group": "B+", "mobile": "9123456780", "email": "arjun.verma@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Hyderabad", "website": "www.acmecorp.com", "photo": "emp3.jpg"},
    {"employee_id": "EMP-2026-0004", "name": "Sneha Iyer", "designation": "UI UX Designer", "department": "Creative", "blood_group": "AB+", "mobile": "9012345678", "email": "sneha.iyer@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Chennai", "website": "www.acmecorp.com", "photo": "emp4.jpg"},
    {"employee_id": "EMP-2026-0005", "name": "Vikram Patel", "designation": "Operations Executive", "department": "Operations", "blood_group": "O-", "mobile": "9345678901", "email": "vikram.patel@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Pune", "website": "www.acmecorp.com", "photo": "emp5.jpg"},
    {"employee_id": "EMP-2026-0006", "name": "Kavya Reddy", "designation": "Graphic Designer", "department": "Creative", "blood_group": "A-", "mobile": "9456789012", "email": "kavya.reddy@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Bengaluru", "website": "www.acmecorp.com", "photo": "emp6.jpg"},
    {"employee_id": "EMP-2026-0007", "name": "Aditya Singh", "designation": "Senior Developer", "department": "IT", "blood_group": "B-", "mobile": "9567890123", "email": "aditya.singh@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Noida", "website": "www.acmecorp.com", "photo": "emp7.jpg"},
    {"employee_id": "EMP-2026-0008", "name": "Meera Joshi", "designation": "Marketing Lead", "department": "Marketing", "blood_group": "O+", "mobile": "9678901234", "email": "meera.joshi@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Mumbai", "website": "www.acmecorp.com", "photo": "emp8.jpg"},
    {"employee_id": "EMP-2026-0009", "name": "Rohit Menon", "designation": "System Administrator", "department": "IT", "blood_group": "AB-", "mobile": "9789012345", "email": "rohit.menon@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Kochi", "website": "www.acmecorp.com", "photo": "emp9.jpg"},
    {"employee_id": "EMP-2026-0010", "name": "Ananya Das", "designation": "HR Executive", "department": "HR", "blood_group": "A+", "mobile": "9890123456", "email": "ananya.das@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Kolkata", "website": "www.acmecorp.com", "photo": "emp10.jpg"},
    {"employee_id": "EMP-2026-0011", "name": "Karan Malhotra", "designation": "Security Officer", "department": "Security", "blood_group": "O+", "mobile": "9901234567", "email": "karan.malhotra@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Delhi", "website": "www.acmecorp.com", "photo": "emp11.jpg"},
    {"employee_id": "EMP-2026-0012", "name": "Divya Kapoor", "designation": "Finance Executive", "department": "Finance", "blood_group": "B+", "mobile": "9011122233", "email": "divya.kapoor@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Chandigarh", "website": "www.acmecorp.com", "photo": "emp12.jpg"},
    {"employee_id": "EMP-2026-0013", "name": "Suresh Kumar", "designation": "Operations Manager", "department": "Operations", "blood_group": "A+", "mobile": "9122233344", "email": "suresh.kumar@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Chennai", "website": "www.acmecorp.com", "photo": "emp13.jpg"},
    {"employee_id": "EMP-2026-0014", "name": "Pooja Mehta", "designation": "Creative Lead", "department": "Creative", "blood_group": "O-", "mobile": "9233344455", "email": "pooja.mehta@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Ahmedabad", "website": "www.acmecorp.com", "photo": "emp14.jpg"},
    {"employee_id": "EMP-2026-0015", "name": "Naveen Raj", "designation": "Backend Developer", "department": "IT", "blood_group": "B+", "mobile": "9344455566", "email": "naveen.raj@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Madurai", "website": "www.acmecorp.com", "photo": "emp15.jpg"},
    {"employee_id": "EMP-2026-0016", "name": "Ishita Sen", "designation": "Brand Manager", "department": "Marketing", "blood_group": "AB+", "mobile": "9455566677", "email": "ishita.sen@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Kolkata", "website": "www.acmecorp.com", "photo": "emp16.jpg"},
    {"employee_id": "EMP-2026-0017", "name": "Deepak Yadav", "designation": "Admin Officer", "department": "Admin", "blood_group": "A-", "mobile": "9566677788", "email": "deepak.yadav@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Lucknow", "website": "www.acmecorp.com", "photo": "emp17.jpg"},
    {"employee_id": "EMP-2026-0018", "name": "Neha Pillai", "designation": "Software Tester", "department": "IT", "blood_group": "O+", "mobile": "9677788899", "email": "neha.pillai@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Trivandrum", "website": "www.acmecorp.com", "photo": "emp18.jpg"},
    {"employee_id": "EMP-2026-0019", "name": "Harish Gowda", "designation": "Network Engineer", "department": "IT", "blood_group": "B-", "mobile": "9788899900", "email": "harish.gowda@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Mysuru", "website": "www.acmecorp.com", "photo": "emp19.jpg"},
    {"employee_id": "EMP-2026-0020", "name": "Riya Chatterjee", "designation": "Marketing Executive", "department": "Marketing", "blood_group": "A+", "mobile": "9899900011", "email": "riya.chatterjee@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Bengaluru", "website": "www.acmecorp.com", "photo": "emp20.jpg"},
]

collection = db['employees']
count = 0
for emp in employees:
    emp['uploaded_at'] = datetime.utcnow().isoformat()
    collection.update_one(
        {'employee_id': emp['employee_id']},
        {'$set': emp},
        upsert=True
    )
    count += 1
    print(f'  [{count}/{len(employees)}] {emp["employee_id"]} - {emp["name"]}')

print(f'\nDone! Inserted {count} employees into {MONGO_DB}.employees')
print(f'Total documents in collection: {collection.count_documents({})}')
client.close()
