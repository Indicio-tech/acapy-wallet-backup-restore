import asyncio
import datetime
import json
import os
import platform
import argparse
from getpass import getpass
import json
import logging

from indy import ledger, pool, wallet
from indy.error import IndyError, WalletAccessFailed

from ctypes import cdll, c_char_p

LOGGER = logging.getLogger(__name__)
"""
For testing purposes:
export ACAPY_WALLET_NAME="TestWallet"
export WALLET_KEY="MySecretKey"
export ACAPY_WALLET_STORAGE_TYPE="postgres_storage"
export WALLET_STORAGE_CONFIG='{"storage_type":"postgres_storage", "storage_config":{"url":"db:5432"}}'
export WALLET_STORAGE_CREDS='{"storage_credentials": {"account":"acapy","password":"acapy","admin_account":"acapy","admin_password":"acapy"}}'

# Use env vars for wallet name and key
python3 ./did-recovery.py backup
python3 ./did-recovery.py restore

#Override wallet name and key for sub wallets
python3 ./did-recovery.py backup -n UserWallet01 -k WalletSecretKey
python3 ./did-recovery.py restore -n MyWallet -k NewWalletSecretKey
"""

WALLET_NAME = os.environ['ACAPY_WALLET_NAME']
WALLET_KEY = os.environ['WALLET_KEY']
STORAGE_TYPE = os.environ['ACAPY_WALLET_STORAGE_TYPE']
STORAGE_CONFIG = os.environ['WALLET_STORAGE_CONFIG']
STORAGE_CREDENTIALS = os.environ['WALLET_STORAGE_CREDS']

EXTENSION = {"darwin": ".dylib", "linux": ".so", "win32": ".dll", 'windows': '.dll'}

def file_ext():
    your_platform = platform.system().lower()
    return EXTENSION[your_platform] if (your_platform in EXTENSION) else '.so'

async def load_postgres(storage_config, storage_creds):
    print("Initializing postgres wallet")
    stg_lib = cdll.LoadLibrary("libindystrgpostgres" + file_ext())
    result = stg_lib.postgresstorage_init()
    if result != 0:
        LOGGER.error("Error unable to load postgres wallet storage: %s", result)
        if raise_exc:
            raise OSError(f"Error unable to load postgres wallet storage: {result}")
        else:
            raise SystemExit(1)
    if "wallet_scheme" in storage_config:
        c_config = c_char_p(storage_config.encode("utf-8"))
        c_credentials = c_char_p(storage_creds.encode("utf-8"))
        result = stg_lib.init_storagetype(c_config, c_credentials)
        if result != 0:
            LOGGER.error("Error unable to configure postgres stg: %s", result)
            if raise_exc:
                raise OSError(f"Error unable to configure postgres stg: {result}")
            else:
                raise SystemExit(1)


async def restore(my_wallet_config, credentials):

    i = await wallet.delete_wallet(my_wallet_config, credentials)
    i = await wallet.import_wallet(my_wallet_config, credentials, '{"path":"./mount/dump.json","key":"default"}')

async def backup(my_wallet_config, credentials):

    my_wallet_handle = await wallet.open_wallet(my_wallet_config, credentials)
    e = await wallet.export_wallet(my_wallet_handle, '{"path":"./mount/dump.json","key":"default"}')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        help="Verbose Mode",
        action='store_true',
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    parser_backup = subparsers.add_parser("backup")
    parser_backup.add_argument(
        "-n",
        "--wallet-name",
        help="The name of the wallet to extract",
        default=WALLET_NAME,
    )
    parser_backup.add_argument(
        "-k",
        "--wallet-key",
        help="The secret key of the wallet",
        default=WALLET_KEY,
    )
    parser_restore = subparsers.add_parser("restore")
    parser_restore.add_argument(
        "-n",
        "--wallet-name",
        help="The name of the wallet to restore",
        default=WALLET_NAME,
    )
    parser_restore.add_argument(
        "-k",
        "--wallet-key",
        help="The secret key of the wallet",
        default=WALLET_KEY,
    )
    args = parser.parse_args()

    # if 'wallet_name' in args:
    #     args.wallet_name = json.loads(args.wallet_name)
    # if 'wallet_key' in args:
    #     args.wallet_key = json.loads(args.wallet_key)
    return args

async def main():
    args = parse_args()
    # print(args)
    # return
    await load_postgres(STORAGE_CONFIG, STORAGE_CREDENTIALS)

    wallet_config = json.dumps({
        "id": args.wallet_name,
        "storage_type": STORAGE_TYPE,
        "storage_config": json.loads(STORAGE_CONFIG),
    })
    wallet_credentials = json.dumps({
        "key": args.wallet_key,
        "storage_credentials": json.loads(STORAGE_CREDENTIALS),
    })

    if args.verbose:
        print(f"Arguments:")
        print(args)
        print(f"WalletConfig: {wallet_config}")
        print(f"WalletCredentials: {wallet_credentials}")

    if args.command == "backup":
        print(f"Backing up {args.wallet_name}")
        await backup(wallet_config, wallet_credentials)
        print(f"Successfully backed up {args.wallet_name}")
    elif args.command == "restore":
        print(f"Restoring {args.wallet_name}")
        await restore(wallet_config, wallet_credentials)
        print(f"Successfully restored {args.wallet_name}")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
