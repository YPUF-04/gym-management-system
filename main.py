"""
=======================================================================
  KURULUM (terminale yapıştır):
    pip install firebase-admin
    pip install qrcode[pil]
    pip install pillow
    pip install opencv-python
    pip install pyzbar

=======================================================================
"""

# -- Standard Libraries ────────────────────────────────────────────────
import os          # Screen clearing
import sys         # Application exit
import time        # Delays (time.sleep)
import hashlib     # Password hashing (SHA-256)
import getpass     # Masked password input
from datetime import datetime, timedelta   # Date/time operations
from pathlib import Path                   # File path management

# -- Firebase (pip install firebase-admin) ─────────────────────────────
import firebase_admin
from firebase_admin import credentials, firestore

# -- QR Code Generation (pip install qrcode[pil] pillow) ───────────────
import qrcode
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# -- Camera QR Scanner (pip install opencv-python pyzbar) ──────────────
try:
    import cv2
    from pyzbar import pyzbar
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False


# =======================================================================
#  CONSTANTS
# =======================================================================

QR_FOLDER = Path("qr_codes")
QR_FOLDER.mkdir(exist_ok=True)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = hashlib.sha256("admin123".encode()).hexdigest()

PACKAGES = {
    "1": ("1 Month",    30),
    "2": ("3 Months",   90),
    "3": ("6 Months",  180),
    "4": ("1 Year",    365),
    "5": ("Custom Date", 0),
}


# =======================================================================
#  FIREBASE CONNECTION
# =======================================================================

db = None

def connect_firebase():
    """Connects to Firebase Firestore using serviceAccountKey.json."""
    global db
    key_path = Path("serviceAccountKey.json")

    if not key_path.exists():
        print("ERROR: serviceAccountKey.json not found!")
        print("  1. Go to https://console.firebase.google.com")
        print("  2. Project Settings > Service Accounts > Generate new private key")
        print("  3. Rename the file to 'serviceAccountKey.json' and place it in this folder")
        sys.exit(1)

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(str(key_path))
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase connection established successfully.")
    except Exception as e:
        print(f"Firebase connection error: {e}")
        sys.exit(1)

def get_password(message="Password") -> str:
    """Takes password input without echoing characters on the screen."""
    try:
        return getpass.getpass(f"{message}: ")
    except Exception:
        return input(f"{message}: ")


def encrypt_password(text: str) -> str:
    """Hashes the input text using SHA-256."""
    return hashlib.sha256(text.encode()).hexdigest()


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def draw_line(n=50):
    print("-" * n)


def print_header(text: str):
    clear_screen()
    draw_line()
    print(f"  {text}")
    draw_line()
    print()


def format_remaining_time(seconds: int) -> str:
    """Converts seconds into days, hours, minutes, and seconds."""
    if seconds <= 0:
        return "MEMBERSHIP EXPIRED"
    days    = seconds // 86400
    rem     = seconds % 86400
    hours   = rem // 3600
    rem     = rem % 3600
    minutes = rem // 60
    secs    = rem % 60
    return f"{days} days  {hours} hours  {minutes} minutes  {secs} seconds"


def get_uid(member: dict) -> str:
    """Retrieves UID from member dictionary supporting old and new schemas."""
    return member.get("uid") or member.get("kullanici_id") or ""


def get_remaining_seconds(end_date_iso: str) -> int:
    """Calculates remaining seconds until the expiration date."""
    end_date = datetime.fromisoformat(end_date_iso)
    return max(0, int((end_date - datetime.now()).total_seconds()))


def generate_id(username: str) -> str:
    """Generates a unique 12-character ID based on the username."""
    return hashlib.md5(username.lower().encode()).hexdigest()[:12]


def ask_input(question: str, required=True) -> str:
    """Prompts user for input and enforces non-empty values if required."""
    while True:
        response = input(f"{question}: ").strip()
        if response or not required:
            return response
        print("  This field cannot be left blank.")


def select_menu_option(options: list[str]) -> str:
    """Validates user menu choice against a list of valid choices."""
    while True:
        choice = input("Your choice: ").strip()
        if choice in options:
            return choice
        print(f"  Invalid choice. Please enter one of the following: {'/'.join(options)}")


