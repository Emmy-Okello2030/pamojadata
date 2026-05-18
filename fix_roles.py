import re
from pathlib import Path

auth_path = Path("src/auth/auth.py")

if not auth_path.exists():
    print("❌ auth.py not found")
    exit(1)

with open(auth_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Add dashboard to M&E Officer
old_me = """    'M&E Officer': [
        'data_input', 'data_quality', 'analysis', 'logframe',
        'data_responsibility', 'hdx', 'three_w'
    ],"""

new_me = """    'M&E Officer': [
        'data_input', 'data_quality', 'analysis', 'logframe',
        'data_responsibility', 'hdx', 'three_w',
        'dashboard'
    ],"""

if old_me in content:
    content = content.replace(old_me, new_me)
    print("✅ Added dashboard to M&E Officer")
else:
    print("⚠️ M&E Officer section not found or already fixed")

# Fix 2: Add budget and analysis to Donor
old_donor = """    'Donor': [
        'dashboard', 'ai_report'
    ],"""

new_donor = """    'Donor': [
        'dashboard', 'ai_report', 'analysis',
        'budget'
    ],"""

if old_donor in content:
    content = content.replace(old_donor, new_donor)
    print("✅ Added analysis and budget to Donor")
else:
    print("⚠️ Donor section not found or already fixed")

# Save the file
with open(auth_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n" + "=" * 50)
print("✅ Role permissions updated!")
print("=" * 50)
print("\nChanges made:")
print("  • M&E Officer: Added 'dashboard' permission")
print("  • Donor: Added 'analysis' and 'budget' (read-only) permissions")
print("\nRestart your app for changes to take effect:")
print("  streamlit run app.py")
