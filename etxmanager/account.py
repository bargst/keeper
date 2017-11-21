from web3 import eth
from flask import Flask, jsonify, request
import copy

#from web3.auto import w3
from web3 import Web3, IPCProvider
w3 = Web3(IPCProvider())
app = Flask(__name__)

accounts = {} 

@app.route("/account/")
def get_accounts():
    return jsonify([ addr for addr in accounts.keys()])

@app.route('/account/', methods=['POST'])
def add_account():
    address = ""

    req_json = request.get_json()
    if req_json and "address" in req_json:
        address = w3.toChecksumAddress(req_json["address"])
        accounts[address] = { "locked": True }
        accounts[address]["key_file"] = req_json

    return jsonify(address)

@app.route('/account/<account_id>')
def show_account(account_id):
    address = w3.toChecksumAddress(account_id)
    account = {}

    if address in accounts.keys():
        # Doing a deepcopy to avoid poping "private_key" ...
        account = copy.copy(accounts[address])
        if "key_file" in account:
            account.pop("key_file")
        if "private_key" in account:
            account.pop("private_key")
        
    return jsonify(account)

@app.route('/account/<account_id>', methods=['POST'])
def unlock(account_id):
    address = w3.toChecksumAddress(account_id)
    password = ""

    req_json = request.get_json()
    if req_json and "password" in req_json:
        password = req_json["password"]

    # Force Lock with empty password
    if not password:
        accounts[address]["private_key"] = ""
        accounts[address]["locked"] = True

    # Try to unlock key_file
    if address in accounts.keys() and password:
        try:
            accounts[address]["private_key"] = eth.Account.decrypt(accounts[address]["key_file"], password)
            accounts[address]["locked"] = False
        except :
            accounts[address]["private_key"] = ""
            accounts[address]["locked"] = True

    return show_account(account_id)

# >>> transaction = {
#        'to': '0xF0109fC8DF283027b6285cc889F5aA624EaC1F55',
#        'value': 1000000000,
#        'gas': 2000000,
#        'gasPrice': 234567897654321,
#        'nonce': 0,
#        'chainId': 1
#    }
@app.route('/account/<account_id>', methods=['PUT'])
def sign(account_id):
    address = w3.toChecksumAddress(account_id)
    transaction = {}
    key = ""
    rawTransaction = ""
    
    if address in accounts and "private_key" in accounts[address]:
        key = accounts[address]["private_key"]

    req_json = request.get_json()
    if key and (req_json
           and "to"        in req_json
           and "value"     in req_json
           and "gas"       in req_json
           and "gasPrice"  in req_json
           and "nonce"     in req_json
           and "chainId"   in req_json ):
        signed = eth.Account().signTransaction(req_json, key)
        rawTransaction = w3.toHex(signed.rawTransaction)


    return jsonify(rawTransaction)
