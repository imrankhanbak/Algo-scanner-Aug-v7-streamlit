#!/usr/bin/env python3
"""
Quick test script for PSX Algo v7 Streamlit app
"""

import sys
import importlib.util

def test_imports():
    """Test if all required packages are available"""
    required_packages = [
        'streamlit', 'pandas', 'numpy', 'plotly', 'requests', 'bs4'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'bs4':
                import bs4
            else:
                exec(f"import {package}")
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - MISSING")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install " + " ".join(missing_packages))
        return False
    else:
        print("\n✅ All required packages are available!")
        return True

def test_psx_api():
    """Test PSX API connectivity"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        print("\n🔍 Testing PSX API connectivity...")
        
        url = "https://dps.psx.com.pk/historical"
        form_data = {
            "symbol": "HBL",
            "year": "2025", 
            "month": "7"
        }
        
        response = requests.post(url, data=form_data, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            
            if table:
                rows = table.find_all('tr')[1:]  # Skip header
                if len(rows) > 0:
                    print(f"✅ PSX API working - Found {len(rows)} data rows for HBL")
                    return True
                else:
                    print("⚠️  PSX API responded but no data rows found")
                    return False
            else:
                print("⚠️  PSX API responded but no table found")
                return False
        else:
            print(f"❌ PSX API error - HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ PSX API test failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🧪 PSX Algo v7 Streamlit App Test")
    print("=" * 40)
    
    # Test imports
    imports_ok = test_imports()
    
    if not imports_ok:
        sys.exit(1)
    
    # Test PSX API
    api_ok = test_psx_api()
    
    print("\n" + "=" * 40)
    if imports_ok and api_ok:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ Ready to deploy to Streamlit Cloud!")
        print("\nTo run locally:")
        print("  streamlit run streamlit_app.py")
        print("\nTo deploy:")
        print("  1. Push to GitHub")
        print("  2. Visit share.streamlit.io")
        print("  3. Deploy from your repository")
    else:
        print("❌ Some tests failed. Please fix issues before deploying.")
        sys.exit(1)

if __name__ == "__main__":
    main()