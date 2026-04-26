import os
import re
import glob


def extract_config_fields(cdn_input):
    fields = {}
    patterns = [
        'apiKey', 'authDomain', 'projectId', 'storageBucket',
        'messagingSenderId', 'appId', 'measurementId', 'databaseURL'
    ]
    for field in patterns:
        match = re.search(rf'{field}\s*:\s*["\']([^"\']+)["\']', cdn_input)
        if match:
            fields[field] = match.group(1)
    return fields


def build_firebase_config_block(fields, indent=""):
    lines = [f'{indent}const firebaseConfig = {{']
    field_order = [
        'apiKey', 'authDomain', 'projectId', 'storageBucket',
        'messagingSenderId', 'appId', 'measurementId', 'databaseURL'
    ]
    for key in field_order:
        if key in fields:
            lines.append(f'{indent}    {key}: "{fields[key]}",')
    lines.append(f'{indent}}};')
    return '\n'.join(lines)


def build_inline_config(fields, indent=""):
    """Build config for initializeApp({ ... }) inline style"""
    lines = [f'initializeApp({{']
    field_order = [
        'apiKey', 'authDomain', 'projectId', 'storageBucket',
        'messagingSenderId', 'appId', 'measurementId', 'databaseURL'
    ]
    for key in field_order:
        if key in fields:
            lines.append(f'{indent}    {key}: "{fields[key]}",')
    lines.append(f'{indent}}})')
    return '\n'.join(lines)


def replace_firebase_config_in_file(filepath, new_fields):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Pattern 1: const/var/let firebaseConfig = { ... }
    named_patterns = [
        r'([ \t]*)const\s+firebaseConfig\s*=\s*\{[^}]+\};?',
        r'([ \t]*)firebaseConfig\s*=\s*\{[^}]+\};?',
        r'([ \t]*)(?:var|let)\s+firebaseConfig\s*=\s*\{[^}]+\};?',
    ]

    for pattern in named_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            indent = match.group(1).replace('\n', '').replace('\r', '')
            new_block = build_firebase_config_block(new_fields, indent)
            new_content = re.sub(pattern, new_block, content, flags=re.DOTALL)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True, "updated"

    # Pattern 2: initializeApp({ ... }) inline style
    inline_pattern = r'initializeApp\s*\(\s*\{[^}]+\}\s*\)'
    match = re.search(inline_pattern, content, re.DOTALL)
    if match:
        # Detect indent from the line where initializeApp appears
        line_start = content.rfind('\n', 0, match.start()) + 1
        indent = re.match(r'([ \t]*)', content[line_start:]).group(1)
        new_block = build_inline_config(new_fields, indent)
        new_content = re.sub(inline_pattern, new_block, content, flags=re.DOTALL)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True, "updated"

    return False, "no_config"


def get_cdn_input():
    print("\n📋 STEP 2: New Firebase CDN Config")
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
    return "\n".join(lines)


def print_banner():
    print("\n" + "=" * 55)
    print("   🔥  FIREBASE CDN REPLACER FOR ALL HTML FILES  🔥")
    print("=" * 55)
    print("  This script will:")
    print("  • Read your new Firebase CDN config")
    print("  • Scan ALL HTML files in your project folder")
    print("  • Replace firebaseConfig in every file automatically")
    print("  • Handles ALL config formats (with/without const,")
    print("    and inline initializeApp style)")
    print("=" * 55 + "\n")


def main():
    print_banner()

    print("📁 STEP 1: Project Folder")
    print("-" * 40)
    print("👉 Enter the full path to the folder containing your HTML files.")
    print(r"   Example: C:\Users\rpsrawat\Desktop\gym-app" + "\n")
    folder = input("📂 Folder path: ").strip().strip('"').strip("'")
    print()

    if not os.path.isdir(folder):
        print(f"❌ Folder not found: {folder}")
        return

    html_files = glob.glob(os.path.join(folder, "**", "*.html"), recursive=True)

    if not html_files:
        print(f"❌ No HTML files found in: {folder}")
        return

    print(f"✅ Found {len(html_files)} HTML file(s):\n")
    for f in html_files:
        print(f"   • {os.path.relpath(f, folder)}")

    cdn_input = get_cdn_input()

    new_fields = extract_config_fields(cdn_input)
    if not new_fields or 'projectId' not in new_fields:
        print("\n❌ Could not find firebaseConfig fields in what you pasted.")
        return

    print(f"\n✅ New Firebase config detected:")
    print(f"   projectId       : {new_fields.get('projectId', 'N/A')}")
    print(f"   authDomain      : {new_fields.get('authDomain', 'N/A')}")
    print(f"   appId           : {new_fields.get('appId', 'N/A')}")
    if 'measurementId' in new_fields:
        print(f"   measurementId   : {new_fields.get('measurementId')}")
    print()

    confirm = input("👉 Replace firebaseConfig in ALL HTML files above? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("\n❌ Cancelled. No files were changed.")
        return

    print("\n🔄 Replacing firebaseConfig in all files...")
    print("-" * 40)

    success_count = 0
    skip_count = 0
    fail_count = 0

    for filepath in html_files:
        filename = os.path.relpath(filepath, folder)
        try:
            success, message = replace_firebase_config_in_file(filepath, new_fields)
            if success:
                print(f"   ✔ {filename}")
                success_count += 1
            elif message == "no_config":
                print(f"   ⚪ {filename} — skipped (no firebaseConfig found)")
                skip_count += 1
        except Exception as e:
            print(f"   ❌ {filename} — Error: {e}")
            fail_count += 1

    print("\n" + "=" * 55)
    print("   🎉 REPLACEMENT COMPLETE!")
    print("=" * 55)
    print(f"  ✔ Updated  : {success_count} file(s)")
    print(f"  ⚪ Skipped  : {skip_count} file(s) — no firebaseConfig")
    print(f"  ❌ Failed   : {fail_count} file(s)")
    print(f"  📁 Folder  : {folder}")
    print(f"  🔗 Project : {new_fields.get('projectId', 'N/A')}")
    print("=" * 55)
    print("\n  👉 All your HTML files now point to your new Firebase!\n")


if __name__ == "__main__":
    main()