from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, abort, send_file
from werkzeug.utils import secure_filename
from web3 import Web3
import hashlib
import json
import os
import datetime
import uuid
import io
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import requests

# Load environment variables
load_dotenv()

# --- SECURITY CHECK ---
# --- SECURITY CHECK ---
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', '').strip().strip('"').strip("'")

# Ensure key is bytes for Fernet
if ENCRYPTION_KEY and isinstance(ENCRYPTION_KEY, str):
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()

try:
    if not ENCRYPTION_KEY:
        raise ValueError("Key is empty")
    # cid = hashlib.md5(ENCRYPTION_KEY).hexdigest()[:8]
    # print(f"ENCRYPTION KEY VALID. KeyID: {cid}")
    cipher_suite = Fernet(ENCRYPTION_KEY)
except Exception as e:
    print(f"FATAL: ENCRYPTION_KEY missing or invalid in .env: {e}")
    exit(1)

app = Flask(__name__)
app.secret_key = 'supersecretkey_demo_project'
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- CONFIGURATION (Change these for your local setup) ---
# For Ganache, usually http://127.0.0.1:7545 or 8545
BLOCKCHAIN_URL = "http://127.0.0.1:7545" 
# Replace with your deployed contract address
CONTRACT_ADDRESS = "0x16dD75A742E34FB36177eE57Dc7Ba88d73bD068e" 
# Replace with the account to perform transactions (e.g., first account from Ganache)
DEFAULT_ACCOUNT = "0xe9f6CA0957C7EDbDBC58a5ab1bA9B610AB1e7Cda"

# Minimal ABI for our contract (You can copy the full one from remix/hardhat build)
CONTRACT_ABI = [
	{
		"anonymous": False,
		"inputs": [
			{"indexed": False, "internalType": "string", "name": "fileHash", "type": "string"},
			{"indexed": False, "internalType": "string", "name": "uploader", "type": "string"},
			{"indexed": False, "internalType": "string", "name": "timestamp", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "previousHash", "type": "string"}
		],
		"name": "ReportUploaded",
		"type": "event"
	},
	{
		"inputs": [{"internalType": "string", "name": "_hash", "type": "string"}],
		"name": "verifyReport",
		"outputs": [
			{"internalType": "string", "name": "", "type": "string"},
			{"internalType": "string", "name": "", "type": "string"},
			{"internalType": "string", "name": "", "type": "string"},
			{"internalType": "bool", "name": "", "type": "bool"},
            {"internalType": "string", "name": "", "type": "string"}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{"internalType": "string", "name": "_hash", "type": "string"},
			{"internalType": "string", "name": "_timestamp", "type": "string"},
			{"internalType": "string", "name": "_uploader", "type": "string"}
		],
		"name": "storeReport",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
    {
		"inputs": [
			{"internalType": "string", "name": "_newHash", "type": "string"},
            {"internalType": "string", "name": "_previousHash", "type": "string"},
			{"internalType": "string", "name": "_timestamp", "type": "string"},
			{"internalType": "string", "name": "_uploader", "type": "string"}
		],
		"name": "updateReport",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	}
]

# Initialize Web3
try:
    w3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_URL))
    if w3.is_connected():
        print("Connected to Blockchain")
        
        # Auto-detect account if possible
        if w3.eth.accounts:
            DEFAULT_ACCOUNT = w3.eth.accounts[0]
            print(f"Using Default Account (Auto-detected): {DEFAULT_ACCOUNT}")
        else:
            print("Warning: No accounts retrieved from provider. Using hardcoded DEFAULT_ACCOUNT.")
        
        contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
    else:
        print("Failed to connect to Blockchain")
        contract = None
except Exception as e:
    print(f"Error connecting to blockchain: {e}")
    contract = None

    contract = None

# --- IPFS Configuration ---
IPFS_API_URL = "http://127.0.0.1:5001/api/v0"

def ipfs_add(file_bytes):
    """Uploads bytes to IPFS via API and returns CID."""
    try:
        files = {'file': file_bytes}
        response = requests.post(f"{IPFS_API_URL}/add", files=files)
        response.raise_for_status()
        return response.json()['Hash']
    except Exception as e:
        print(f"IPFS Upload Error: {e}")
        return None

