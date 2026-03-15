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
    source_dir = r"c:\Users\francisco\.gemini\antigravity\scratch\algo_trading_agent\Sindicato_Alpha_Nexus"
    target_dir = "strategies/Sindicato_Nexus"
    
    commit_sha, base_tree_sha = get_latest_commit()
    print(f"Latest commit: {commit_sha}")
    
    tree_data = []
    
    for root, _, files in os.walk(source_dir):
        if '__pycache__' in root:
            continue
        for file in files:
            filepath = os.path.join(root, file)
            # Skip big HTML reports to save space/time, models are okay
            if file.endswith('.html') and os.path.getsize(filepath) > 1024 * 1024 * 2:
                print(f"Skipping large HTML: {file}")
                continue
                
            rel_path = os.path.relpath(filepath, source_dir)
            # Replace backslashes for unix paths in git
            git_path = f"{target_dir}/{rel_path}".replace('\\', '/')
            
            blob_sha = create_blob(filepath)
            
            tree_data.append({
                'path': git_path,
                'mode': '100644',
                'type': 'blob',
                'sha': blob_sha
            })
            
    print(f"Created {len(tree_data)} blobs. Pushing tree...")
    new_tree_sha = create_tree(base_tree_sha, tree_data)
    
    print("Creating commit...")
    new_commit_sha = create_commit("feat: Incorporación de Agentes Multi-Modelo Sindicato Nexus", new_tree_sha, commit_sha)
    
    print("Updating reference...")
    update_ref(new_commit_sha)

if __name__ == '__main__':
    try:
        main()
        print("Upload COMPLETE.")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)
