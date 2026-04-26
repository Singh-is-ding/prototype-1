import re
import sys
import subprocess
import time
import os
import glob
from datetime import datetime


def extract_project_id(cdn_input):
    match = re.search(r'projectId["\s]*:["\s]*["\']([^"\']+)["\']', cdn_input)
    if match:
        return match.group(1).strip()
    match = re.search(r'projectId["\s]*:["\s]*([a-zA-Z0-9_-]+)', cdn_input)
    if match:
        return match.group(1).strip()
    return None


def get_project_short_name(project_id):
    return project_id.split("-")[0].lower()


def find_gcloud():
    possible_paths = [
        r"C:\Users\{}\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd".format(os.environ.get("USERNAME", "")),
        r"C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        r"C:\google-cloud-sdk\bin\gcloud.cmd",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    try:
        result = subprocess.run(["where", "gcloud"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except Exception:
        pass

    try:
        result = subprocess.run(["where", "gcloud.cmd"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except Exception:
        pass

    home = os.path.expanduser("~")
    pattern = os.path.join(home, "**", "gcloud.cmd")
    matches = glob.glob(pattern, recursive=True)
    if matches:
        return matches[0]

    return None


def run_gcloud(gcloud_path, args, capture=True):
    cmd = f'"{gcloud_path}" {args}'
    return subprocess.run(cmd, shell=True, capture_output=capture, text=True)


def check_gcloud_login(gcloud_path):
    result = run_gcloud(gcloud_path, "auth list --filter=status:ACTIVE --format=value(account)")
    return bool(result.stdout.strip())


def install_firebase_admin():
    print("\n📦 Installing firebase-admin... please wait.")
    subprocess.run([sys.executable, "-m", "pip", "install", "firebase-admin"], check=True)
    print("✅ firebase-admin installed!\n")


def print_banner():
    print("\n" + "=" * 55)
    print("   🏋️  GYM FIREBASE FIRESTORE AUTO-SETUP 🏋️")
    print("=" * 55)
    print("  This script will:")
    print("  • Connect to your Firebase project")
    print("  • Create your Firestore database")
    print("  • Seed all gym collections with sample data")
    print("=" * 55 + "\n")


def find_service_account_key(project_id):
    home = os.path.expanduser("~")
    short_name = get_project_short_name(project_id)

    search_dirs = [
        os.path.join(home, "Downloads"),
        os.path.join(home, "Desktop"),
        home,
    ]

    exact_matches = []
    general_matches = []

    for directory in search_dirs:
        if os.path.exists(directory):
            json_files = glob.glob(os.path.join(directory, "*.json"))
            for f in json_files:
                filename = os.path.basename(f).lower()
                is_firebase = any(keyword in filename for keyword in [
                    "firebase", "adminsdk", "service", "serviceaccount",
                    "private", "key", "credential"
                ])
                if not is_firebase:
                    continue
                if short_name in filename or project_id.lower() in filename:
                    exact_matches.append(f)
                else:
                    general_matches.append(f)

    return exact_matches, general_matches


def get_service_account_path(project_id):
    print("📋 STEP 2: Service Account Key")
    print("-" * 40)

    short_name = get_project_short_name(project_id)
    exact_matches, general_matches = find_service_account_key(project_id)

    if exact_matches:
        print(f"🎯 Found key file(s) matching your project '{short_name}':\n")
        all_shown = exact_matches + general_matches
        for i, path in enumerate(exact_matches, 1):
            print(f"   [{i}] ✅ {os.path.basename(path)}")
            print(f"        📂 {os.path.dirname(path)}")

        if general_matches:
            print(f"\n   Other Firebase key files found:")
            offset = len(exact_matches)
            for i, path in enumerate(general_matches, offset + 1):
                print(f"   [{i}] ⚪ {os.path.basename(path)}")
                print(f"        📂 {os.path.dirname(path)}")

        print(f"\n   [M] Manually enter path\n")

        while True:
            choice = input("👉 Pick a number or press M to enter manually: ").strip().upper()
            if choice == "M":
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(all_shown):
                selected = all_shown[int(choice) - 1]
                print(f"\n✅ Using: {os.path.basename(selected)}\n")
                return selected
            else:
                print("   ❌ Invalid choice. Try again.")

    elif general_matches:
        print(f"🔍 No exact match for '{short_name}' found. Other Firebase key files:\n")
        all_shown = general_matches
        for i, path in enumerate(general_matches, 1):
            print(f"   [{i}] {os.path.basename(path)}")
            print(f"        📂 {os.path.dirname(path)}")
        print(f"\n   [M] Manually enter path\n")

        while True:
            choice = input("👉 Pick a number or press M to enter manually: ").strip().upper()
            if choice == "M":
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(all_shown):
                selected = all_shown[int(choice) - 1]
                print(f"\n✅ Using: {os.path.basename(selected)}\n")
                return selected
            else:
                print("   ❌ Invalid choice. Try again.")

    else:
        print("⚠️  No Firebase key file found automatically.\n")
        print("👉 Go to Firebase Console → Project Settings → Service Accounts")
        print("   Click 'Generate new private key' → download the JSON file.\n")

    print("📁 Paste the full path to your key file OR just the folder:")
    print(r"   Example folder : C:\Users\rpsrawat\Downloads")
    print(r"   Example file   : C:\Users\rpsrawat\Downloads\gimbo-e5920-adminsdk.json" + "\n")
    user_input = input("📂 Path: ").strip().strip('"').strip("'")
    print()

    if os.path.isfile(user_input) and user_input.endswith(".json"):
        print(f"✅ Using: {os.path.basename(user_input)}\n")
        return user_input

    if os.path.isdir(user_input):
        json_files = glob.glob(os.path.join(user_input, "*.json"))
        firebase_files = [
            f for f in json_files
            if any(kw in os.path.basename(f).lower() for kw in [
                "firebase", "adminsdk", "service", "key", "credential",
                short_name, project_id.lower()
            ])
        ]

        if not firebase_files:
            firebase_files = json_files

        if len(firebase_files) == 1:
            print(f"✅ Auto-detected key file: {os.path.basename(firebase_files[0])}\n")
            return firebase_files[0]

        elif len(firebase_files) > 1:
            print(f"🔍 Multiple JSON files found. Pick the correct one:\n")
            for i, f in enumerate(firebase_files, 1):
                print(f"   [{i}] {os.path.basename(f)}")
            print()
            while True:
                choice = input("👉 Enter number: ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(firebase_files):
                    selected = firebase_files[int(choice) - 1]
                    print(f"\n✅ Using: {os.path.basename(selected)}\n")
                    return selected
                print("   ❌ Invalid. Try again.")
        else:
            print("❌ No JSON files found in that folder.")
            sys.exit(1)

    print("❌ Path not valid.")
    sys.exit(1)


def seed_attendance(db):
    records = [
        {
            "checkIn": "04:17",
            "date": "2026-04-17",
            "name": "Adarsh",
            "powerId": "O01",
            "shift": "morning",
            "status": "present",
            "time": "12:13",
            "timestamp": datetime(2026, 4, 17, 12, 13, 49)
        },
        {
            "checkIn": "06:00",
            "date": "2026-04-18",
            "name": "Ravi Kumar",
            "powerId": "O02",
            "shift": "morning",
            "status": "present",
            "time": "08:30",
            "timestamp": datetime(2026, 4, 18, 8, 30, 0)
        },
        {
            "checkIn": "",
            "date": "2026-04-18",
            "name": "Sneha Patel",
            "powerId": "O03",
            "shift": "evening",
            "status": "absent",
            "time": "",
            "timestamp": datetime(2026, 4, 18, 15, 0, 0)
        }
    ]
    for record in records:
        db.collection("attendance").add(record)
        print(f"    ✔ {record['name']} | {record['date']} | {record['status']}")


def seed_equipment(db):
    items = [
        {
            "condition": "GOOD",
            "name": "Treadmill",
            "notes": "Serviced regularly. Reliable cardio machine.",
            "purchaseDate": datetime(2025, 6, 18, 2, 10, 28),
            "quantity": 2,
            "type": "Cardio"
        },
        {
            "condition": "GOOD",
            "name": "Dumbbells Set",
            "notes": "Rubber coated hex dumbbells 5kg to 50kg.",
            "purchaseDate": datetime(2024, 1, 10, 10, 0, 0),
            "quantity": 5,
            "type": "Free Weights"
        },
        {
            "condition": "FAIR",
            "name": "Lat Pulldown Machine",
            "notes": "Cable needs inspection next month.",
            "purchaseDate": datetime(2023, 8, 5, 9, 0, 0),
            "quantity": 1,
            "type": "Strength"
        }
    ]
    for item in items:
        db.collection("equipment").add(item)
        print(f"    ✔ {item['name']} | {item['type']} | qty: {item['quantity']}")


def seed_fees(db):
    records = [
        {
            "amount": 1200,
            "name": "Amit Rajput",
            "paymentDate": "2026-04-13",
            "powerId": "O42",
            "status": "paid"
        },
        {
            "amount": 999,
            "name": "Sneha Patel",
            "paymentDate": "2026-04-01",
            "powerId": "O03",
            "status": "paid"
        },
        {
            "amount": 1500,
            "name": "Ravi Kumar",
            "paymentDate": "2026-03-20",
            "powerId": "O02",
            "status": "unpaid"
        }
    ]
    for record in records:
        db.collection("fees").add(record)
        print(f"    ✔ {record['name']} | ₹{record['amount']} | {record['status']}")


def seed_gym_settings(db):
    config = {
        "address": "Dehradun",
        "createdAt": datetime(2026, 4, 24, 13, 25, 35),
        "eveningClose": "09:30",
        "eveningCloseAmpm": "PM",
        "eveningOpen": "03:00",
        "eveningOpenAmpm": "PM",
        "gymName": "MUTANTS",
        "gymTiming": {
            "eveningClose": "21:30",
            "eveningOpen": "15:00",
            "morningClose": "13:00",
            "morningOpen": "04:00"
        },
        "morningClose": "01:00",
        "morningCloseAmpm": "PM",
        "morningOpen": "04:00",
        "morningOpenAmpm": "AM",
        "phone": "9999999999"
    }
    db.collection("gym_settings").document("config").set(config)
    print(f"    ✔ gymName: {config['gymName']} | address: {config['address']}")


def seed_members(db):
    members = [
        {
            "email": "ishamukherjee@gmail.com",
            "fitnessGoal": "Fitness",
            "joinDate": "2026-03-16",
            "membershipDays": 365,
            "name": "Isha Mukherjee",
            "package": "1 Year",
            "phone": "9074316370",
            "powerId": "O29",
            "status": "active"
        },
        {
            "email": "amit.rajput@gmail.com",
            "fitnessGoal": "Weight Loss",
            "joinDate": "2026-01-10",
            "membershipDays": 180,
            "name": "Amit Rajput",
            "package": "6 Months",
            "phone": "9876543210",
            "powerId": "O42",
            "status": "active"
        },
        {
            "email": "ravi.kumar@gmail.com",
            "fitnessGoal": "Muscle Gain",
            "joinDate": "2025-12-01",
            "membershipDays": 30,
            "name": "Ravi Kumar",
            "package": "1 Month",
            "phone": "9123456780",
            "powerId": "O02",
            "status": "inactive"
        }
    ]
    for member in members:
        db.collection("members").add(member)
        print(f"    ✔ {member['name']} | {member['powerId']} | {member['package']}")


def seed_staff(db):
    staff_list = [
        {
            "email": "trainerrahul@gym.com",
            "joinDate": datetime(2026, 4, 22, 12, 24, 51),
            "name": "Trainer Rahul",
            "paymentStatus": "PAID",
            "phone": "8888888888",
            "role": "Trainer",
            "salary": 15000,
            "status": "active"
        },
        {
            "email": "priya.sharma@gym.com",
            "joinDate": datetime(2025, 8, 1, 10, 0, 0),
            "name": "Priya Sharma",
            "paymentStatus": "PAID",
            "phone": "9123456789",
            "role": "Manager",
            "salary": 25000,
            "status": "active"
        },
        {
            "email": "suresh.nair@gym.com",
            "joinDate": datetime(2025, 6, 15, 9, 0, 0),
            "name": "Suresh Nair",
            "paymentStatus": "UNPAID",
            "phone": "9765432100",
            "role": "Receptionist",
            "salary": 12000,
            "status": "active"
        }
    ]
    for staff in staff_list:
        db.collection("staff").add(staff)
        print(f"    ✔ {staff['name']} | {staff['role']} | ₹{staff['salary']}")


def seed_supplement_sales(db):
    sales = [
        {
            "date": "2026-04-19",
            "quantity": 4,
            "supplement": "Creatine",
            "totalAmount": 1200,
            "unitPrice": 300
        },
        {
            "date": "2026-04-20",
            "quantity": 2,
            "supplement": "Whey Protein",
            "totalAmount": 5000,
            "unitPrice": 2500
        },
        {
            "date": "2026-04-21",
            "quantity": 3,
            "supplement": "BCAA",
            "totalAmount": 2100,
            "unitPrice": 700
        }
    ]
    for sale in sales:
        db.collection("supplement_sales").add(sale)
        print(f"    ✔ {sale['supplement']} | qty: {sale['quantity']} | ₹{sale['totalAmount']}")


def seed_supplements(db):
    supplements = [
        {
            "brand": "ON",
            "name": "Whey Protein",
            "price": 2500,
            "stock": 10
        },
        {
            "brand": "MuscleBlaze",
            "name": "Creatine",
            "price": 300,
            "stock": 25
        },
        {
            "brand": "MyProtein",
            "name": "BCAA",
            "price": 700,
            "stock": 15
        }
    ]
    for supp in supplements:
        db.collection("supplements").add(supp)
        print(f"    ✔ {supp['name']} | {supp['brand']} | ₹{supp['price']} | stock: {supp['stock']}")


def main():
    print_banner()

    print("📋 STEP 1: Firebase CDN Config")
    print("-" * 40)
    print("👉 Go to Firebase Console → Project Settings → Your Apps")
    print("   Copy your firebaseConfig object and paste it below.")
    print("   Press Enter twice when done:\n")

    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    cdn_input = "\n".join(lines)

    project_id = extract_project_id(cdn_input)
    if not project_id:
        print("\n❌ ERROR: Could not find projectId in the config you pasted.")
        sys.exit(1)

    short_name = get_project_short_name(project_id)
    print(f"\n✅ Found your project : {project_id}")
    print(f"🔑 Matching key files : '{short_name}'\n")

    service_account_path = get_service_account_path(project_id)

    if not os.path.exists(service_account_path):
        print(f"❌ File not found: {service_account_path}")
        sys.exit(1)
    print(f"✅ Key file confirmed : {os.path.basename(service_account_path)}\n")

    print("🔧 Setting up gcloud & Firestore...")
    print("-" * 40)

    print("🔍 Searching for gcloud on your system...")
    gcloud_path = find_gcloud()

    if not gcloud_path:
        print("❌ gcloud CLI not found on your system.")
        print("   Install it from: https://cloud.google.com/sdk/docs/install")
        print("   After installing, restart your terminal and run this script again.")
        sys.exit(1)

    print(f"✅ gcloud found at  : {gcloud_path}")

    if not check_gcloud_login(gcloud_path):
        print("🔐 Not logged into gcloud. Opening browser for login...")
        subprocess.run(f'"{gcloud_path}" auth login', shell=True)
        if not check_gcloud_login(gcloud_path):
            print("❌ Login failed. Please try again.")
            sys.exit(1)
    print("✅ gcloud authenticated.")

    print(f"🔗 Setting project to: {project_id}")
    result = run_gcloud(gcloud_path, f"config set project {project_id}")
    if result.returncode != 0:
        print(f"❌ Failed to set project.\n{result.stderr}")
        sys.exit(1)
    print("✅ Project set.")

    print("⚙️  Enabling Firestore API...")
    result = run_gcloud(gcloud_path, "services enable firestore.googleapis.com")
    if result.returncode != 0:
        print(f"❌ Failed to enable Firestore API.\n{result.stderr}")
        sys.exit(1)
    print("✅ Firestore API enabled.")

    print("🗄️  Creating Firestore database in asia-south1...")
    result = run_gcloud(gcloud_path, "firestore databases create --location=asia-south1")
    if result.returncode != 0:
        if "already exists" in result.stderr.lower() or "already exists" in result.stdout.lower():
            print("ℹ️  Firestore database already exists. Skipping.")
        else:
            print(f"❌ Failed to create database.\n{result.stderr}")
            sys.exit(1)
    else:
        print("✅ Firestore database created.")

    print("\n⏳ Waiting 25 seconds for Firestore to fully initialize...")
    for i in range(25, 0, -5):
        print(f"   ⏱  {i} seconds remaining...")
        time.sleep(5)
    print("✅ Firestore is ready!\n")

    print("🔌 Connecting Firebase Admin SDK...")
    print("-" * 40)

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        install_firebase_admin()
        import firebase_admin
        from firebase_admin import credentials, firestore

    try:
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Connected to Firestore!\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        sys.exit(1)

    print("🌱 Seeding collections with sample data...")
    print("-" * 40)

    print("\n📁 attendance")
    seed_attendance(db)

    print("\n📁 equipment")
    seed_equipment(db)

    print("\n📁 fees")
    seed_fees(db)

    print("\n📁 gym_settings")
    seed_gym_settings(db)

    print("\n📁 members")
    seed_members(db)

    print("\n📁 staff")
    seed_staff(db)

    print("\n📁 supplement_sales")
    seed_supplement_sales(db)

    print("\n📁 supplements")
    seed_supplements(db)

    print("\n" + "=" * 55)
    print("   🎉 ALL DONE! Your Firestore is ready to use.")
    print("=" * 55)
    print(f"  Project   : {project_id}")
    print("  Region    : asia-south1")
    print("  Collections seeded:")
    print("    ✔ attendance        ✔ equipment")
    print("    ✔ fees              ✔ gym_settings")
    print("    ✔ members           ✔ staff")
    print("    ✔ supplement_sales  ✔ supplements")
    print("=" * 55)
    print("\n  👉 Open Firebase Console to see your data:")
    print(f"  https://console.firebase.google.com/project/{project_id}/firestore\n")


if __name__ == "__main__":
    main()