def ipfs_get(cid):
    """Retrieves bytes from IPFS via API."""
    try:
        params = {'arg': cid}
        response = requests.post(f"{IPFS_API_URL}/cat", params=params)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"IPFS Get Error: {e}")
        return None

# Check IPFS Connection (Optional)
try:
    requests.post(f"{IPFS_API_URL}/id", timeout=2)
    print("Connected to IPFS API")
except:
    print("Warning: IPFS Daemon not reachable")

# In-memory "Database" for the demo
# Structure: { username: { password, role, uploads: [] } }
# Uploads structure: [{ filename, hash, time, tx_hash, verified }]
DB = {
    "admin": {"password": "admin", "role": "admin", "uploads": []},
    "emp1": {"password": "123", "role": "employee", "uploads": []},
    "emp2": {"password": "123", "role": "employee", "uploads": []}
}


ALL_UPLOADS = [] # Global list for admin view

# --- Intrusion Prevention Monitor ---
SECURITY_MONITOR = {}

# --- HELPER FUNCTIONS ---

def init_security_profile(user):
    if user not in SECURITY_MONITOR:
        SECURITY_MONITOR[user] = {
            "tamper_attempts": 0,
            "blocked": False
        }

def block_user_if_tampered(username):
    if username not in SECURITY_MONITOR:
        SECURITY_MONITOR[username] = {
            "blocked": True,
            "reason": "Tampered Report Detected"
        }
    else:
        SECURITY_MONITOR[username]["blocked"] = True

    print(f"[IPS ALERT] User {username} blocked due to tampered upload.")

def is_user_blocked(username):
    return SECURITY_MONITOR.get(username, {}).get("blocked", False)

def generate_hash(file_bytes):
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_bytes)
    return sha256_hash.hexdigest()

def blockchain_store(file_hash, timestamp, uploader):
    if not contract or not w3.is_connected():
        return "MOCK_TX_HASH_NO_CONNECTION"
    
    try:
        # Simple transaction - in production, you'd sign this with a private key
        # For Ganache/Test, we can often just transact from an unlocked account
        tx_hash = contract.functions.storeReport(
            file_hash, timestamp, uploader
        ).transact({'from': DEFAULT_ACCOUNT})
        return w3.to_hex(tx_hash)
    except Exception as e:
        print(f"Blockchain Error: {e}")
        return "ERROR_STORING_ON_CHAIN"

def blockchain_update(new_hash, prev_hash, timestamp, uploader):
    if not contract or not w3.is_connected():
        return "MOCK_TX_HASH_NO_CONNECTION"
    try:
        tx_hash = contract.functions.updateReport(
            new_hash, prev_hash, timestamp, uploader
        ).transact({'from': DEFAULT_ACCOUNT})
        return w3.to_hex(tx_hash)
    except Exception as e:
        print(f"Blockchain Update Error (DETAILS): {e}")
        # Try to parse the error message if possible
        if hasattr(e, 'args') and len(e.args) > 0:
             print(f"Error Args: {e.args}")
        return "ERROR_UPDATING_ON_CHAIN"

def blockchain_verify(file_hash):
    if not contract or not w3.is_connected():
        return False
    try:
        data = contract.functions.verifyReport(file_hash).call()
        # Returns (fileHash, timestamp, uploader, exists)
        return data[3] # The boolean 'exists'
    except Exception as e:
        print(f"Blockchain Verify Error: {e}")
        return False



# --- ROUTES ---

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        pwd = request.form.get('password')
        role = request.form.get('role')

        if user in DB and DB[user]['password'] == pwd and DB[user]['role'] == role:
            # Check for IPS Block BEFORE allowing login
            if SECURITY_MONITOR.get(user, {}).get("blocked", False):
                return render_template('login.html', ips_blocked=True)

            session['user'] = user
            session['role'] = role
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('employee_dashboard'))
        else:
            return render_template('login.html', error="Invalid Credentials")
            
    return render_template('login.html')

