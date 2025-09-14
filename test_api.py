#!/usr/bin/env python3
"""Test script for P1 Diff API."""

import json
import requests

def test_api():
    """Test the P1 Diff API with real repository data."""
    
    # Load test data
    with open('test_api_request.json') as f:
        data = json.load(f)
    
    print("🧪 Testing P1 Diff API...")
    print(f"Repository: {data['repo_url']}")
    print(f"Commits: {data['commit_good'][:8]} -> {data['commit_candidate'][:8]}")
    print()
    
    try:
        # Make API request
        response = requests.post('http://127.0.0.1:8000/diff', json=data, timeout=60)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Length: {len(response.text)} characters")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('ok'):
                print("✅ Success!")
                data_section = result['data']
                files = data_section['files']
                provenance = data_section['provenance']
                
                print(f"Files changed: {len(files)}")
                print(f"Omitted files: {data_section['omitted_files_count']}")
                print(f"Git version: {provenance['git_version']}")
                print(f"Checksum: {provenance['checksum']}")
                
                # Show file types
                statuses = {}
                for file in files:
                    status = file['status']
                    statuses[status] = statuses.get(status, 0) + 1
                print(f"File changes by type: {statuses}")
                
                # Save response to file for comparison
                with open('api_response.json', 'w') as f:
                    json.dump(result, f, indent=2)
                print("Response saved to api_response.json")
                
                # Compare with CLI output if available
                try:
                    with open('test_output.json') as f:
                        cli_result = json.load(f)
                    
                    if cli_result['data']['provenance']['checksum'] == provenance['checksum']:
                        print("✅ Checksum matches CLI output - API is deterministic!")
                    else:
                        print("⚠️  Checksum differs from CLI output")
                        
                except FileNotFoundError:
                    print("ℹ️  No CLI output file found for comparison")
                
            else:
                print("❌ Error in response")
                error = result.get('error', {})
                print(f"Error Code: {error.get('code')}")
                print(f"Error Message: {error.get('message')}")
                print(f"Error Details: {error.get('details')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text[:500])
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_api()
