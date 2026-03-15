import os
import base64
import requests
import sys

TOKEN = 'TU_TOKEN_AQUI' # Redactado por seguridad
REPO = 'garytest26-open/Openclaw-trading-system'
BRANCH = 'main'
BASE_URL = f'https://api.github.com/repos/{REPO}'
HEADERS = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

def get_latest_commit():
    r = requests.get(f'{BASE_URL}/git/refs/heads/{BRANCH}', headers=HEADERS)
    r.raise_for_status()
    commit_sha = r.json()['object']['sha']
    
    r2 = requests.get(f'{BASE_URL}/git/commits/{commit_sha}', headers=HEADERS)
    r2.raise_for_status()
    tree_sha = r2.json()['tree']['sha']
    return commit_sha, tree_sha

def create_blob(filepath):
    print(f"Creating blob for {filepath}...")
    with open(filepath, 'rb') as f:
        content = f.read()
    
    # Check if file has valid unicode characters to send it as text, otherwise base64
    try:
        content_str = content.decode('utf-8')
        r = requests.post(f'{BASE_URL}/git/blobs', headers=HEADERS, json={
            'content': content_str,
            'encoding': 'utf-8'
        })
    except UnicodeDecodeError:
        r = requests.post(f'{BASE_URL}/git/blobs', headers=HEADERS, json={
            'content': base64.b64encode(content).decode('ascii'),
            'encoding': 'base64'
        })
        
    r.raise_for_status()
    return r.json()['sha']

def create_tree(base_tree_sha, tree_data):
    r = requests.post(f'{BASE_URL}/git/trees', headers=HEADERS, json={
        'base_tree': base_tree_sha,
        'tree': tree_data
    })
    r.raise_for_status()
    return r.json()['sha']

def create_commit(message, tree_sha, parent_sha):
    r = requests.post(f'{BASE_URL}/git/commits', headers=HEADERS, json={
        'message': message,
        'tree': tree_sha,
        'parents': [parent_sha]
    })
    r.raise_for_status()
    return r.json()['sha']

def update_ref(commit_sha):
    r = requests.patch(f'{BASE_URL}/git/refs/heads/{BRANCH}', headers=HEADERS, json={
        'sha': commit_sha,
        'force': False
    })
    r.raise_for_status()
    print("Reference updated successfully!")

def main():
    base_dir = r"c:\Users\francisco\.gemini\antigravity\scratch\algo_trading_agent"
    
    files_to_upload = [
        "nexus_omega_strategy.py",
        "backtest_nexus_omega.py",
        "nexus_omega_rl_layer.py"
    ]
    
    target_dir = "strategies/Nexus_Omega"
    
    commit_sha, base_tree_sha = get_latest_commit()
    print(f"Latest commit: {commit_sha}")
    
    tree_data = []
    
    for filename in files_to_upload:
        filepath = os.path.join(base_dir, filename)
        if not os.path.exists(filepath):
            print(f"ERROR: File {filepath} not found!")
            continue
            
        git_path = f"{target_dir}/{filename}"
        
        blob_sha = create_blob(filepath)
        
        tree_data.append({
            'path': git_path,
            'mode': '100644',
            'type': 'blob',
            'sha': blob_sha
        })
            
    if not tree_data:
        print("No files to upload.")
        return
        
    print(f"Created {len(tree_data)} blobs. Pushing tree...")
    new_tree_sha = create_tree(base_tree_sha, tree_data)
    
    print("Creating commit...")
    new_commit_sha = create_commit("feat: Incorporación de Estrategia NEXUS OMEGA (8 Capas)", new_tree_sha, commit_sha)
    
    print("Updating reference...")
    update_ref(new_commit_sha)

if __name__ == '__main__':
    try:
        main()
        print("Upload COMPLETE.")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)