@app.route('/employee')
def employee_dashboard():
    if 'user' not in session or session['role'] != 'employee':
        return redirect(url_for('login'))
    
    if is_user_blocked(session['user']):
        session.clear()
        return redirect(url_for('login'))
    
    user = session['user']
    my_uploads = DB[user]['uploads']
    return render_template('employee.html', user=user, uploads=my_uploads, count=len(my_uploads))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    if is_user_blocked(session['user']):
        return jsonify({
            "error": "Access Blocked by Intrusion Prevention System"
        }), 403
    
    user = session['user']
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Process file
    original_filename = secure_filename(file.filename)
    
    # 1. Read strict bytes
    file.stream.seek(0)
    file_content = file.read()
    
    # 2. Compute Hash of ORIGINAL file
    file_hash = generate_hash(file_content)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"UPLOAD DEBUG: Original File Hash: {file_hash}")

    # 3. Encrypt
    encrypted_data = cipher_suite.encrypt(file_content)
    
    # 4. Save as .enc
    encrypted_filename = f"{uuid.uuid4().hex}.enc"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], encrypted_filename)
    
    with open(file_path, 'wb') as f:
        f.write(encrypted_data)

    # Store on IPFS (Backup Layer)
    cid = ipfs_add(encrypted_data)
    if cid:
        print(f"IPFS CID generated: {cid}")
    else:
        print("IPFS Upload Failed")

    # Store on Blockchain
    tx_id = blockchain_store(file_hash, timestamp, user)

    # CRITICAL: Abort upload if blockchain transaction failed
    if tx_id == "ERROR_STORING_ON_CHAIN":
        print("[BLOCKCHAIN ERROR] storeReport failed – Upload Aborted")
        # Clean up the encrypted file we already wrote to disk
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({
            "success": False,
            "error": "Blockchain transaction failed. Please ensure Ganache is running and the contract is deployed."
        }), 500

    if tx_id == "MOCK_TX_HASH_NO_CONNECTION":
        print("[BLOCKCHAIN] No blockchain connection – Proceeding with local/IPFS storage only.")
    else:
        print(f"Blockchain TX SUCCESS: {tx_id}")

    # --- AUTO-GENERATE TAMPER ENGINE MAPPINGS ---
    try:
        from pdf_parser import extract_text_lines_from_pdf
        from hash_mapper import generate_line_hashes
        
        # pass the actual unencrypted bytes read earlier
        pages_lines = extract_text_lines_from_pdf(file_content)
        line_hashes = generate_line_hashes(pages_lines)
        
        # save hash map
        hashmap_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_hash}_hashmap.json")
        with open(hashmap_path, 'w') as f:
            json.dump(line_hashes, f)
            
        # save original lines for diff
        lines_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_hash}_lines.json")
        with open(lines_path, 'w') as f:
            json.dump(pages_lines, f)
        print(f"[TAMPER ENGINE] Auto-initialized mapping for {file_hash}")
    except Exception as e:
        print(f"[TAMPER ENGINE] Failed to auto-initialize mapping: {e}")

    # 5. Save to local DB (Mapping)
    record = {
        "sno": len(ALL_UPLOADS) + 1,
        "filename": original_filename,
        "encrypted_filename": encrypted_filename,
        "cid": cid,
        "time": timestamp,
        "hash": file_hash,
        "tx_id": tx_id,
        "uploader": user,
        "verified": "Pending",
        "stored_on_chain": tx_id != "MOCK_TX_HASH_NO_CONNECTION" and tx_id != "ERROR_STORING_ON_CHAIN",
        "simulate_local_attack": False,
        "simulate_cid_attack": False
    }
    
    DB[user]['uploads'].append(record)
    ALL_UPLOADS.append(record)

    return jsonify({"success": True, "tx_id": tx_id, "hash": file_hash})

