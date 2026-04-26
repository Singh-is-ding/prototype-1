import sys
import os
import glob
import subprocess
import json


# =============================================================
#   🔐 GYM FIREBASE AUTH USER CREATOR
#   Auto-enables Email/Password sign-in + creates accounts
#   Roles: owner / member / zumba
# =============================================================


def install_package(name):
    print(f"\n📦 Installing {name}... please wait.")
    subprocess.run([sys.executable, "-m", "pip", "install", name], check=True)
    print(f"✅ {name} installed!\n")


def find_gcloud():
    possible_paths = [
        r"C:\Users\{}\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd".format(
            os.environ.get("USERNAME", "")),
        r"C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        r"C:\google-cloud-sdk\bin\gcloud.cmd",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    for cmd in ["gcloud", "gcloud.cmd"]:
        try:
            result = subprocess.run(["where", cmd], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().splitlines()[0]
        except Exception:
            pass
    matches = glob.glob(os.path.join(os.path.expanduser("~"), "**", "gcloud.cmd"), recursive=True)
    return matches[0] if matches else None


def get_access_token(gcloud_path):
    result = subprocess.run(
        f'"{gcloud_path}" auth print-access-token',
        shell=True, capture_output=True, text=True
    )
    return result.stdout.strip() or None


def enable_email_password_auth(project_id, access_token):
    try:
        import requests
    except ImportError:
        install_package("requests")
        import requests

    url = (
        f"https://identitytoolkit.googleapis.com/admin/v2/projects/"
        f"{project_id}/config?updateMask=signIn.email.enabled,signIn.email.passwordRequired"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "signIn": {
            "email": {
                "enabled": True,
                "passwordRequired": True
            }
        }
    }
    response = requests.patch(url, headers=headers, json=body)
    return response.status_code == 200, response.text


def find_service_account_key():
    home = os.path.expanduser("~")
    matches = []
    for directory in [os.path.join(home, "Downloads"), os.path.join(home, "Desktop"), home]:
        if os.path.exists(directory):
            for f in glob.glob(os.path.join(directory, "*.json")):
                if any(kw in os.path.basename(f).lower() for kw in [
                    "firebase", "adminsdk", "service", "serviceaccount", "private", "key", "credential"
                ]):
                    matches.append(f)
    return matches


def get_project_id_from_key(key_path):
    try:
        with open(key_path, "r") as f:
            return json.load(f).get("project_id")
    except Exception:
        return None


def get_service_account_path():
    print("📋 STEP 1: Service Account Key")
    print("-" * 40)

    matches = find_service_account_key()

    if matches:
        print("🎯 Firebase key file(s) found:\n")
        for i, path in enumerate(matches, 1):
            print(f"   [{i}] {os.path.basename(path)}")
            print(f"        📂 {os.path.dirname(path)}")
        print(f"\n   [M] Manually enter path\n")

        while True:
            choice = input("👉 Pick a number or press M to enter manually: ").strip().upper()
            if choice == "M":
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(matches):
                selected = matches[int(choice) - 1]
                print(f"\n✅ Using: {os.path.basename(selected)}\n")
                return selected
            else:
                print("   ❌ Invalid choice. Try again.")
    else:
        print("⚠️  No Firebase key file found automatically.\n")
        print("👉 Go to Firebase Console → Project Settings → Service Accounts")
        print("   Click 'Generate new private key' → download the JSON file.\n")

    print("📁 Paste the full path to your key file OR just the folder:")
    print(r"   Example: C:\Users\rpsrawat\Downloads\gimbo-e5920-adminsdk.json" + "\n")
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
                "firebase", "adminsdk", "service", "key", "credential"
            ])
        ] or json_files

        if len(firebase_files) == 1:
            print(f"✅ Auto-detected: {os.path.basename(firebase_files[0])}\n")
            return firebase_files[0]
        elif len(firebase_files) > 1:
            print("🔍 Multiple JSON files found:\n")
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


def create_auth_users(fb_auth):
    print("\n👥 STEP 3: Create Firebase Auth Users")
    print("-" * 40)
    print("  Roles available: owner, member, zumba")
    print("  Email pattern  : owner1@gmail.com, member2@gmail.com ...")
    print("  Password       : same as email prefix  (e.g. owner1, member2)")
    print("  Press Enter (blank) to skip a role.\n")

    roles = ["owner", "member", "zumba"]
    created = skipped = failed = 0

    for role in roles:
        raw = input(f"  How many {role} accounts to create? (e.g. 3): ").strip()
        if not raw.isdigit() or int(raw) == 0:
            print(f"   ⚪ Skipping {role}\n")
            continue

        count = int(raw)
        print()
        for i in range(1, count + 1):
            email    = f"{role}{i}@gmail.com"
            password = f"{role}{i}"
            try:
                fb_auth.create_user(email=email, password=password)
                print(f"   ✔ Created  : {email:<32}  password: {password}")
                created += 1
            except Exception as e:
                err = str(e)
                if "EMAIL_EXISTS" in err or "already exists" in err.lower():
                    print(f"   ⚠ Exists   : {email}")
                    skipped += 1
                else:
                    print(f"   ❌ Failed   : {email} — {e}")
                    failed += 1
        print()

    print("=" * 55)
    print(f"  ✔ Created         : {created}")
    print(f"  ⚪ Already existed : {skipped}")
    print(f"  ❌ Failed          : {failed}")
    print("=" * 55)


