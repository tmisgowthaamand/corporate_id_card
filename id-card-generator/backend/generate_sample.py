"""Generate sample ID cards directly to test preview."""
import urllib.request
import json

url = 'http://127.0.0.1:5000/generate'
employees = [
    {"employee_id": "EMP-2026-0001", "name": "Rahul Sharma", "designation": "Software Engineer", "department": "IT", "blood_group": "O+", "mobile": "9876543210", "email": "rahul.sharma@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Chennai", "website": "www.acmecorp.com", "photo": "emp1.jpg"},
    {"employee_id": "EMP-2026-0002", "name": "Priya Nair", "designation": "HR Manager", "department": "HR", "blood_group": "A+", "mobile": "9988776655", "email": "priya.nair@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Bengaluru", "website": "www.acmecorp.com", "photo": "emp2.jpg"},
    {"employee_id": "EMP-2026-0003", "name": "Arjun Verma", "designation": "Finance Analyst", "department": "Finance", "blood_group": "B+", "mobile": "9123456780", "email": "arjun.verma@acmecorp.com", "valid_till": "Dec 2027", "company": "Acme Corp International", "address": "Hyderabad", "website": "www.acmecorp.com", "photo": "emp3.jpg"},
]

data = json.dumps({"employees": employees}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
result = json.loads(resp.read().decode())
print(json.dumps(result, indent=2))