@app.route('/update_report', methods=['POST'])
def update_report():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user = session['user']
    if 'file' not in request.files or 'previous_hash' not in request.form:
        return jsonify({"error": "Missing file or previous_hash"}), 400
        
    file = request.files['file']
    previous_hash = request.form['previous_hash']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Process file
    original_filename = secure_filename(file.filename)
    file_content = file.read()
    
    # 1. Compute Hash
    file_hash = generate_hash(file_content)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 2. Encrypt
    encrypted_data = cipher_suite.encrypt(file_content)
    
    # 3. Save as .enc
    encrypted_filename = f"{uuid.uuid4().hex}.enc"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], encrypted_filename)
    
    with open(file_path, 'wb') as f:
        f.write(encrypted_data)

    # Store UPDATE on IPFS
    cid = ipfs_add(encrypted_data)
    if cid:
        print(f"IPFS CID generated: {cid}")
    else:
        print("IPFS Upload Failed")

    # Store UPDATE on Blockchain
    tx_id = blockchain_update(file_hash, previous_hash, timestamp, user)

    # Determine Status
    if tx_id == "ERROR_UPDATING_ON_CHAIN":
        verified_status = "Blockchain Update Failed"
        on_chain_status = False
    else:
        verified_status = "Pending"
        on_chain_status = True

    # --- AUTO-GENERATE TAMPER ENGINE MAPPINGS ---
    try:
        from pdf_parser import extract_text_lines_from_pdf
        from hash_mapper import generate_line_hashes
        
        # pass the actual unencrypted bytes read earlier
        pages_lines = extract_text_lines_from_pdf(file_content)
        line_hashes = generate_line_hashes(pages_lines)
        
        # save hash map
        hashmap_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_hash}_hashmap.json")
        with open(hashmap_path, 'w') as f:
            json.dump(line_hashes, f)
            
        # save original lines for diff
        lines_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_hash}_lines.json")
        with open(lines_path, 'w') as f:
            json.dump(pages_lines, f)
        print(f"[TAMPER ENGINE] Auto-initialized mapping for update {file_hash}")
    except Exception as e:
        print(f"[TAMPER ENGINE] Failed to auto-initialize mapping: {e}")

    # 4. Save to local DB (Mapping)
    record = {
        "sno": len(ALL_UPLOADS) + 1,
        "filename": original_filename,
        "encrypted_filename": encrypted_filename,
        "cid": cid,
        "time": timestamp,
        "hash": file_hash,
        "previous_hash": previous_hash, # Link to old version
        "tx_id": tx_id,
        "uploader": user,
        "verified": verified_status,
        "stored_on_chain": on_chain_status,
        "simulate_local_attack": False,
        "simulate_cid_attack": False
    }
    
    DB[user]['uploads'].append(record)
    ALL_UPLOADS.append(record)

    return jsonify({"success": True, "tx_id": tx_id, "hash": file_hash, "version": "updated"})

@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    return render_template('admin.html', uploads=ALL_UPLOADS)