# =======================================================================
#  QR CODE OPERATIONS
# =======================================================================

def generate_qr(uid: str, first_name: str, last_name: str, open_file=False) -> Path:
    """Generates a personalized QR code PNG file."""
    content = f"GYMSYS|UID:{uid}|{first_name} {last_name}"

    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4
    )
    qr.add_data(content)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    file_path = QR_FOLDER / f"{uid}.png"
    img.save(str(file_path))

    if open_file:
        if os.name == "nt":                  # Windows
            os.startfile(str(file_path))
        elif sys.platform == "darwin":    # macOS
            os.system(f"open '{file_path}'")
        else:                             # Linux
            os.system(f"xdg-open '{file_path}'")

    return file_path


def print_qr_to_terminal(uid: str):
    """Renders the QR code inside the terminal using ASCII characters."""
    qr = qrcode.QRCode(border=1)
    qr.add_data(f"GYMSYS|UID:{uid}")
    qr.make(fit=True)
    print("\nQR Code:")
    for row in qr.get_matrix():
        print("".join("##" if pixel else "  " for pixel in row))
    print()


def scan_qr_from_camera() -> str | None:
    """Scans QR code via webcam feed and returns verified UID."""
    if not CAMERA_AVAILABLE:
        print("ERROR: opencv or pyzbar dependencies are missing.")
        print("  Run: pip install opencv-python pyzbar")
        return None

    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("ERROR: Could not open camera feed!")
        print("  Is DroidCam active? Adjust camera index 0 if using multiple inputs.")
        return None

    print("Camera active. Hold your QR code up to the camera. Press 'q' to cancel.")
    found_uid = None

    while True:
        success, frame = camera.read()
        if not success:
            break

        for qr in pyzbar.decode(frame):
            data = qr.data.decode("utf-8")

            if data.startswith("GYMSYS|UID:"):
                found_uid = data.split("|")[1].replace("UID:", "")

                points = [(p.x, p.y) for p in qr.polygon]
                for i in range(len(points)):
                    cv2.line(frame, points[i], points[(i+1) % len(points)], (0, 255, 0), 3)
                cv2.putText(frame, f"Found: {found_uid}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("GYM QR Scanner  |  q = cancel", frame)

        if found_uid:
            time.sleep(0.8)
            break
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()
    return found_uid


# =======================================================================
#  FIRESTORE CRUD DATABASE ACTIONS
# =======================================================================

def save_user(data: dict) -> bool:
    try:
        db.collection("kullanicilar").document(data["uid"]).set(data)
        return True
    except Exception as e:
        print(f"Registration error: {e}")
        return False


def get_user_by_username(username: str) -> dict | None:
    try:
        results = (db.collection("kullanicilar")
                     .where(filter=firestore.FieldFilter("kullanici_adi", "==", username.lower()))
                     .limit(1).get())
        for doc in results:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"Query error: {e}")
        return None


def get_user_by_uid(uid: str) -> dict | None:
    try:
        doc = db.collection("kullanicilar").document(uid).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        print(f"Query error: {e}")
        return None


def get_all_users() -> list:
    try:
        return [doc.to_dict() for doc in db.collection("kullanicilar").get()]
    except Exception as e:
        print(f"Fetch list error: {e}")
        return []


def update_user(uid: str, updates: dict) -> bool:
    try:
        db.collection("kullanicilar").document(uid).update(updates)
        return True
    except Exception as e:
        print(f"Update error: {e}")
        return False


def delete_user(uid: str) -> bool:
    try:
        db.collection("kullanicilar").document(uid).delete()
        qr_file = QR_FOLDER / f"{uid}.png"
        if qr_file.exists():
            qr_file.unlink()
        return True
    except Exception as e:
        print(f"Deletion error: {e}")
        return False


def is_username_available(username: str) -> bool:
    return get_user_by_username(username) is None


