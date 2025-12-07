import requests
import json
import sys

BASE_URL = "http://localhost:8000"
EMAIL = "phase3test_v2@example.com"
PASSWORD = "securepassword123"

def run_test():
    print("🚀 Starting Phase 3 Test Sequence...\n")

    # 1. Register (Try to register, but ignore if already exists)
    print("1️⃣  Registering User...")
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": EMAIL, 
        "password": PASSWORD, 
        "full_name": "Phase 3 Tester"
    })
    
    if reg_res.status_code in [200, 201]:
        print("   ✅ User registered (or returned)")
    elif reg_res.status_code == 400 and "registered" in reg_res.text:
        print("   ℹ️  User already exists (proceeding to login)")
    else:
        print(f"   ⚠️  Registration response: {reg_res.status_code}")

    # 2. Login
    print("\n2️⃣  Logging In...")
    login_res = requests.post(f"{BASE_URL}/auth/login", data={
        "username": EMAIL, 
        "password": PASSWORD
    })
    
    if login_res.status_code != 200:
        print(f"   ❌ Login failed: {login_res.status_code}")
        print(f"   Response: {login_res.text}")
        sys.exit(1)

    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"   ✅ Logged in! Token obtained.")

    # 3. Create Meal Plan
    print("\n3️⃣  Creating Test Meal Plan...")
    
    # UPDATED: Using correct endpoint /meal-plans/generate
    # Payload structure based on MealPlanCreate schema
    plan_payload = {
        "week_start_date": "2025-12-01",
        "preferences_override": {
            "dietary_restrictions": [],
            "calorie_target": 2000,
            "budget": 150
        }
    }
    
    # Correct endpoint: /meal-plans/generate
    plan_res = requests.post(f"{BASE_URL}/meal-plans/generate", headers=headers, json=plan_payload)
    
    if plan_res.status_code in [200, 201]:
        plan_id = plan_res.json()["id"]
        print(f"   ✅ Meal Plan Created! ID: {plan_id}")
    else:
        print(f"   ⚠️  Creating new plan failed ({plan_res.status_code}), checking for existing...")
        # Fallback: Check if we have any existing plans
        get_plans = requests.get(f"{BASE_URL}/meal-plans/", headers=headers)
        if get_plans.status_code == 200 and len(get_plans.json()) > 0:
            plan_id = get_plans.json()[0]["id"]
            print(f"   ✅ Found existing plan ID: {plan_id}")
        else:
            print(f"   ❌ Could not create or find a meal plan. Response: {plan_res.text}")
            sys.exit(1)

    # 4. Generate Shopping List
    print("\n4️⃣  Generating Shopping List (The Big Test!)...")
    list_res = requests.post(f"{BASE_URL}/shopping-lists/generate", headers=headers, json={
        "plan_id": plan_id,
        "name": "Phase 3 Automated Test List",
        "include_pantry_check": False
    })

    if list_res.status_code in [200, 201]:
        data = list_res.json()
        print(f"   ✅ SUCCESS! Shopping List Generated:")
        print(f"      🆔 List ID: {data['id']}")
        print(f"      🛒 Total Items: {data.get('total_items', len(data.get('items', [])))}")
        print(f"      💰 Est. Cost: ${data.get('total_estimated_cost', 0)}")
        
        if 'items' in data and data['items']:
            print("\n   Sample Items:")
            for item in data['items'][:3]:
                print(f"      - {item['quantity']} {item['unit']} {item['ingredient_name']} ({item['category']})")
    else:
        print(f"   ❌ Shopping List Generation Failed: {list_res.status_code} {list_res.text}")

if __name__ == "__main__":
    run_test()