@app.route('/verify_report', methods=['POST'])
def verify_report():
    if 'user' not in session or session['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    original_hash = data.get('hash')

    user = session['user']
    init_security_profile(user)

    if SECURITY_MONITOR[user]['blocked']:
        print(f"[IPS BLOCK] {user} is currently blocked due to suspicious behaviour.")
        return jsonify({
            "status": "Access Blocked by Intrusion Prevention System",
            "on_chain": False
        })
    
    # 1. Find the file record locally using the HASH
    record = None
    for upload in ALL_UPLOADS:
        if upload['hash'] == original_hash:
            record = upload
            break
            
    if not record:
        return jsonify({"status": "Error: Record Not Found", "on_chain": False})

    # STEP 1: Lazy Initialization
    record.setdefault('verified', 'Pending')
    record.setdefault('is_quarantined', False)
    record.setdefault('risk_reason', None)
    
    # CRITICAL SECURITY CHECK: Block verification if not stored on chain
    if not record.get('stored_on_chain'):
        print("[SECURITY] Verification blocked: Not stored on chain")
        
        record['verified'] = "Not Stored On Chain"
        
        return jsonify({
            "status": "Verification Failed – Not Stored On Blockchain",
            "on_chain": False
        })

    encrypted_filename = record.get('encrypted_filename')
    
    # Fallback for old files (if any exist without encryption) - strict mode: fail
    if not encrypted_filename:
         return jsonify({"status": "Error: Legacy File / Missing Enc mapping", "on_chain": False})

    # 2. Read the ENCRYPTED file from disk
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], encrypted_filename)
    if not os.path.exists(file_path):
        return jsonify({"status": "Error: File Missing", "on_chain": False})
        
    try:
        # FETCH ENCRYPTED FILE BASED ON ATTACK TYPE
        
        if record.get('simulate_local_attack') or record.get('simulate_content_attack'):
            print("[SIMULATION] Reading tampered local encrypted file")
            
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], record['encrypted_filename'])
            
            if not os.path.exists(file_path):
                return jsonify({"status": "Local File Missing", "on_chain": False})
            
            with open(file_path, 'rb') as f:
                encrypted_bytes = f.read()

        else:
            if record.get('simulate_cid_attack'):
                cid_to_fetch = "QmFakeTamperedCID123"
                print("[SIMULATION] Using tampered CID reference")
            else:
                cid_to_fetch = record.get('cid')
            
            print("Fetching encrypted file from IPFS...")
            encrypted_bytes = ipfs_get(cid_to_fetch)
        
        # Step B: Decrypt FIRST
        decrypted_bytes = cipher_suite.decrypt(encrypted_bytes)

        # LOG 1: After decrypting file
        print("----------------------------------------")
        print("VERIFY REQUEST START")
        print(f"Requested Hash: {original_hash}")
        print(f"Encrypted File: {encrypted_filename}")
        print("----------------------------------------")

    except Exception as e:
        print(f"DECRYPTION FAILED (TAMPERING SUSPECTED): {e}")
        
        # Treat decryption failure as a severe integrity violation
        status = "QUARANTINED"
        record['verified'] = status
        record['is_quarantined'] = True
        record['risk_reason'] = "Decryption failed (File Corrupted/Tampered)"
        
        uploader = record.get('uploader')
        block_user_if_tampered(uploader)
        
        print("---------- SECURITY ALERT ----------")
        print("Tampering/Corruption detected (Decryption Failed)!")
        print(f"File: {record['filename']}")
        print(f"Uploader: {record['uploader']}")
        print("------------------------------------")
        
        return jsonify({
            "status": "QUARANTINED",
            "on_chain": False
        })
        
    # Step C: Hash the DECRYPTED content
    local_hash = generate_hash(decrypted_bytes)
    
    # LOG 2: After generating local_hash
    print(f"LOCAL HASH (Decrypted SHA-256): {local_hash}")

    # Step D: Fetch from Blockchain
    blockchain_hash = "N/A"
    exists_on_chain = False
    
    previous_hash = record.get('previous_hash')

    if contract and w3.is_connected():
        try:
            # FIX: verification must compare LOCAL_HASH vs ORIGINAL_BLOCKCHAIN_HASH
            original_hash = record['hash']
            
            # Fetch blockchain data using ORIGINAL hash
            chain_data = contract.functions.verifyReport(original_hash).call()
            blockchain_hash = chain_data[0]
            exists_on_chain = chain_data[3]
            
        except Exception as e:
            print(f"Blockchain Verification Error: {e}")
            blockchain_hash = "Error Fetching"
            exists_on_chain = False
            return jsonify({
                "status": "Blockchain Error: Smart Contract Not Found or Ganache Reset",
                "on_chain": False
            })
    else:
        print("Blockchain connection invalid.")
        
    # LOG 3: After blockchain call
    print(f"BLOCKCHAIN HASH: {blockchain_hash}")
    print(f"EXISTS ON CHAIN: {exists_on_chain}")

    # Step E: Compare Hashes
    # ALWAYS RESET STATUS before comparison
    record['verified'] = "Pending"
    record['risk_reason'] = None
    
    # Calculate local hash FRESHLY
    local_hash = generate_hash(decrypted_bytes)
    
    if exists_on_chain:
        if local_hash == blockchain_hash:
            record['verified'] = "Verified (On-Chain)"
            record['is_quarantined'] = False
            record['risk_reason'] = None
            
        else:
            # --- NEW TAMPER LOCALIZATION LOGIC ---
            print("[SECURITY ALERT] Hash mismatch detected. Running Document-Level Tamper Localization Engine...")
            try:
                # 1. Load original hash map
                hashmap_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{original_hash}_hashmap.json")
                if os.path.exists(hashmap_path):
                    with open(hashmap_path, 'r') as f:
                        original_hash_map = json.load(f)
                        
                    # 2. Extract and hash newly decrypted content
                    from pdf_parser import extract_text_lines_from_pdf
                    from hash_mapper import generate_line_hashes
                    from tamper_detector import compare_hashes
                    from highlight_engine import generate_diff_html
                    
                    new_pages_lines = extract_text_lines_from_pdf(decrypted_bytes)
                    new_hash_map = generate_line_hashes(new_pages_lines)
                    
                    # 3. Detect Mismatches
                    mismatches = compare_hashes(original_hash_map, new_hash_map)
                    print(f"[TAMPER LOCATOR] Found {len(mismatches)} line mismatches.")
                    
                    # 4. Generate Diff HTML
                    lines_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{original_hash}_lines.json")
                    if os.path.exists(lines_path):
                        with open(lines_path, 'r') as f:
                            original_pages_lines = json.load(f)
                            
                        # Flatten to list for difflib
                        orig_list = []
                        new_list = []
                        
                        all_pages = sorted(list(set(original_pages_lines.keys()).union(set(new_pages_lines.keys()))), key=lambda x: int(x.split('_')[1]) if '_' in x else 0)
                        for page in all_pages:
                            orig_list.extend(original_pages_lines.get(page, []))
                            new_list.extend(new_pages_lines.get(page, []))
                            
                        # add line breaks to list items for diff html readability
                        orig_list = [line + '\n' for line in orig_list]
                        new_list = [line + '\n' for line in new_list]
                            
                        diff_html = generate_diff_html(orig_list, new_list)
                        
                        report_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{original_hash}_tamper_report.html")
                        with open(report_path, 'w', encoding='utf-8') as f:
                            f.write(diff_html)
                        
                        print(f"[TAMPER LOCATOR] Saved mismatch report to {report_path}")
            except Exception as tampe_e:
                print(f"[TAMPER LOCATOR ERROR]: {tampe_e}")

            record['verified'] = "QUARANTINED"
            record['is_quarantined'] = True
            record['risk_reason'] = "Tampered – Integrity mismatch"
            
            print("[SECURITY ALERT] Tampering detected")
            
            uploader = record.get('uploader')
            block_user_if_tampered(uploader)
    
            return jsonify({
                "status": "QUARANTINED",
                "on_chain": False
            })
            
    else:
        return jsonify({
            "status": "Verification Failed – Not Stored On Blockchain",
            "on_chain": False
        })

    # LOG 5: Before returning response (Normal case)
    status = record['verified']
    print(f"FINAL STATUS: {status}")
    print("----------------------------------------")
    print("VERIFY REQUEST END")
    print("----------------------------------------")

    return jsonify({"status": status, "on_chain": exists_on_chain})



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin_unblock', methods=['POST'])
def admin_unblock():
    if 'user' not in session or session['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    file_hash = data.get('hash')

    record = None
    for upload in ALL_UPLOADS:
        if upload['hash'] == file_hash:
            record = upload
            break

    if not record:
        return jsonify({"error": "Record not found"}), 404

    # FILE LEVEL UNBLOCK
    record['verified'] = "Verified (Admin Override)"
    record['is_quarantined'] = False
    record['risk_reason'] = None

    # 🔥 USER LEVEL IPS RESET (VERY IMPORTANT)
    uploader = record.get('uploader')

    if uploader in SECURITY_MONITOR:
        SECURITY_MONITOR[uploader]['blocked'] = False
        SECURITY_MONITOR[uploader]['tamper_attempts'] = 0
        print(f"[IPS RESET] User {uploader} restored by admin")

    return jsonify({"success": True, "message": "File & User Unblocked"})

@app.route('/admin_unblock_user', methods=['POST'])
def admin_unblock_user():
    if 'user' not in session or session['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401

    username = request.json.get('username')

    if username in SECURITY_MONITOR:
        SECURITY_MONITOR[username]['blocked'] = False
        print(f"[ADMIN OVERRIDE] User {username} unblocked.")

    return jsonify({"success": True})



    return jsonify({"error": "User not found"}), 404

@app.route('/simulate_attack', methods=['POST'])
def simulate_attack():
    if 'user' not in session or session['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    file_hash = data.get('hash')
    
    record = None
    for upload in ALL_UPLOADS:
        if upload['hash'] == file_hash:
            record = upload
            break
            
    if not record:
        return jsonify({"error": "File not found"}), 404

    encrypted_filename = record.get('encrypted_filename')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], encrypted_filename)
    
    try:
        # Read - Decrypt - Modify - Encrypt - Save
        with open(file_path, 'rb') as f:
            encrypted_bytes = f.read()
            
        decrypted_bytes = cipher_suite.decrypt(encrypted_bytes)
        tampered_content = decrypted_bytes + b" [MALICIOUS INJECTION]"
        
        new_encrypted_data = cipher_suite.encrypt(tampered_content)
        
        with open(file_path, 'wb') as f:
            f.write(new_encrypted_data)
            
        # Update Verification Status in DB to reset UI
        record['verified'] = "Pending"
            
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Simulation Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/simulate_local_attack', methods=['POST'])
def simulate_local_attack():
    if 'user' not in session or session['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401

    try:
        file_hash = request.json.get('hash')
        print(f"[SIMULATION] Local Attack Requested for Hash: {file_hash}")

        for record in ALL_UPLOADS:
            if record['hash'] == file_hash:

                file_path = os.path.join(app.config['UPLOAD_FOLDER'], record['encrypted_filename'])
                print(f"[SIMULATION] Target Path: {file_path}")

                if os.path.exists(file_path):
                    # Corrupt the file by appending garbage bytes
                    with open(file_path, 'ab') as f:
                        f.write(b'ATTACK_GARBAGE_DATA')

                    record['simulate_local_attack'] = True
                    # Force re-verification
                    record['verified'] = "Pending" 
                    
                    print("[SIMULATION] Local encrypted file tampered successfully.")
                    return jsonify({"success": True})
                else:
                    print("[SIMULATION] Error: File path does not exist.")
                    return jsonify({"error": "File not found on server disk"}), 404

        print("[SIMULATION] Error: Record not found in ALL_UPLOADS.")
        return jsonify({"error": "Record not found"}), 404
        
    except Exception as e:
        print(f"[SIMULATION] Exception in Local Attack: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/simulate_cid_attack', methods=['POST'])
def simulate_cid_attack():
    if 'user' not in session or session['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401

    try:
        file_hash = request.json.get('hash')
        print(f"[SIMULATION] CID Attack Requested for Hash: {file_hash}")

        for record in ALL_UPLOADS:
            if record['hash'] == file_hash:
                record['simulate_cid_attack'] = True
                
                # Force re-verification status update so UI shows something changed? 
                # Or keep it pending until they click verify.
                record['verified'] = "Pending"
                
                print("[SIMULATION] CID reference tampered.")
                return jsonify({"success": True})

        print("[SIMULATION] Error: Record not found in ALL_UPLOADS.")
        return jsonify({"error": "Record not found"}), 404
        
    except Exception as e:
        print(f"[SIMULATION] Exception in CID Attack: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Record not found"}), 404

@app.route('/download/<file_hash>')
def download_file(file_hash):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user = session['user']
    
    init_security_profile(user)

    if is_user_blocked(session['user']):
        return jsonify({
            "error": "Access Blocked by Intrusion Prevention System"
        }), 403

    role = session.get('role')

    # 1. Lookup file record by hash
    record = None
    for upload in ALL_UPLOADS:
        if upload['hash'] == file_hash:
            record = upload
            break
            
    if not record:
        return jsonify({"error": "File record not found"}), 404

    # STEP 4: Download Protection
    if record.get('is_quarantined'):
        print("[ACCESS BLOCKED] Attempt to download quarantined file.")
        return jsonify({
            "error": "File is quarantined due to integrity mismatch. Admin review required."
        }), 403

    # 2. Access Control
    # Admin: Allow all. Employee: Allow only if uploader is self.
    if role == 'employee' and record['uploader'] != user:
        return jsonify({"error": "Forbidden: You do not have permission to access this file."}), 403

    encrypted_filename = record.get('encrypted_filename')
    original_filename = record.get('filename')

    if not encrypted_filename:
        return jsonify({"error": "File structure invalid (missing encryption mapping)"}), 500

    # 3. Read & Decrypt
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], encrypted_filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found on server"}), 404
        
    try:
        encrypted_bytes = None

        # Try IPFS first
        if record.get("cid"):
            encrypted_bytes = ipfs_get(record["cid"])
            if encrypted_bytes:
                print("Download source: IPFS")
            else:
                print("IPFS fetch failed. Falling back to local storage.")

        # Fallback to local
        if not encrypted_bytes:
            with open(file_path, 'rb') as f:
                encrypted_bytes = f.read()
            print("Download source: Local Storage")
            
        decrypted_bytes = cipher_suite.decrypt(encrypted_bytes)
        
        # 4. Serve
        return send_file(
            io.BytesIO(decrypted_bytes),
            as_attachment=True,
            download_name=original_filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        print(f"DECRYPTION FAILED: {str(e)}")
        # Return 400 as requested
        return "Invalid encryption key or corrupted file", 400

@app.route('/generateLineHashMap', methods=['POST'])
def generate_line_hash_map():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    file_hash = data.get('hash')
    
    # find record
    record = None
    for upload in ALL_UPLOADS:
        if upload['hash'] == file_hash:
            record = upload
            break
            
    if not record:
        return jsonify({"error": "File record not found"}), 404
        
    encrypted_filename = record.get('encrypted_filename')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], encrypted_filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
        
    try:
        with open(file_path, 'rb') as f:
            encrypted_bytes = f.read()
            
        # Try IPFS first if available
        if record.get("cid"):
            ipfs_bytes = ipfs_get(record["cid"])
            if ipfs_bytes:
                encrypted_bytes = ipfs_bytes
                print("LineHashMap Generation -> Download source: IPFS")

        decrypted_bytes = cipher_suite.decrypt(encrypted_bytes)
        
        from pdf_parser import extract_text_lines_from_pdf
        from hash_mapper import generate_line_hashes
        
        pages_lines = extract_text_lines_from_pdf(decrypted_bytes)
        line_hashes = generate_line_hashes(pages_lines)
        
        # save hash map
        hashmap_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_hash}_hashmap.json")
        with open(hashmap_path, 'w') as f:
            json.dump(line_hashes, f)
            
        # save original lines for diff
        lines_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_hash}_lines.json")
        with open(lines_path, 'w') as f:
            json.dump(pages_lines, f)
            
        print(f"[TAMPER ENGINE] Generated line hash map for {file_hash}")
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"[TAMPER ENGINE ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/simulate_content_tamper', methods=['POST'])
def simulate_content_tamper():
    if 'user' not in session or session['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    file_hash = data.get('hash')
    
    record = None
    for upload in ALL_UPLOADS:
        if upload['hash'] == file_hash:
            record = upload
            break
            
    if not record:
        return jsonify({"error": "Record not found"}), 404
        
    encrypted_filename = record.get('encrypted_filename')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], encrypted_filename)
    
    try:
        with open(file_path, 'rb') as f:
            encrypted_bytes = f.read()
            
        decrypted_bytes = cipher_suite.decrypt(encrypted_bytes)
        
        # Open with PyMuPDF
        import fitz
        doc = fitz.open(stream=decrypted_bytes, filetype="pdf")
        if len(doc) > 0:
            page = doc[0]
            
            # --- DYNAMIC ADD, MODIFY, AND DELETE ATTACK ---
            text = page.get_text("text")
            lines = [l.strip() for l in text.replace('\r', '').split('\n') if l.strip()]
            
            if len(lines) >= 3:
                # 1. DELETE: Redact the first line completely
                to_delete = lines[0]
                rects_del = page.search_for(to_delete)
                if rects_del:
                    for r in rects_del:
                        page.add_redact_annot(r)
                        
                # 2. MODIFY: Redact the second line and inject replacement text
                to_modify = lines[1]
                rects_mod = page.search_for(to_modify)
                if rects_mod:
                    for r in rects_mod:
                        page.add_redact_annot(r)
                        page.insert_text((r.x0, r.y0 + 12), "[MODIFIED] " + to_modify[:15] + "...", fontsize=11, color=(1, 0, 0))
                
                # Apply the deletions and modifications
                page.apply_redactions()
                
            # 3. ADD: Inject new text at the bottom
            page.insert_text((50, 600), "MALICIOUS PAYLOAD INJECTED!", fontsize=14, color=(1, 0, 0))
            
        tampered_bytes = doc.write()
        doc.close()
        
        # Re-encrypt
        new_encrypted_data = cipher_suite.encrypt(tampered_bytes)
        
        with open(file_path, 'wb') as f:
            f.write(new_encrypted_data)
            
        record['verified'] = "Pending"
        record['simulate_content_attack'] = True
        print(f"[SIMULATION] Smart Content Tamper applied for {file_hash}")
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"[SIMULATION ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/highlightTampering', methods=['GET'])
def highlight_tampering():
    if 'user' not in session:
        return "Unauthorized", 401
        
    file_hash = request.args.get('hash')
    if not file_hash:
        return "Missing hash", 400
        
    report_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_hash}_tamper_report.html")
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return "Tamper report not found. Please verify the report first to generate the diff.", 404

@app.route('/debug')
def debug_py():
    import sys
    return jsonify({
        "executable": sys.executable,
        "path": sys.path
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