def main():
    print("\n" + "=" * 55)
    print("   🔐  GYM FIREBASE AUTH USER CREATOR 🔐")
    print("=" * 55)
    print("  Auto-enables Email/Password sign-in")
    print("  then creates owner / member / zumba accounts.")
    print("=" * 55 + "\n")

    # ── STEP 1: Key file ─────────────────────────────────────
    service_account_path = get_service_account_path()
    if not os.path.exists(service_account_path):
        print(f"❌ File not found: {service_account_path}")
        sys.exit(1)

    project_id = get_project_id_from_key(service_account_path)
    if not project_id:
        print("❌ Could not read project_id from key file.")
        sys.exit(1)
    print(f"🔑 Project ID : {project_id}\n")

    # ── STEP 2: Auto-enable Email/Password Auth ───────────────
    print("⚙️  STEP 2: Enable Email/Password Authentication")
    print("-" * 40)
    print("🔍 Looking for gcloud on your system...")

    gcloud_path = find_gcloud()
    if not gcloud_path:
        print("⚠️  gcloud not found — cannot auto-enable.")
        print("   Manually go to: Firebase Console → Authentication → Sign-in method → Email/Password → Enable\n")
    else:
        print("✅ gcloud found.")

        # Ensure logged in
        result = subprocess.run(
            f'"{gcloud_path}" auth list --filter=status:ACTIVE --format=value(account)',
            shell=True, capture_output=True, text=True
        )
        if not result.stdout.strip():
            print("🔐 Not logged in to gcloud. Opening browser...")
            subprocess.run(f'"{gcloud_path}" auth login', shell=True)

        # Set project
        subprocess.run(
            f'"{gcloud_path}" config set project {project_id}',
            shell=True, capture_output=True, text=True
        )

        # Enable Identity Toolkit API
        print("⚙️  Enabling Identity Toolkit API...")
        r = subprocess.run(
            f'"{gcloud_path}" services enable identitytoolkit.googleapis.com',
            shell=True, capture_output=True, text=True
        )
        if r.returncode == 0:
            print("✅ Identity Toolkit API enabled.")
        else:
            print("⚠️  Could not enable API (may already be enabled).")

        # Get access token and enable Email/Password
        print("🔑 Getting access token...")
        token = get_access_token(gcloud_path)
        if not token:
            print("⚠️  Could not get access token. Skipping auto-enable.")
            print("   Manually enable Email/Password in Firebase Console.\n")
        else:
            print("🔧 Enabling Email/Password sign-in provider...")
            ok, response_text = enable_email_password_auth(project_id, token)
            if ok:
                print("✅ Email/Password Authentication ENABLED!\n")
            else:
                # 400 with CONFIGURATION_NOT_FOUND means Auth hasn't been initialized yet
                # In that case we need to initialize it first via Firebase Management API
                if "CONFIGURATION_NOT_FOUND" in response_text or "404" in response_text:
                    print("🔧 Auth not initialized yet. Initializing Firebase Authentication...")
                    try:
                        import requests
                    except ImportError:
                        install_package("requests")
                        import requests

                    # Initialize Firebase Auth for the project
                    init_url = f"https://identitytoolkit.googleapis.com/admin/v2/projects/{project_id}/config"
                    init_headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    }
                    # First GET to initialize, then PATCH
                    requests.get(init_url, headers=init_headers)

                    # Enable Firebase Management API too
                    subprocess.run(
                        f'"{gcloud_path}" services enable firebase.googleapis.com',
                        shell=True, capture_output=True, text=True
                    )

                    # Try the PATCH again
                    ok2, response_text2 = enable_email_password_auth(project_id, token)
                    if ok2:
                        print("✅ Email/Password Authentication ENABLED!\n")
                    else:
                        print(f"⚠️  Auto-enable failed: {response_text2}")
                        print("   Please manually enable in Firebase Console:")
                        print(f"   https://console.firebase.google.com/project/{project_id}/authentication/providers\n")
                else:
                    print(f"⚠️  Auto-enable failed: {response_text}")
                    print("   Please manually enable in Firebase Console:")
                    print(f"   https://console.firebase.google.com/project/{project_id}/authentication/providers\n")

    # ── STEP 3: Connect Firebase Admin ───────────────────────
    print("🔌 Connecting to Firebase...")
    try:
        import firebase_admin
        from firebase_admin import credentials, auth as fb_auth
    except ImportError:
        install_package("firebase-admin")
        import firebase_admin
        from firebase_admin import credentials, auth as fb_auth

    try:
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        print("✅ Connected to Firebase!\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        sys.exit(1)

    # ── STEP 4: Create users ──────────────────────────────────
    create_auth_users(fb_auth)

    print("\n  💡 Users can now log in at your gym app.")
    print("  💡 Run this script again anytime — existing accounts are safely skipped.\n")


if __name__ == "__main__":
    main()