def log_check_in(uid: str, full_name: str, method="QR_CAMERA"):
    try:
        db.collection("giris_loglari").add({
            "uid":      uid,
            "ad_soyad": full_name,
            "tur":      method,
            "zaman":    datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Logging error: {e}")


def get_logs(limit=50) -> list:
    try:
        results = (db.collection("giris_loglari")
                     .order_by("zaman", direction=firestore.Query.DESCENDING)
                     .limit(limit).get())
        return [doc.to_dict() for doc in results]
    except Exception as e:
        print(f"Log fetch error: {e}")
        return []


# =======================================================================
#  SCREENS & PANELS INTERFACES
# =======================================================================

def login_screen() -> tuple[str, dict | None]:
    print_header("GYM MANAGEMENT SYSTEM")

    if CAMERA_AVAILABLE:
        print("  Camera Status: READY")
    else:
        print("  Camera Status: DISABLED (opencv/pyzbar missing)")

    print()
    print("  1 -> Admin Login")
    print("  2 -> Member Login (Username + Password)")
    print("  3 -> Access via Text Entry Code")
    if CAMERA_AVAILABLE:
        print("  4 -> Access via QR Code Scanning")
    print("  0 -> Exit Program")
    print()

    options = ["0", "1", "2", "3", "4"] if CAMERA_AVAILABLE else ["0", "1", "2", "3"]
    choice = select_menu_option(options)

    if choice == "0":
        return "cikis", None

    if choice == "1":
        username = ask_input("Username")
        password = get_password("Password")

        if username == ADMIN_USERNAME and encrypt_password(password) == ADMIN_PASSWORD:
            print("Admin authentication successful.")
            time.sleep(0.8)
            return "admin", None

        print("Invalid administrative credentials.")
        time.sleep(1.5)
        return login_screen()

    if choice == "2":
        username = ask_input("Username").lower()
        password = get_password("Password")
        member   = get_user_by_username(username)

        if member is None:
            print("This username is not registered.")
            time.sleep(1.5)
            return login_screen()

        if member.get("sifre_hash") != encrypt_password(password):
            print("Incorrect password profile match.")
            time.sleep(1.5)
            return login_screen()

        print(f"Welcome back, {member['ad']} {member['soyad']}!")
        time.sleep(0.8)
        return "uye", member

    if choice == "3":
        code   = input("Enter Text Access Code: ").strip()
        member = get_user_by_uid(code)

        if member is None:
            print("Invalid code identifier.")
            time.sleep(1.5)
            return login_screen()

        remaining_sec = get_remaining_seconds(member["bitis_tarihi"])
        full_name     = f"{member['ad']} {member['soyad']}"

        if remaining_sec <= 0:
            print("ACCESS DENIED: Membership duration period has expired.")
            print(f"  User: {full_name}")
            print(f"  End Date: {member['bitis_tarihi'][:10]}")
            time.sleep(2)
            return login_screen()

        log_check_in(code, full_name, "TEXT_CODE")
        print(f"Welcome, {full_name}!")
        print(f"  Remaining: {format_remaining_time(remaining_sec)}")
        time.sleep(0.8)
        return "uye", member

    if choice == "4":
        print("Initializing camera components...")
        uid = scan_qr_from_camera()

        if uid is None:
            print("QR check-in operation canceled.")
            time.sleep(1)
            return login_screen()

        member = get_user_by_uid(uid)
        if member is None:
            print(f"No active record associated with this QR identifier. UID: {uid}")
            time.sleep(2)
            return login_screen()

        remaining_sec = get_remaining_seconds(member["bitis_tarihi"])
        full_name     = f"{member['ad']} {member['soyad']}"

        if remaining_sec <= 0:
            print("ACCESS DENIED: Membership duration period has expired.")
            print(f"  User: {full_name}")
            print(f"  End Date: {member['bitis_tarihi'][:10]}")
            time.sleep(2)
            return login_screen()

        log_check_in(uid, full_name, "QR_CAMERA")
        print(f"ACCESS GRANTED: {full_name}")
        print(f"  Remaining: {format_remaining_time(remaining_sec)}")
        time.sleep(1)
        return "uye", member


def get_local_ip() -> str:
    """Finds the local WiFi IP address of the machine (e.g., 192.168.x.x)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def serve_qr_to_phone(uid: str, first_name: str, last_name: str):
    """Spins up a lightweight server to let mobile phones download the QR image over WiFi."""
    qr_file = generate_qr(uid, first_name, last_name)
    ip      = get_local_ip()
    port    = 8181

    class QRHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/qr", "/qr.png"):
                with open(str(qr_file), "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Content-Disposition", f'attachment; filename="qr_{uid}.png"')
                self.end_headers()
                self.wfile.write(data)
            else:
                html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Your QR Access Code</title>
  <style>
    body {{ font-family: sans-serif; text-align: center; background: #f5f5f5; padding: 30px; }}
    img  {{ max-width: 300px; border: 2px solid #333; border-radius: 8px; background: white; padding: 10px; }}
    a    {{ display: inline-block; margin-top: 20px; padding: 12px 28px; background: #333; color: white; text-decoration: none; border-radius: 6px; font-size: 16px; }}
  </style>
</head>
<body>
  <h2>{first_name} {last_name}</h2>
  <p>Your Access QR Code:</p>
  <img src="/qr" alt="QR Code"><br>
  <a href="/qr.png" download>Save to Phone</a>
  <p style="color:#888; font-size:13px; margin-top:30px;">
    Press Enter back inside the terminal interface to close this server connection link.
  </p>
</body>
</html>"""
                enc = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(enc)))
                self.end_headers()
                self.wfile.write(enc)

        def log_message(self, fmt, *args):
            pass

    server = HTTPServer(("", port), QRHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    print()
    print("Local QR Web Server Started!")
    print("  Connect your mobile phone device to the same WiFi network and open:")
    print()
    print(f"  >>> http://{ip}:{port} <<<")
    print()
    print("  The webpage displays your QR badge. Tap 'Save to Phone' to download.")
    print("  Press Enter to terminate the web host server.")
    print()
    input()

    server.shutdown()
    print("Web server closed.")


def member_panel(member: dict):
    while True:
        print_header(f"MEMBER DASHBOARD  |  {member['ad']} {member['soyad']}")

        remaining_sec = get_remaining_seconds(member["bitis_tarihi"])

        print(f"  Full Name         : {member['ad']} {member['soyad']}")
        print(f"  Username Profile  : {member.get('kullanici_adi', '-')}")
        print(f"  Contact Phone     : {member.get('telefon', '-')}")
        print(f"  Email Address     : {member.get('eposta', '-')}")
        print(f"  Enrolled Package  : {member.get('paket_adi', '-')}")
        print(f"  Start Valid Date  : {member['baslangic_tarihi'][:10]}")
        print(f"  End Expiry Date   : {member['bitis_tarihi'][:10]}")
        print(f"  Account Status    : {'ACTIVE' if remaining_sec > 0 else 'MEMBERSHIP EXPIRED'}")
        print(f"  Time Remaining    : {format_remaining_time(remaining_sec)}")
        print()
        draw_line()
        print("  1 -> Transfer My QR Code to Phone (WiFi Link)")
        print("  2 -> Live Countdown Monitor (Press CTRL+C to halt stream)")
        print("  0 -> Log Out")
        print()

        choice = select_menu_option(["0", "1", "2"])

        if choice == "0":
            break
        elif choice == "1":
            serve_qr_to_phone(get_uid(member), member["ad"], member["soyad"])
        elif choice == "2":
            live_countdown_loop(member["bitis_tarihi"])


def live_countdown_loop(end_date_iso: str):
    print("Press CTRL+C to exit real-time logging.\n")
    try:
        while True:
            remaining_sec = get_remaining_seconds(end_date_iso)
            print(f"\r  Remaining: {format_remaining_time(remaining_sec)}   ", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCountdown stream stopped.")


def admin_panel():
    while True:
        print_header("ADMINISTRATIVE MANAGEMENT CONSOLE")
        print("  1 -> Register New System Member")
        print("  2 -> View All Registered Members")
        print("  3 -> Search / Edit / Delete Member Profiles")
        print("  4 -> View Entry Activity History Logs")
        print("  5 -> Launch QR Camera Turnstile Scanner Mode")
        print("  0 -> Return to Main Exit Menu")
        print()

        choice = select_menu_option(["0", "1", "2", "3", "4", "5"])

        if   choice == "0": break
        elif choice == "1": register_member()
        elif choice == "2": list_all_members()
        elif choice == "3": search_and_modify_member()
        elif choice == "4": display_logs()
        elif choice == "5": turnstile_camera_scanner()


def register_member():
    print_header("REGISTER NEW MEMBER")

    first_name = ask_input("First Name").title()
    last_name  = ask_input("Last Name").title()

    while True:
        username = ask_input("Choose Unique Username").lower()
        if is_username_available(username):
            break
        print("  This username is already taken. Please try another.")

    phone_number = ask_input("Phone Number")
    email_addr   = ask_input("Email Address")

    while True:
        password  = get_password("Set Password")
        password_confirm = get_password("Confirm Password")
        if password == password_confirm:
            break
        print("  Passwords do not match. Please re-enter.")

    print()
    print("Available Membership Packages:")
    for key, (label, total_days) in PACKAGES.items():
        day_tag = f" ({total_days} days)" if total_days > 0 else ""
        print(f"  {key} -> {label}{day_tag}")
    print()

    package_choice = select_menu_option(list(PACKAGES.keys()))
    package_label, package_days = PACKAGES[package_choice]
    start_date = datetime.now()

    if package_days > 0:
        end_date = start_date + timedelta(days=package_days)
    else:
        while True:
            try:
                custom_start = ask_input("Start date entry (YYYY-MM-DD)")
                custom_end   = ask_input("End expiration date (YYYY-MM-DD)")
                start_date   = datetime.strptime(custom_start, "%Y-%m-%d")
                end_date     = datetime.strptime(custom_end, "%Y-%m-%d")
                if end_date > start_date:
                    break
                print("  The expiration date cannot be equal or prior to the activation date.")
            except ValueError:
                print("  Date string format parsing error. Example schema format: 2026-06-15")

    uid  = generate_id(username)
    data = {
        "uid":               uid,
        "kullanici_adi":    username,
        "ad":                first_name,
        "soyad":             last_name,
        "telefon":           phone_number,
        "eposta":            email_addr,
        "sifre_hash":        encrypt_password(password),
        "paket_adi":        package_label,
        "baslangic_tarihi": start_date.isoformat(),
        "bitis_tarihi":     end_date.isoformat(),
        "kayit_tarihi":     datetime.now().isoformat(),
        "aktif":            True,
    }

    if save_user(data):
        qr_file = generate_qr(uid, first_name, last_name, open_file=True)
        print()
        print("Member successfully registered inside database!")
        print(f"  Username Account : {username}")
        print(f"  Saved QR Location: {qr_file}")
        print(f"  Expiration Date  : {end_date.strftime('%m.%d.%Y')}")
        print()
        print(f"  Text Access Code : {uid}")
        print("  (This specific string can be used for fallback authentication keypads)")
        print_qr_to_terminal(uid)
    else:
        print("Failed registration event sequence execution.")

    input("\nPress Enter to return to management console...")


def list_all_members():
    print_header("ALL REGISTERED MEMBERS LIST")

    members_list = get_all_users()
    if not members_list:
        print("No registered membership entries found.")
        input("Press Enter...")
        return

    print(f"{'Full Name':<22} {'Username':<16} {'Package':<12} {'End Date':<12} {'Status'}")
    draw_line(75)

    for member in members_list:
        end_date_str = member.get("bitis_tarihi", "")
        try:
            rem_sec = get_remaining_seconds(end_date_str)
        except Exception:
            rem_sec = -1

        full_name = f"{member.get('ad','') or ''} {member.get('soyad','') or ''}"
        status    = "ACTIVE" if rem_sec > 0 else "EXPIRED"

        print(
            f"{full_name:<22} "
            f"{member.get('kullanici_adi','-'):<16} "
            f"{member.get('paket_adi','-'):<12} "
            f"{end_date_str[:10]:<12} "
            f"{status}"
        )

    draw_line(75)
    print(f"Total Database Pool Count: {len(members_list)} metrics entries.")
    input("\nPress Enter to clear screen view...")


def search_and_modify_member():
    print_header("SEARCH AND MANAGE MEMBERS")

    username = ask_input("Enter Target Account Username").lower()
    member   = get_user_by_username(username)

    if not member:
        print("No matching records found for that profile name.")
        input("Press Enter...")
        return

    display_individual_details(member)

    print()
    print("  1 -> Edit Personal Demographics Metadata")
    print("  2 -> Update / Extend Membership Term Package")
    print("  3 -> Regenerate and Print New Access QR Code")
    print("  4 -> Permanently Purge Account Record")
    print("  0 -> Return to Management Hub")
    print()

    choice = select_menu_option(["0", "1", "2", "3", "4"])

    if   choice == "1": edit_member_details(member)
    elif choice == "2": modify_member_package(member)
    elif choice == "3":
        qr_file = generate_qr(get_uid(member), member["ad"], member["soyad"])
        print(f"QR code regenerated: {qr_file}")
        print_qr_to_terminal(get_uid(member))
        input("Press Enter...")
    elif choice == "4":
        confirmation = input(f"  Are you sure you want to delete {member['ad']} {member['soyad']}? (y/n): ").strip().lower()
        if confirmation == "y":
            delete_user(get_uid(member))
            print("Profile scrubbed from master systems directories.")
        input("Press Enter...")


def display_individual_details(member: dict):
    rem_sec = get_remaining_seconds(member.get("bitis_tarihi", ""))
    draw_line()
    print(f"  Full Name         : {member.get('ad','')} {member.get('soyad','')}")
    print(f"  Username Handle   : {member.get('kullanici_adi', '-')}")
    print(f"  Phone Registry    : {member.get('telefon', '-')}")
    print(f"  Email Address     : {member.get('eposta', '-')}")
    print(f"  Active Plan       : {member.get('paket_adi', '-')}")
    print(f"  Activation Point  : {member.get('baslangic_tarihi','')[:10]}")
    print(f"  Expiration Point  : {member.get('bitis_tarihi','')[:10]}")
    print(f"  Time Left Metric  : {format_remaining_time(rem_sec)}")
    print(f"  Unique System ID  : {member.get('uid', '-')}")
    draw_line()


def edit_member_details(member: dict):
    uid = get_uid(member)
    print("(Leave fields completely blank if you do not want to alter historical baseline entries)\n")

    updates = {}

    new_first_name = input(f"  First Name  [{member['ad']}]: ").strip()
    new_last_name  = input(f"  Last Name   [{member['soyad']}]: ").strip()
    new_phone      = input(f"  Phone Number [{member.get('telefon','')}]: ").strip()
    new_email      = input(f"  Email        [{member.get('eposta','')}]: ").strip()

    current_user_handle = member.get("kullanici_adi", "")
    new_user_handle     = input(f"  Username     [{current_user_handle}]: ").strip().lower()
    
    if new_user_handle and new_user_handle != current_user_handle:
        if is_username_available(new_user_handle):
            updates["kullanici_adi"] = new_user_handle
        else:
            print("  This username is taken. Field value changes discarded.")

    new_passwd = get_password("  New Password Entry (Blank to ignore parameter updates)")
    if new_passwd:
        passwd_confirm = get_password("  Repeat New Password Entry")
        if new_passwd == passwd_confirm:
            updates["sifre_hash"] = encrypt_password(new_passwd)
        else:
            print("  Password match sync failure. Change parameter discarded.")

    if new_first_name: updates["ad"]      = new_first_name.title()
    if new_last_name:  updates["soyad"]   = new_last_name.title()
    if new_phone:      updates["telefon"] = new_phone
    if new_email:      updates["eposta"]  = new_email

    if updates:
        update_user(uid, updates)
        print("Database record updated successfully.")
    else:
        print("No manual configuration entries processed. Record remains static.")

    input("Press Enter...")


def modify_member_package(member: dict):
    uid = get_uid(member)

    print("Select Renewal Plan Package Upgrade:")
    for key, (label, total_days) in PACKAGES.items():
        day_tag = f" ({total_days} days)" if total_days > 0 else ""
        print(f"  {key} -> {label}{day_tag}")
    print()

    package_choice = select_menu_option(list(PACKAGES.keys()))
    package_label, package_days = PACKAGES[package_choice]

    print()
    print("  1 -> Initialize validity clock calculation starting TODAY")
    print("  2 -> Append extension term duration onto existing expiration date baseline")
    print()
    origin_choice = select_menu_option(["1", "2"])

    if origin_choice == "1":
        start_date = datetime.now()
    else:
        existing_expiry_iso = member.get("bitis_tarihi", datetime.now().isoformat())
        existing_expiry     = datetime.fromisoformat(existing_expiry_iso)
        start_date          = max(existing_expiry, datetime.now())

    if package_days > 0:
        end_date = start_date + timedelta(days=package_days)
    else:
        while True:
            try:
                custom_end_str = ask_input("Specify custom expiration date (YYYY-MM-DD)")
                end_date       = datetime.strptime(custom_end_str, "%Y-%m-%d")
                if end_date > start_date:
                    break
                print("  Date logic sequencing validation error.")
            except ValueError:
                print("  Formatting paradigm syntax error. Example structure requirements: YYYY-MM-DD")

    update_user(uid, {
        "paket_adi":        package_label,
        "baslangic_tarihi": start_date.isoformat(),
        "bitis_tarihi":     end_date.isoformat(),
    })
    print(f"New system operational expiration timeline limit: {end_date.strftime('%m.%d.%Y')}")
    input("Press Enter...")


def display_logs():
    print_header("SYSTEM ACCESS AUDIT ENTRIES (Last 50 Logs)")

    activity_logs = get_logs(50)
    if not activity_logs:
        print("No historical logging activity captured inside database tables.")
        input("Press Enter...")
        return

    print(f"{'Date & Timestamp':<20} {'User Full Name':<22} {'Mechanism':<12} {'Unique UID'}")
    draw_line(72)

    for entry in activity_logs:
        timestamp_formatted = entry.get("zaman", "")[:19].replace("T", " ")
        print(
            f"{timestamp_formatted:<20} "
            f"{entry.get('ad_soyad','-'):<22} "
            f"{entry.get('tur','-'):<12} "
            f"{entry.get('uid','-')}"
        )

    draw_line(72)
    input("\nPress Enter to continue tracking options...")


def turnstile_camera_scanner():
    print_header("QR TURNSTILE TERMINAL SCANNING MODE")

    if not CAMERA_AVAILABLE:
        print("Prerequisite hardware integration dependencies (opencv/pyzbar) are absent.")
        print("  Execute target script environment setup: pip install opencv-python pyzbar")
        input("Press Enter...")
        return

    while True:
        print("Position QR label in view. Use operational window 'q' hook controls to break capture loop.")
        uid = scan_qr_from_camera()

        if uid is None:
            print("Scan execution sequence aborted by operator terminal commands.")
            break

        member = get_user_by_uid(uid)

        if not member:
            print(f"ACCESS REJECTED: Unrecognized credential layout configuration data. UID: {uid}")
        else:
            remaining_sec = get_remaining_seconds(member["bitis_tarihi"])
            full_name     = f"{member['ad']} {member['soyad']}"

            if remaining_sec > 0:
                print(f"ACCESS APPROVED : {full_name}")
                print(f"  Time Balance  : {format_remaining_time(remaining_sec)}")
                log_check_in(uid, full_name, "QR_CAMERA")
            else:
                print(f"ACCESS REJECTED: Registered profile validity limit reached.")
                print(f"  User profile  : {full_name}")
                print(f"  Expiration    : {member['bitis_tarihi'][:10]}")

        print()
        loop_check = input("Process alternative scanning cycle? (y/n): ").strip().lower()
        if loop_check != "y":
            break


def main():
    connect_firebase()

    while True:
        role, active_user = login_screen()

        if role == "cikis":
            print("\nSession logging out. Have a great workout session!\n")
            break
        elif role == "admin":
            admin_panel()
        elif role == "uye":
            member_panel(active_user)


if __name__ == "__main__":
    main()