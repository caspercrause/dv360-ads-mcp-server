#!/usr/bin/env python
"""Helper script to find your DV360 Partner ID"""

import os
import json
from dotenv import load_dotenv
from googleapiclient import discovery
from google.oauth2 import service_account

load_dotenv()

SERVICE_ACCOUNT_JSON = os.getenv('DV360_SERVICE_ACCOUNT')
DV360_API_SCOPES = ["https://www.googleapis.com/auth/display-video"]

print('🔍 Attempting to discover Partner ID...\n')

try:
    # Authenticate with DV360 API
    service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=DV360_API_SCOPES
    )

    service = discovery.build('displayvideo', 'v4', credentials=credentials)

    print('✅ DV360 API authenticated successfully')
    print()

    # Try to list partners (requires partner-level access)
    print('Attempting to list partners (may require special permissions)...')
    try:
        result = service.partners().list().execute()
        partners = result.get('partners', [])

        if partners:
            print(f'✅ Found {len(partners)} partner(s):')
            for partner in partners:
                print(f'   Partner ID: {partner.get("partnerId")}')
                print(f'   Name: {partner.get("displayName")}')
                print()
        else:
            print('⚠️  No partners found (may not have partner-level access)')
    except Exception as e:
        print(f'⚠️  Cannot list partners: {str(e)}')
        print('   (This is normal if you only have advertiser-level access)')

    print()
    print('='*60)
    print('WAYS TO FIND YOUR PARTNER ID:')
    print('='*60)
    print()
    print('1. From DV360 UI:')
    print('   • Go to: https://displayvideo.google.com/')
    print('   • Look at the URL after logging in')
    print('   • Format: https://displayvideo.google.com/ng_nav/p/[PARTNER_ID]/...')
    print()
    print('2. From advertiser ID (7697223550):')
    print('   • Advertisers belong to partners')
    print('   • Try testing with small partner IDs or contact your DV360 admin')
    print()
    print('3. Test the list_advertisers tool:')
    print('   • Once you have a partner ID, run:')
    print('   • list_advertisers(partner_id="YOUR_PARTNER_ID")')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
