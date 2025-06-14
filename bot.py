import aiohttp
import asyncio
import aiofiles
import json
import os
import sys

# ==================== BOT 1: Token Generator ====================
async def get_firebase_token(email, password):
    url = 'https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword'
    params = {
        'key': 'AIzaSyB0YXNLWl-mPWQNX-tvd7rp-HVNr_GhAmk'
    }
    payload = {
        'email': email,
        'password': password,
        'returnSecureToken': True,
        'clientType': 'CLIENT_TYPE_ANDROID'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json',
        'X-Android-Package': 'com.lumira_mobile',
        'X-Android-Cert': '1A1F179100AAF62649EAD01C6870FDE2510B1BC2',
        'Accept-Language': 'en-US',
        'X-Client-Version': 'Android/Fallback/X22003001/FirebaseCore-Android',
        'X-Firebase-GMPID': '1:599727959790:android:5c819be0c7e7e3057a4dff',
        'X-Firebase-Client': 'H4sIAAAAAAAAAKtWykhNLCpJSk0sKVayio7VUSpLLSrOzM9TslIyUqoFAFyivEQfAAAA'
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params, json=payload, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                return {
                    'email': data['email'],
                    'idToken': data['idToken']
                }
    except aiohttp.ClientResponseError as e:
        print(f"Error for {email}: {e.message}")
        return None
    except Exception as e:
        print(f"Error for {email}: {str(e)}")
        return None

async def process_accounts():
    try:
        # Read accounts from accounts.json
        async with aiofiles.open('accounts.json', mode='r') as file:
            content = await file.read()
            accounts = json.loads(content)

        all_tokens = []

        # Process each account to get Firebase tokens
        for account in accounts:
            token_data = await get_firebase_token(account['email'], account['password'])
            if token_data and token_data['idToken']:  # Ensure idToken is not empty
                all_tokens.append(token_data['idToken'])  # Only save idToken

        # Write tokens to tokens.txt
        if all_tokens:
            content = '\n'.join(all_tokens)  # Join tokens with newline
            async with aiofiles.open('tokens.txt', mode='w') as file:
                await file.write(content)
            print(f"\n{len(all_tokens)} tokens successfully saved to tokens.txt")
            return True
        else:
            print("No tokens were retrieved.")
            return False

    except FileNotFoundError:
        print("Error: 'accounts.json' not found.")
        return False
    except json.JSONDecodeError:
        print("Error: 'accounts.json' is not a valid JSON file.")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

# ==================== BOT 2: Mining Bot ====================
default_headers = {
    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
    'accept': '*/*',
    'accept-encoding': 'gzip',
    'host': 'api.airdroptoken.com'
}

API_ENDPOINTS = {
    'payouts': 'https://api.airdroptoken.com/airdrops/payouts',
    'miners': 'https://api.airdroptoken.com/miners/',
    'minerDetail': 'https://api.airdroptoken.com/miners/miner/'
}

async def get_tokens():
    try:
        with open('tokens.txt', 'r') as file:
            tokens = [line.strip() for line in file if line.strip()]
            return tokens
    except FileNotFoundError:
        print("Error: 'tokens.txt' not found. Create the file with one token per line.")
        return []
    except Exception as e:
        print(f"Error reading tokens: {e}")
        return []

async def make_api_request(endpoint, token):
    try:
        headers = {**default_headers, 'authorization': f'Bearer {token}'}
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers, timeout=30) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientResponseError as e:
        if e.status == 401:
            # Raise specific exception for 401 error
            raise Exception("API Error: 401 - Unauthorized")
        raise Exception(f"API Error: {e.status} - {e.message}")
    except asyncio.TimeoutError:
        raise Exception("Request timed out after 30 seconds")
    except Exception as e:
        raise Exception(f"Request failed: {str(e)}")

def print_banner(token_count):
    print(f"""
*********************************************
*     MULTI-ACCOUNT MIRA NETWORK MINING     *
*     recode by VYUGRAA                     *
*     https://github.com/vyugraa            *
*********************************************
*     (Running {token_count} accounts)                 *
*********************************************
""")

async def countdown(seconds):
    for i in range(seconds, 0, -1):
        print(f"NEXT CYCLE IN {i}s", end="\r")
        await asyncio.sleep(1)
    print(" " * 20, end="\r")  # Clear line

async def process_account(index, token):
    account_number = index + 1
    try:
        miner_data = await make_api_request(API_ENDPOINTS['minerDetail'], token)
        print(f"""
ACCOUNT #{account_number} STATUS 
Token: {token[:5]}...
Time Left: {miner_data.get('object', {}).get('mining_time_left', 0)}s
ADT/hour: {miner_data.get('object', {}).get('adt_per_hour', 0)}
""")

        # Background requests (fire-and-forget)
        asyncio.create_task(make_api_request(API_ENDPOINTS['payouts'], token))
        asyncio.create_task(make_api_request(API_ENDPOINTS['miners'], token))

    except Exception as e:
        print(f"""
ACCOUNT #{account_number} ERROR 
{str(e)}
""")
        if "401 - Unauthorized" in str(e):
            raise  # Re-raise the exception to trigger token refresh

async def start_mining():
    while True:  # Infinite loop to handle token refresh
        tokens = await get_tokens()
        if not tokens:
            print("No tokens found. Trying to generate new tokens...")
            success = await process_accounts()
            if not success:
                print("Failed to generate tokens. Waiting before retrying...")
                await asyncio.sleep(30)
                continue
            
            # Try to get tokens again after generation
            tokens = await get_tokens()
            if not tokens:
                print("Still no tokens available. Waiting before retrying...")
                await asyncio.sleep(30)
                continue

        print_banner(len(tokens))

        try:
            # Main mining loop
            while True:
                tasks = [process_account(i, token) for i, token in enumerate(tokens)]
                await asyncio.gather(*tasks)
                await countdown(30)
        except Exception as e:
            if "401 - Unauthorized" in str(e):
                print("\nDetected 401 Unauthorized error. Refreshing tokens...")
                # Delete old tokens file
                try:
                    os.remove('tokens.txt')
                except:
                    pass
                await asyncio.sleep(5)
                continue  # Will restart the outer loop to get new tokens
            else:
                print(f"\nUnexpected error: {str(e)}")
                await asyncio.sleep(30)

# ==================== MAIN FUNCTION ====================
async def main():
    try:
        # First generate tokens
        success = await process_accounts()
        if not success:
            print("Initial token generation failed. Exiting.")
            return
        
        # Then start mining
        await start_mining()
    except KeyboardInterrupt:
        print('\nStopping mining process...')
        sys.exit(0)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nStopping mining process...')
        sys.exit(0)
