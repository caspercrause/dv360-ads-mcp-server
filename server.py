"""
DV360 (Display & Video 360) MCP Server
FastMCP-based server for querying DV360 reporting data via Bid Manager API v2
"""

import logging
import os
import sys
import csv
import io
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from contextlib import closing
from urllib.request import urlopen

from fastmcp import FastMCP
from pydantic import Field
from google.oauth2 import service_account
from googleapiclient import discovery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("DV360 Reporting API")

# Constants
BID_MANAGER_API_NAME = "doubleclickbidmanager"
BID_MANAGER_API_VERSION = "v2"
BID_MANAGER_API_SCOPES = ["https://www.googleapis.com/auth/doubleclickbidmanager"]

DV360_API_NAME = "displayvideo"
DV360_API_VERSION = "v4"
DV360_API_SCOPES = ["https://www.googleapis.com/auth/display-video"]

SERVICE_ACCOUNT_JSON = os.getenv("DV360_SERVICE_ACCOUNT")
DEFAULT_PARTNER_ID = os.getenv("DV360_PARTNER_ID")

# Global service instances
_bid_manager_service = None
_dv360_service = None


def get_bid_manager_service():
    """
    Get or create the DV360 Bid Manager API service instance (for reporting).

    Returns:
        googleapiclient.discovery.Resource: Bid Manager API service instance

    Raises:
        ValueError: If service account credentials are not configured
    """
    global _bid_manager_service

    if _bid_manager_service is None:
        if not SERVICE_ACCOUNT_JSON:
            raise ValueError(
                "DV360_SERVICE_ACCOUNT environment variable not set. "
                "Please set it to your service account JSON credentials."
            )

        try:
            service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in DV360_SERVICE_ACCOUNT environment variable: {e}"
            )

        logger.info("Authenticating Bid Manager API with service account credentials")

        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=BID_MANAGER_API_SCOPES
        )

        _bid_manager_service = discovery.build(
            BID_MANAGER_API_NAME,
            BID_MANAGER_API_VERSION,
            credentials=credentials
        )

        logger.info("Bid Manager API service initialized successfully")

    return _bid_manager_service


def get_dv360_service():
    """
    Get or create the Display & Video 360 API service instance (for entity management).

    Returns:
        googleapiclient.discovery.Resource: DV360 API service instance

    Raises:
        ValueError: If service account credentials are not configured
    """
    global _dv360_service

    if _dv360_service is None:
        if not SERVICE_ACCOUNT_JSON:
            raise ValueError(
                "DV360_SERVICE_ACCOUNT environment variable not set. "
                "Please set it to your service account JSON credentials."
            )

        try:
            service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in DV360_SERVICE_ACCOUNT environment variable: {e}"
            )

        logger.info("Authenticating DV360 API with service account credentials")

        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=DV360_API_SCOPES
        )

        _dv360_service = discovery.build(
            DV360_API_NAME,
            DV360_API_VERSION,
            credentials=credentials
        )

        logger.info("DV360 API service initialized successfully")

    return _dv360_service


# Backward compatibility
def get_service():
    """Alias for get_bid_manager_service() for backward compatibility."""
    return get_bid_manager_service()


def download_csv_from_gcs(gcs_path: str) -> str:
    """
    Download CSV file from Google Cloud Storage.

    Args:
        gcs_path: Google Cloud Storage path to the CSV file

    Returns:
        str: CSV content as string
    """
    logger.info(f"Downloading report from: {gcs_path}")
    with closing(urlopen(gcs_path)) as url:
        content = url.read().decode('utf-8')
    logger.info(f"Report downloaded successfully ({len(content)} bytes)")
    return content


def parse_csv_to_json(csv_content: str) -> List[Dict[str, Any]]:
    """
    Parse CSV content into JSON-friendly list of dictionaries.

    Args:
        csv_content: CSV file content as string

    Returns:
        List[Dict]: Parsed data as list of dictionaries
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    data = []

    for row in reader:
        # Convert numeric strings to appropriate types
        parsed_row = {}
        for key, value in row.items():
            if value is None or value == '':
                parsed_row[key] = None
            elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                # Try to convert to number
                try:
                    parsed_row[key] = int(value) if '.' not in value else float(value)
                except ValueError:
                    parsed_row[key] = value
            else:
                parsed_row[key] = value
        data.append(parsed_row)

    logger.info(f"Parsed {len(data)} rows from CSV")
    return data


def format_date_for_api(date_str: str) -> Dict[str, str]:
    """
    Convert YYYY-MM-DD date string to API format.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Dict with year, month, day keys
    """
    year, month, day = date_str.split('-')
    return {
        'year': year,
        'month': month,
        'day': day
    }


def prepare_filters(
    advertiser_ids: Optional[Union[List[str], str]] = None,
    campaign_ids: Optional[Union[List[str], str]] = None,
    insertion_order_ids: Optional[Union[List[str], str]] = None,
    line_item_ids: Optional[Union[List[str], str]] = None
) -> List[Dict[str, str]]:
    """
    Prepare filter list from various ID parameters.

    Args:
        advertiser_ids: Advertiser ID(s) to filter by
        campaign_ids: Campaign ID(s) to filter by
        insertion_order_ids: Insertion Order ID(s) to filter by
        line_item_ids: Line Item ID(s) to filter by

    Returns:
        List of filter dictionaries
    """
    filters = []

    # Handle advertiser IDs
    if advertiser_ids:
        if isinstance(advertiser_ids, str):
            advertiser_ids = [id.strip() for id in advertiser_ids.split(',')]
        for adv_id in advertiser_ids:
            filters.append({"type": "FILTER_ADVERTISER", "value": adv_id})

    # Handle campaign IDs
    if campaign_ids:
        if isinstance(campaign_ids, str):
            campaign_ids = [id.strip() for id in campaign_ids.split(',')]
        for camp_id in campaign_ids:
            filters.append({"type": "FILTER_MEDIA_PLAN", "value": camp_id})

    # Handle insertion order IDs
    if insertion_order_ids:
        if isinstance(insertion_order_ids, str):
            insertion_order_ids = [id.strip() for id in insertion_order_ids.split(',')]
        for io_id in insertion_order_ids:
            filters.append({"type": "FILTER_INSERTION_ORDER", "value": io_id})

    # Handle line item IDs
    if line_item_ids:
        if isinstance(line_item_ids, str):
            line_item_ids = [id.strip() for id in line_item_ids.split(',')]
        for li_id in line_item_ids:
            filters.append({"type": "FILTER_LINE_ITEM", "value": li_id})

    return filters


def prepare_dimensions_and_metrics(
    dimensions: Union[List[str], str],
    metrics: Union[List[str], str]
) -> tuple[List[str], List[str]]:
    """
    Prepare dimensions and metrics lists from flexible input.

    Args:
        dimensions: Dimensions as list or comma-separated string
        metrics: Metrics as list or comma-separated string

    Returns:
        Tuple of (dimensions_list, metrics_list)
    """
    # Handle dimensions
    if isinstance(dimensions, str):
        dimensions = [d.strip() for d in dimensions.split(',')]

    # Handle metrics
    if isinstance(metrics, str):
        metrics = [m.strip() for m in metrics.split(',')]

    return dimensions, metrics


@mcp.tool()
def dv_list_advertisers(
    partner_id: Optional[str] = Field(default=None, description="Partner ID (optional if DV360_PARTNER_ID is set in .env)"),
    page_size: int = Field(default=100, description="Number of advertisers to return per page (max 100)"),
    order_by: Optional[str] = Field(default=None, description="Field to order by (e.g., 'displayName', 'advertiserId')")
) -> Dict[str, Any]:
    """
    List all advertisers accessible under a partner.

    This uses the Display & Video 360 API v4 to list advertisers programmatically.
    If partner_id is not provided, it will use DV360_PARTNER_ID from your .env file.

    **How to find your partner ID:**
    - Log into DV360 UI
    - Look at the URL: https://displayvideo.google.com/ng_nav/p/[PARTNER_ID]/...
    - Or set it in your .env file as DV360_PARTNER_ID=1465151954

    Args:
        partner_id: The partner ID under which to list advertisers (optional if set in .env)
        page_size: Number of advertisers per page (default: 100, max: 100)
        order_by: Optional field to order results by

    Returns:
        Dictionary containing:
        - advertisers: List of advertiser objects with id, displayName, entityStatus, etc.
        - count: Number of advertisers returned
        - partner_id: The partner ID queried

    Example:
        list_advertisers()  # Uses DV360_PARTNER_ID from .env
        list_advertisers(partner_id="123456")  # Override with specific partner
    """
    try:
        # Use provided partner_id or fall back to environment variable
        if partner_id is None:
            partner_id = DEFAULT_PARTNER_ID
            if partner_id is None:
                return {
                    "success": False,
                    "error": "No partner_id provided and DV360_PARTNER_ID not set in .env file",
                    "message": "Either provide partner_id parameter or set DV360_PARTNER_ID in your .env file"
                }

        service = get_dv360_service()

        logger.info(f"Listing advertisers for partner {partner_id}...")

        # Build request parameters
        params = {
            'partnerId': partner_id,
            'pageSize': min(page_size, 100)  # API max is 100
        }

        if order_by:
            params['orderBy'] = order_by

        # Make API call
        result = service.advertisers().list(**params).execute()

        advertisers = result.get('advertisers', [])

        logger.info(f"Found {len(advertisers)} advertisers")

        # Format response
        formatted_advertisers = []
        for adv in advertisers:
            formatted_advertisers.append({
                'advertiser_id': adv.get('advertiserId'),
                'advertiser_name': adv.get('displayName'),
                'partner_id': adv.get('partnerId'),
                'entity_status': adv.get('entityStatus'),
                'update_time': adv.get('updateTime')
            })

        return {
            "success": True,
            "advertisers": formatted_advertisers,
            "count": len(formatted_advertisers),
            "partner_id": partner_id,
            "next_page_token": result.get('nextPageToken')
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error listing advertisers: {error_msg}", exc_info=True)

        # Provide helpful error messages
        if 'permission' in error_msg.lower() or '403' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": "Permission denied. Ensure your service account has Display & Video 360 API access and is linked to the partner account."
            }
        elif 'not found' in error_msg.lower() or '404' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": f"Partner ID {partner_id} not found. Double-check the partner ID."
            }
        else:
            return {
                "success": False,
                "error": error_msg
            }


@mcp.tool()
def dv_list_campaigns(
    advertiser_id: str = Field(..., description="Advertiser ID under which to list campaigns"),
    page_size: int = Field(default=100, description="Number of campaigns to return per page (max 100)"),
    filter: Optional[str] = Field(default=None, description="Filter expression to filter campaigns (e.g., 'entityStatus=\"ENTITY_STATUS_ACTIVE\"')"),
    order_by: Optional[str] = Field(default=None, description="Field to order by (e.g., 'displayName', 'campaignId')")
) -> Dict[str, Any]:
    """
    List all campaigns for an advertiser with optional filtering and ordering.

    Use this to retrieve campaign details that can be used for performance reporting.
    Supports filtering by entity status, date ranges, and other campaign properties.

    **Filter Examples:**
    - entityStatus="ENTITY_STATUS_ACTIVE"
    - entityStatus="ENTITY_STATUS_PAUSED"
    - updateTime>"2025-01-01T00:00:00Z"

    **Order By Examples:**
    - displayName
    - campaignId
    - updateTime desc

    Args:
        advertiser_id: The advertiser ID under which to list campaigns (required)
        page_size: Number of campaigns per page (default: 100, max: 100)
        filter: Optional filter expression to narrow results
        order_by: Optional field name to order results by

    Returns:
        Dictionary containing:
        - campaigns: List of campaign objects with id, displayName, budget, dates, etc.
        - count: Number of campaigns returned
        - advertiser_id: The advertiser ID queried

    Example:
        list_campaigns(advertiser_id="123456", filter='entityStatus="ENTITY_STATUS_ACTIVE"')
    """
    try:
        service = get_dv360_service()

        logger.info(f"Listing campaigns for advertiser {advertiser_id}...")

        # Build request parameters
        params = {
            'advertiserId': advertiser_id,
            'pageSize': min(page_size, 100)  # API max is 100
        }

        if filter:
            params['filter'] = filter

        if order_by:
            params['orderBy'] = order_by

        # Make API call
        result = service.advertisers().campaigns().list(**params).execute()

        campaigns = result.get('campaigns', [])

        logger.info(f"Found {len(campaigns)} campaigns")

        # Format response
        formatted_campaigns = []
        for camp in campaigns:
            formatted_campaigns.append({
                'campaign_id': camp.get('campaignId'),
                'campaign_name': camp.get('displayName'),
                'advertiser_id': camp.get('advertiserId'),
                'entity_status': camp.get('entityStatus'),
                'update_time': camp.get('updateTime'),
                'campaign_goal': camp.get('campaignGoal', {}),
                'campaign_flight': camp.get('campaignFlight', {}),
                'frequency_cap': camp.get('frequencyCap', {})
            })

        return {
            "success": True,
            "campaigns": formatted_campaigns,
            "count": len(formatted_campaigns),
            "advertiser_id": advertiser_id,
            "next_page_token": result.get('nextPageToken')
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error listing campaigns: {error_msg}", exc_info=True)

        if 'permission' in error_msg.lower() or '403' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": "Permission denied. Ensure your service account has access to this advertiser."
            }
        elif 'not found' in error_msg.lower() or '404' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": f"Advertiser ID {advertiser_id} not found."
            }
        else:
            return {
                "success": False,
                "error": error_msg
            }


@mcp.tool()
def dv_get_campaign(
    advertiser_id: str = Field(..., description="Advertiser ID"),
    campaign_id: str = Field(..., description="Campaign ID to retrieve")
) -> Dict[str, Any]:
    """
    Get detailed information about a specific campaign.

    Use this to retrieve full campaign details including budget, flight dates,
    frequency caps, and other settings needed for performance analysis.

    Args:
        advertiser_id: The advertiser ID that owns the campaign
        campaign_id: The campaign ID to retrieve

    Returns:
        Dictionary containing complete campaign details including:
        - campaign_id, campaign_name
        - entity_status, update_time
        - campaign_goal (type and performance goal)
        - campaign_flight (start/end dates)
        - frequency_cap settings
        - And all other campaign properties

    Example:
        get_campaign(advertiser_id="123456", campaign_id="789012")
    """
    try:
        service = get_dv360_service()

        logger.info(f"Fetching campaign {campaign_id} for advertiser {advertiser_id}...")

        # Make API call
        campaign = service.advertisers().campaigns().get(
            advertiserId=advertiser_id,
            campaignId=campaign_id
        ).execute()

        logger.info(f"Successfully retrieved campaign: {campaign.get('displayName')}")

        return {
            "success": True,
            "campaign": campaign
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting campaign: {error_msg}", exc_info=True)

        if 'permission' in error_msg.lower() or '403' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": "Permission denied. Ensure your service account has access to this campaign."
            }
        elif 'not found' in error_msg.lower() or '404' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": f"Campaign {campaign_id} not found for advertiser {advertiser_id}."
            }
        else:
            return {
                "success": False,
                "error": error_msg
            }


@mcp.tool()
def dv_list_insertion_orders(
    advertiser_id: str = Field(..., description="Advertiser ID under which to list insertion orders"),
    page_size: int = Field(default=100, description="Number of insertion orders to return per page (max 100)"),
    filter: Optional[str] = Field(default=None, description="Filter expression to filter insertion orders (e.g., 'entityStatus=\"ENTITY_STATUS_ACTIVE\"')"),
    order_by: Optional[str] = Field(default=None, description="Field to order by (e.g., 'displayName', 'insertionOrderId')")
) -> Dict[str, Any]:
    """
    List all insertion orders for an advertiser with optional filtering and ordering.

    Use this to retrieve insertion order details for performance reporting.
    Supports filtering by entity status, budget settings, and other properties.

    **Filter Examples:**
    - entityStatus="ENTITY_STATUS_ACTIVE"
    - entityStatus="ENTITY_STATUS_PAUSED"
    - updateTime>"2025-01-01T00:00:00Z"

    **Order By Examples:**
    - displayName
    - insertionOrderId
    - updateTime desc

    Args:
        advertiser_id: The advertiser ID under which to list insertion orders (required)
        page_size: Number of insertion orders per page (default: 100, max: 100)
        filter: Optional filter expression to narrow results
        order_by: Optional field name to order results by

    Returns:
        Dictionary containing:
        - insertion_orders: List of insertion order objects
        - count: Number of insertion orders returned
        - advertiser_id: The advertiser ID queried

    Example:
        list_insertion_orders(advertiser_id="123456", filter='entityStatus="ENTITY_STATUS_ACTIVE"')
    """
    try:
        service = get_dv360_service()

        logger.info(f"Listing insertion orders for advertiser {advertiser_id}...")

        # Build request parameters
        params = {
            'advertiserId': advertiser_id,
            'pageSize': min(page_size, 100)  # API max is 100
        }

        if filter:
            params['filter'] = filter

        if order_by:
            params['orderBy'] = order_by

        # Make API call
        result = service.advertisers().insertionOrders().list(**params).execute()

        insertion_orders = result.get('insertionOrders', [])

        logger.info(f"Found {len(insertion_orders)} insertion orders")

        # Format response
        formatted_ios = []
        for io in insertion_orders:
            formatted_ios.append({
                'insertion_order_id': io.get('insertionOrderId'),
                'insertion_order_name': io.get('displayName'),
                'advertiser_id': io.get('advertiserId'),
                'campaign_id': io.get('campaignId'),
                'entity_status': io.get('entityStatus'),
                'update_time': io.get('updateTime'),
                'pacing': io.get('pacing', {}),
                'frequency_cap': io.get('frequencyCap', {}),
                'budget': io.get('budget', {}),
                'insertion_order_type': io.get('insertionOrderType')
            })

        return {
            "success": True,
            "insertion_orders": formatted_ios,
            "count": len(formatted_ios),
            "advertiser_id": advertiser_id,
            "next_page_token": result.get('nextPageToken')
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error listing insertion orders: {error_msg}", exc_info=True)

        if 'permission' in error_msg.lower() or '403' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": "Permission denied. Ensure your service account has access to this advertiser."
            }
        elif 'not found' in error_msg.lower() or '404' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": f"Advertiser ID {advertiser_id} not found."
            }
        else:
            return {
                "success": False,
                "error": error_msg
            }


@mcp.tool()
def dv_get_insertion_order(
    advertiser_id: str = Field(..., description="Advertiser ID"),
    insertion_order_id: str = Field(..., description="Insertion Order ID to retrieve")
) -> Dict[str, Any]:
    """
    Get detailed information about a specific insertion order.

    Use this to retrieve full insertion order details including budget, pacing,
    frequency caps, and other settings needed for performance analysis.

    Args:
        advertiser_id: The advertiser ID that owns the insertion order
        insertion_order_id: The insertion order ID to retrieve

    Returns:
        Dictionary containing complete insertion order details including:
        - insertion_order_id, insertion_order_name
        - campaign_id, entity_status
        - pacing settings
        - budget settings
        - frequency_cap settings
        - And all other insertion order properties

    Example:
        get_insertion_order(advertiser_id="123456", insertion_order_id="789012")
    """
    try:
        service = get_dv360_service()

        logger.info(f"Fetching insertion order {insertion_order_id} for advertiser {advertiser_id}...")

        # Make API call
        insertion_order = service.advertisers().insertionOrders().get(
            advertiserId=advertiser_id,
            insertionOrderId=insertion_order_id
        ).execute()

        logger.info(f"Successfully retrieved insertion order: {insertion_order.get('displayName')}")

        return {
            "success": True,
            "insertion_order": insertion_order
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting insertion order: {error_msg}", exc_info=True)

        if 'permission' in error_msg.lower() or '403' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": "Permission denied. Ensure your service account has access to this insertion order."
            }
        elif 'not found' in error_msg.lower() or '404' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": f"Insertion order {insertion_order_id} not found for advertiser {advertiser_id}."
            }
        else:
            return {
                "success": False,
                "error": error_msg
            }


@mcp.tool()
def dv_list_line_items(
    advertiser_id: str = Field(..., description="Advertiser ID under which to list line items"),
    page_size: int = Field(default=100, description="Number of line items to return per page (max 100)"),
    filter: Optional[str] = Field(default=None, description="Filter expression to filter line items (e.g., 'entityStatus=\"ENTITY_STATUS_ACTIVE\"')"),
    order_by: Optional[str] = Field(default=None, description="Field to order by (e.g., 'displayName', 'lineItemId')")
) -> Dict[str, Any]:
    """
    List all line items for an advertiser with optional filtering and ordering.

    Line items contain the targeting settings (age, gender, audiences, etc.) and 
    are where age-based naming conventions are typically found.

    Use this to retrieve line item details for performance reporting and targeting analysis.
    Supports filtering by entity status, line item type, and other properties.

    **Filter Examples:**
    - entityStatus="ENTITY_STATUS_ACTIVE"
    - entityStatus="ENTITY_STATUS_PAUSED"
    - lineItemType="LINE_ITEM_TYPE_DISPLAY_DEFAULT"
    - updateTime>"2025-01-01T00:00:00Z"

    **Order By Examples:**
    - displayName
    - lineItemId
    - updateTime desc

    Args:
        advertiser_id: The advertiser ID under which to list line items (required)
        page_size: Number of line items per page (default: 100, max: 100)
        filter: Optional filter expression to narrow results
        order_by: Optional field name to order results by

    Returns:
        Dictionary containing:
        - line_items: List of line item objects with id, displayName, targeting, budget, etc.
        - count: Number of line items returned
        - advertiser_id: The advertiser ID queried

    Example:
        list_line_items(advertiser_id="123456", filter='entityStatus="ENTITY_STATUS_ACTIVE"')
    """
    try:
        service = get_dv360_service()

        logger.info(f"Listing line items for advertiser {advertiser_id}...")

        # Build request parameters
        params = {
            'advertiserId': advertiser_id,
            'pageSize': min(page_size, 100)  # API max is 100
        }

        if filter:
            params['filter'] = filter

        if order_by:
            params['orderBy'] = order_by

        # Make API call
        result = service.advertisers().lineItems().list(**params).execute()

        line_items = result.get('lineItems', [])

        logger.info(f"Found {len(line_items)} line items")

        # Format response
        formatted_line_items = []
        for li in line_items:
            formatted_line_items.append({
                'line_item_id': li.get('lineItemId'),
                'line_item_name': li.get('displayName'),
                'advertiser_id': li.get('advertiserId'),
                'campaign_id': li.get('campaignId'),
                'insertion_order_id': li.get('insertionOrderId'),
                'entity_status': li.get('entityStatus'),
                'line_item_type': li.get('lineItemType'),
                'update_time': li.get('updateTime'),
                'flight': li.get('flight', {}),
                'budget': li.get('budget', {}),
                'pacing': li.get('pacing', {}),
                'frequency_cap': li.get('frequencyCap', {}),
                'bid_strategy': li.get('bidStrategy', {})
            })

        return {
            "success": True,
            "line_items": formatted_line_items,
            "count": len(formatted_line_items),
            "advertiser_id": advertiser_id,
            "next_page_token": result.get('nextPageToken')
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error listing line items: {error_msg}", exc_info=True)

        if 'permission' in error_msg.lower() or '403' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": "Permission denied. Ensure your service account has access to this advertiser."
            }
        elif 'not found' in error_msg.lower() or '404' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": f"Advertiser ID {advertiser_id} not found."
            }
        else:
            return {
                "success": False,
                "error": error_msg
            }


@mcp.tool()
def dv_get_line_item(
    advertiser_id: str = Field(..., description="Advertiser ID"),
    line_item_id: str = Field(..., description="Line Item ID to retrieve")
) -> Dict[str, Any]:
    """
    Get detailed information about a specific line item including targeting settings.

    Use this to retrieve full line item details including targeting (age, gender, 
    audiences), budget, pacing, bid strategy, and other settings.

    Args:
        advertiser_id: The advertiser ID that owns the line item
        line_item_id: The line item ID to retrieve

    Returns:
        Dictionary containing complete line item details including:
        - line_item_id, line_item_name
        - campaign_id, insertion_order_id
        - entity_status, line_item_type
        - flight dates
        - budget and pacing settings
        - bid_strategy
        - targeting_expansion
        - And all other line item properties

    Example:
        get_line_item(advertiser_id="123456", line_item_id="789012")
    """
    try:
        service = get_dv360_service()

        logger.info(f"Fetching line item {line_item_id} for advertiser {advertiser_id}...")

        # Make API call
        line_item = service.advertisers().lineItems().get(
            advertiserId=advertiser_id,
            lineItemId=line_item_id
        ).execute()

        logger.info(f"Successfully retrieved line item: {line_item.get('displayName')}")

        return {
            "success": True,
            "line_item": line_item
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting line item: {error_msg}", exc_info=True)

        if 'permission' in error_msg.lower() or '403' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": "Permission denied. Ensure your service account has access to this line item."
            }
        elif 'not found' in error_msg.lower() or '404' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": f"Line item {line_item_id} not found for advertiser {advertiser_id}."
            }
        else:
            return {
                "success": False,
                "error": error_msg
            }


@mcp.tool()
def dv_list_creatives(
    advertiser_id: str = Field(..., description="Advertiser ID under which to list creatives"),
    page_size: int = Field(default=100, description="Number of creatives to return per page (max 100)"),
    filter: Optional[str] = Field(default=None, description="Filter expression to filter creatives (e.g., 'entityStatus=\"ENTITY_STATUS_ACTIVE\"')"),
    order_by: Optional[str] = Field(default=None, description="Field to order by (e.g., 'displayName', 'creativeId')")
) -> Dict[str, Any]:
    """
    List all creatives for an advertiser with optional filtering and ordering.

    Use this to retrieve creative details for performance reporting.
    Supports filtering by entity status, creative type, and other properties.

    **Filter Examples:**
    - entityStatus="ENTITY_STATUS_ACTIVE"
    - entityStatus="ENTITY_STATUS_ARCHIVED"
    - creativeType="CREATIVE_TYPE_STANDARD"
    - updateTime>"2025-01-01T00:00:00Z"

    **Order By Examples:**
    - displayName
    - creativeId
    - updateTime desc

    Args:
        advertiser_id: The advertiser ID under which to list creatives (required)
        page_size: Number of creatives per page (default: 100, max: 100)
        filter: Optional filter expression to narrow results
        order_by: Optional field name to order results by

    Returns:
        Dictionary containing:
        - creatives: List of creative objects
        - count: Number of creatives returned
        - advertiser_id: The advertiser ID queried

    Example:
        list_creatives(advertiser_id="123456", filter='entityStatus="ENTITY_STATUS_ACTIVE"')
    """
    try:
        service = get_dv360_service()

        logger.info(f"Listing creatives for advertiser {advertiser_id}...")

        # Build request parameters
        params = {
            'advertiserId': advertiser_id,
            'pageSize': min(page_size, 100)  # API max is 100
        }

        if filter:
            params['filter'] = filter

        if order_by:
            params['orderBy'] = order_by

        # Make API call
        result = service.advertisers().creatives().list(**params).execute()

        creatives = result.get('creatives', [])

        logger.info(f"Found {len(creatives)} creatives")

        # Format response
        formatted_creatives = []
        for creative in creatives:
            formatted_creatives.append({
                'creative_id': creative.get('creativeId'),
                'creative_name': creative.get('displayName'),
                'advertiser_id': creative.get('advertiserId'),
                'creative_type': creative.get('creativeType'),
                'entity_status': creative.get('entityStatus'),
                'update_time': creative.get('updateTime'),
                'dimensions': creative.get('dimensions', {}),
                'creative_attributes': creative.get('creativeAttributes', []),
                'hosting_source': creative.get('hostingSource')
            })

        return {
            "success": True,
            "creatives": formatted_creatives,
            "count": len(formatted_creatives),
            "advertiser_id": advertiser_id,
            "next_page_token": result.get('nextPageToken')
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error listing creatives: {error_msg}", exc_info=True)

        if 'permission' in error_msg.lower() or '403' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": "Permission denied. Ensure your service account has access to this advertiser."
            }
        elif 'not found' in error_msg.lower() or '404' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": f"Advertiser ID {advertiser_id} not found."
            }
        else:
            return {
                "success": False,
                "error": error_msg
            }


@mcp.tool()
def dv_get_creative(
    advertiser_id: str = Field(..., description="Advertiser ID"),
    creative_id: str = Field(..., description="Creative ID to retrieve")
) -> Dict[str, Any]:
    """
    Get detailed information about a specific creative.

    Use this to retrieve full creative details including assets, dimensions,
    creative attributes, and other properties needed for performance analysis.

    Args:
        advertiser_id: The advertiser ID that owns the creative
        creative_id: The creative ID to retrieve

    Returns:
        Dictionary containing complete creative details including:
        - creative_id, creative_name
        - creative_type, entity_status
        - dimensions (width, height)
        - creative_attributes
        - assets information
        - And all other creative properties

    Example:
        get_creative(advertiser_id="123456", creative_id="789012")
    """
    try:
        service = get_dv360_service()

        logger.info(f"Fetching creative {creative_id} for advertiser {advertiser_id}...")

        # Make API call
        creative = service.advertisers().creatives().get(
            advertiserId=advertiser_id,
            creativeId=creative_id
        ).execute()

        logger.info(f"Successfully retrieved creative: {creative.get('displayName')}")

        return {
            "success": True,
            "creative": creative
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting creative: {error_msg}", exc_info=True)

        if 'permission' in error_msg.lower() or '403' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": "Permission denied. Ensure your service account has access to this creative."
            }
        elif 'not found' in error_msg.lower() or '404' in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": f"Creative {creative_id} not found for advertiser {advertiser_id}."
            }
        else:
            return {
                "success": False,
                "error": error_msg
            }


@mcp.tool()
def dv_run_report(
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format (e.g., '2025-01-01')"),
    end_date: str = Field(..., description="End date in YYYY-MM-DD format (e.g., '2025-01-31')"),
    dimensions: Union[List[str], str] = Field(..., description="Dimensions to group by (list or comma-separated string)"),
    metrics: Union[List[str], str] = Field(..., description="Metrics to retrieve (list or comma-separated string)"),
    advertiser_ids: Optional[Union[List[str], str]] = Field(default=None, description="Advertiser ID(s) to filter by"),
    campaign_ids: Optional[Union[List[str], str]] = Field(default=None, description="Campaign ID(s) to filter by"),
    insertion_order_ids: Optional[Union[List[str], str]] = Field(default=None, description="Insertion Order ID(s) to filter by"),
    line_item_ids: Optional[Union[List[str], str]] = Field(default=None, description="Line Item ID(s) to filter by"),
    report_name: str = Field(default="MCP Report", description="Name for the report")
) -> Dict[str, Any]:
    """
    Run a DV360 report and return results as JSON.

    This tool creates a query, runs it synchronously, downloads the CSV,
    parses it to JSON, and returns the data. No CSV files are left behind.

    **Available Dimensions** (groupBys):
    
    **Entity Dimensions:**
    - FILTER_DATE: Date
    - FILTER_ADVERTISER: Advertiser ID
    - FILTER_ADVERTISER_NAME: Advertiser Name
    - FILTER_MEDIA_PLAN: Campaign ID
    - FILTER_MEDIA_PLAN_NAME: Campaign Name
    - FILTER_INSERTION_ORDER: Insertion Order ID
    - FILTER_INSERTION_ORDER_NAME: Insertion Order Name
    - FILTER_LINE_ITEM: Line Item ID
    - FILTER_LINE_ITEM_NAME: Line Item Name
    - FILTER_CREATIVE: Creative ID
    - FILTER_CREATIVE_TYPE: Creative Type
    
    **Floodlight Conversion Dimensions (CRITICAL for conversion tracking):**
    - FILTER_FLOODLIGHT_ACTIVITY_ID: Floodlight Activity ID
    - FILTER_FLOODLIGHT_ACTIVITY: Floodlight Activity Name
    
    ⚠️ IMPORTANT LIMITATION: Floodlight dimensions can ONLY be used with conversion metrics.
    You CANNOT query impressions, clicks, or costs by floodlight activity.
    
    Use these together to map activity IDs to human-readable names:
    dimensions=["FILTER_DATE", "FILTER_FLOODLIGHT_ACTIVITY_ID", "FILTER_FLOODLIGHT_ACTIVITY"]
    
    For revenue/conversion value, you must also include FILTER_ADVERTISER_CURRENCY:
    dimensions=["FILTER_DATE", "FILTER_FLOODLIGHT_ACTIVITY_ID", "FILTER_FLOODLIGHT_ACTIVITY", "FILTER_ADVERTISER_CURRENCY"]
    
    **Geographic Dimensions:**
    - FILTER_COUNTRY: Country
    - FILTER_REGION: Region/State
    - FILTER_CITY: City
    
    **Device & Platform Dimensions:**
    - FILTER_DEVICE_TYPE: Device Type
    - FILTER_BROWSER: Browser
    - FILTER_ENVIRONMENT: Environment

    **Available Metrics**:
    
    **Core Performance Metrics:**
    - METRIC_IMPRESSIONS: Impressions
    - METRIC_CLICKS: Clicks
    - METRIC_CTR: Click-through Rate
    - METRIC_VIEWABLE_IMPRESSIONS: Viewable Impressions
    - METRIC_MEASURABLE_IMPRESSIONS: Measurable Impressions
    
    **Conversion Metrics (ONLY these work with Floodlight dimensions):**
    - METRIC_TOTAL_CONVERSIONS: Total Conversions (all types)
    - METRIC_LAST_CLICKS: Post-Click Conversions
    - METRIC_LAST_IMPRESSIONS: Post-View Conversions
    - METRIC_REVENUE_ADVERTISER: Revenue/Conversion Value (requires FILTER_ADVERTISER_CURRENCY dimension)
    
    **Cost Metrics (NOT compatible with Floodlight dimensions):**
    - METRIC_MEDIA_COST_ADVERTISER: Media Cost (Advertiser Currency)
    - METRIC_TOTAL_MEDIA_COST_ADVERTISER: Total Media Cost
    - METRIC_BILLABLE_COST_ADVERTISER: Billable Cost
    
    **Video Metrics:**
    - METRIC_VIDEO_COMPLETION_RATE: Video Completion Rate

    For the complete list, see: https://developers.google.com/bid-manager/reference/rest/v2/filters-metrics

    **Example Usage**:
    
    # Basic campaign performance
    ```
    run_report(
        start_date="2025-01-01",
        end_date="2025-01-31",
        dimensions=["FILTER_DATE", "FILTER_ADVERTISER_NAME", "FILTER_MEDIA_PLAN_NAME"],
        metrics=["METRIC_IMPRESSIONS", "METRIC_CLICKS", "METRIC_CTR", "METRIC_TOTAL_CONVERSIONS"],
        advertiser_ids="123456789"
    )
    ```
    
    # Conversion tracking by Floodlight Activity (CRITICAL FOR CONVERSION ANALYSIS)
    ```
    run_report(
        start_date="2025-11-01",
        end_date="2025-11-30",
        dimensions=["FILTER_DATE", "FILTER_FLOODLIGHT_ACTIVITY_ID", "FILTER_FLOODLIGHT_ACTIVITY"],
        metrics=["METRIC_TOTAL_CONVERSIONS", "METRIC_LAST_CLICKS", "METRIC_LAST_IMPRESSIONS"],
        advertiser_ids="123456789"
    )
    ```
    
    # Conversion tracking with Revenue/Conversion Value
    ```
    run_report(
        start_date="2025-11-01",
        end_date="2025-11-30",
        dimensions=["FILTER_DATE", "FILTER_FLOODLIGHT_ACTIVITY_ID", "FILTER_FLOODLIGHT_ACTIVITY", "FILTER_ADVERTISER_CURRENCY"],
        metrics=["METRIC_TOTAL_CONVERSIONS", "METRIC_REVENUE_ADVERTISER"],
        advertiser_ids="123456789"
    )
    ```

    Args:
        start_date: Report start date (YYYY-MM-DD)
        end_date: Report end date (YYYY-MM-DD)
        dimensions: Dimensions to group by (list or comma-separated)
        metrics: Metrics to retrieve (list or comma-separated)
        advertiser_ids: Optional advertiser ID(s) to filter
        campaign_ids: Optional campaign ID(s) to filter
        insertion_order_ids: Optional insertion order ID(s) to filter
        line_item_ids: Optional line item ID(s) to filter
        report_name: Optional name for the report

    Returns:
        Dictionary containing:
        - success: Boolean indicating success
        - data: List of dictionaries with report rows
        - metadata: Report metadata (dates, filters, etc.)
    """
    try:
        service = get_service()

        # Prepare dates
        start_date_dict = format_date_for_api(start_date)
        end_date_dict = format_date_for_api(end_date)

        # Prepare dimensions and metrics
        dimensions_list, metrics_list = prepare_dimensions_and_metrics(dimensions, metrics)

        # Prepare filters
        filters = prepare_filters(
            advertiser_ids=advertiser_ids,
            campaign_ids=campaign_ids,
            insertion_order_ids=insertion_order_ids,
            line_item_ids=line_item_ids
        )

        if not filters:
            logger.warning("No filters specified. Report will include all data (may be very large).")

        # Build query object
        query_obj = {
            "metadata": {
                "title": report_name,
                "dataRange": {
                    "range": "CUSTOM_DATES",
                    "customStartDate": start_date_dict,
                    "customEndDate": end_date_dict
                },
                "format": "CSV"
            },
            "params": {
                "type": "STANDARD",
                "groupBys": dimensions_list,
                "filters": filters,
                "metrics": metrics_list
            },
            "schedule": {
                "frequency": "ONE_TIME"
            }
        }

        logger.info(f"Creating query: {report_name}")

        # Create query
        query_response = service.queries().create(body=query_obj).execute()
        query_id = query_response["queryId"]

        logger.info(f"Query {query_id} created. Running synchronously...")

        # Run query synchronously (wait for completion)
        report_response = service.queries().run(
            queryId=query_id,
            synchronous=True
        ).execute()

        # Check status
        if report_response["metadata"]["status"]["state"] == "FAILED":
            error_msg = report_response["metadata"]["status"].get("message", "Unknown error")
            logger.error(f"Report failed: {error_msg}")
            return {
                "success": False,
                "error": f"Report generation failed: {error_msg}",
                "query_id": query_id
            }

        logger.info(f"Report {report_response['key']['reportId']} generated successfully")

        # Download and parse CSV
        gcs_path = report_response["metadata"]["googleCloudStoragePath"]
        csv_content = download_csv_from_gcs(gcs_path)
        parsed_data = parse_csv_to_json(csv_content)

        return {
            "success": True,
            "data": parsed_data,
            "metadata": {
                "query_id": query_id,
                "report_id": report_response["key"]["reportId"],
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "dimensions": dimensions_list,
                "metrics": metrics_list,
                "filters": filters,
                "row_count": len(parsed_data)
            }
        }

    except Exception as e:
        logger.error(f"Error running report: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@mcp.resource("dv360://dimensions-and-metrics")
def dimensions_and_metrics_reference() -> str:
    """
    Complete reference for DV360 dimensions and metrics.
    """
    return """# DV360 Dimensions and Metrics Reference

## ⚡ CRITICAL CAPABILITY: Floodlight Conversion Tracking

**You can segment conversions by Floodlight Activities!**

Use these dimensions together to track specific conversion actions:
- `FILTER_FLOODLIGHT_ACTIVITY_ID` - Unique activity identifier
- `FILTER_FLOODLIGHT_ACTIVITY` - Human-readable activity name

Example: Track product views, add-to-cart, purchases, downloads, etc. separately.

---

## Dimensions (groupBys)

### Entity Dimensions
- FILTER_ADVERTISER: Advertiser ID
- FILTER_ADVERTISER_NAME: Advertiser name
- FILTER_MEDIA_PLAN: Campaign ID
- FILTER_MEDIA_PLAN_NAME: Campaign name
- FILTER_INSERTION_ORDER: Insertion Order ID
- FILTER_INSERTION_ORDER_NAME: Insertion Order name
- FILTER_LINE_ITEM: Line Item ID
- FILTER_LINE_ITEM_NAME: Line Item name
- FILTER_CREATIVE: Creative ID
- FILTER_CREATIVE_TYPE: Creative type
- FILTER_CREATIVE_SIZE: Creative size

### Floodlight Conversion Dimensions (CRITICAL)
- FILTER_FLOODLIGHT_ACTIVITY_ID: Floodlight Activity ID (unique identifier)
- FILTER_FLOODLIGHT_ACTIVITY: Floodlight Activity Name (human-readable name)
- FILTER_ADVERTISER_CURRENCY: Required when using METRIC_REVENUE_ADVERTISER

⚠️ **IMPORTANT LIMITATION**: Floodlight dimensions can ONLY be used with conversion metrics.
You CANNOT query impressions, clicks, or costs by floodlight activity.

**Usage patterns**:
```python
# Basic conversion tracking
dimensions=["FILTER_FLOODLIGHT_ACTIVITY_ID", "FILTER_FLOODLIGHT_ACTIVITY"]
metrics=["METRIC_TOTAL_CONVERSIONS"]

# With revenue/conversion value
dimensions=["FILTER_FLOODLIGHT_ACTIVITY_ID", "FILTER_FLOODLIGHT_ACTIVITY", "FILTER_ADVERTISER_CURRENCY"]
metrics=["METRIC_TOTAL_CONVERSIONS", "METRIC_REVENUE_ADVERTISER"]
```
This allows you to segment conversions by specific floodlight actions (e.g., "product_view", "add_to_cart", "online_sale")

### Time Dimensions
- FILTER_DATE: Date (YYYY-MM-DD)
- FILTER_WEEK: Week
- FILTER_MONTH: Month
- FILTER_YEAR: Year

### Geographic Dimensions
- FILTER_COUNTRY: Country
- FILTER_REGION: Region/State
- FILTER_CITY: City
- FILTER_ZIP_CODE: Zip/Postal code
- FILTER_DMA: Designated Market Area

### Device & Platform Dimensions
- FILTER_DEVICE_TYPE: Device type (Desktop, Mobile, Tablet, Connected TV)
- FILTER_BROWSER: Browser
- FILTER_OS: Operating system
- FILTER_CARRIER: Mobile carrier
- FILTER_ENVIRONMENT: Environment (App, Web)

### Targeting Dimensions
- FILTER_AUDIENCE_LIST: Audience list
- FILTER_AGE: Age range
- FILTER_GENDER: Gender

### Inventory Dimensions
- FILTER_EXCHANGE: Exchange
- FILTER_SITE: Site/App
- FILTER_URL: URL
- FILTER_INVENTORY_SOURCE: Inventory source

## Metrics

### Impression & Reach Metrics
- METRIC_IMPRESSIONS: Total impressions
- METRIC_VIEWABLE_IMPRESSIONS: Viewable impressions (MRC standard)
- METRIC_MEASURABLE_IMPRESSIONS: Measurable impressions
- METRIC_UNIQUE_REACH_IMPRESSION: Unique reach (impressions)
- METRIC_ACTIVE_VIEW_PERCENT_VIEWABLE_IMPRESSIONS: Active View viewable impression %
- METRIC_ACTIVE_VIEW_PERCENT_MEASURABLE_IMPRESSIONS: Active View measurable impression %

### Click Metrics
- METRIC_CLICKS: Total clicks
- METRIC_CTR: Click-through rate
- METRIC_UNIQUE_REACH_CLICK: Unique reach (clicks)

### Conversion Metrics
- METRIC_TOTAL_CONVERSIONS: Total conversions (all types)
- METRIC_LAST_CLICKS: Last-click conversions
- METRIC_LAST_IMPRESSIONS: Last-impression conversions
- METRIC_POST_VIEW_CONVERSIONS: Post-view conversions
- METRIC_POST_CLICK_CONVERSIONS: Post-click conversions

### Cost Metrics
- METRIC_MEDIA_COST_ADVERTISER: Media cost (advertiser currency)
- METRIC_BILLABLE_COST_ADVERTISER: Billable cost (advertiser currency)
- METRIC_TOTAL_MEDIA_COST_ADVERTISER: Total media cost
- METRIC_CPM_FEE1_ADVERTISER: CPM Fee 1
- METRIC_CPM_FEE2_ADVERTISER: CPM Fee 2
- METRIC_PLATFORM_FEE_ADVERTISER: Platform fee

### Revenue & ROI Metrics
- METRIC_REVENUE_ADVERTISER: Revenue (advertiser currency)
- METRIC_PROFIT_ADVERTISER: Profit (advertiser currency)
- METRIC_ROI_RATIO: Return on investment ratio
- METRIC_REVENUE_ECPA_ADVERTISER: Revenue eCPA
- METRIC_REVENUE_ECPC_ADVERTISER: Revenue eCPC
- METRIC_REVENUE_ECPM_ADVERTISER: Revenue eCPM

### Video Metrics
- METRIC_VIDEO_COMPANION_IMPRESSIONS: Video companion impressions
- METRIC_VIDEO_COMPLETION_RATE: Video completion rate
- METRIC_TRUEVIEW_VIEWS: TrueView views
- METRIC_TRUEVIEW_VIEW_RATE: TrueView view rate
- METRIC_VIDEO_QUARTILE_25_RATE: 25% video completion rate
- METRIC_VIDEO_QUARTILE_50_RATE: 50% video completion rate
- METRIC_VIDEO_QUARTILE_75_RATE: 75% video completion rate
- METRIC_VIDEO_QUARTILE_100_RATE: 100% video completion rate

### Engagement Metrics
- METRIC_RICH_MEDIA_ENGAGEMENTS: Rich media engagements
- METRIC_RICH_MEDIA_AVERAGE_DISPLAY_TIME: Rich media avg display time

## Example Queries

### Daily Campaign Performance
```python
dimensions=["FILTER_DATE", "FILTER_MEDIA_PLAN_NAME"]
metrics=["METRIC_IMPRESSIONS", "METRIC_CLICKS", "METRIC_CTR", "METRIC_TOTAL_CONVERSIONS", "METRIC_MEDIA_COST_ADVERTISER"]
```

### Floodlight Conversion Tracking by Activity (CRITICAL FOR CONVERSION ANALYSIS)
```python
# This segments conversions by specific floodlight actions
# ⚠️ NOTE: Only conversion metrics work with floodlight dimensions
dimensions=["FILTER_DATE", "FILTER_FLOODLIGHT_ACTIVITY_ID", "FILTER_FLOODLIGHT_ACTIVITY"]
metrics=["METRIC_TOTAL_CONVERSIONS", "METRIC_LAST_CLICKS", "METRIC_LAST_IMPRESSIONS"]

# Example output shows conversion funnel:
# - product_view: 43 conversions
# - add_to_cart: 3 conversions  
# - online_sale: 3 conversions
# - find_a_branch: 4 conversions
```

### Floodlight Conversion Value / Revenue Tracking
```python
# Track revenue by floodlight activity (requires FILTER_ADVERTISER_CURRENCY)
dimensions=["FILTER_DATE", "FILTER_FLOODLIGHT_ACTIVITY_ID", "FILTER_FLOODLIGHT_ACTIVITY", "FILTER_ADVERTISER_CURRENCY"]
metrics=["METRIC_TOTAL_CONVERSIONS", "METRIC_REVENUE_ADVERTISER"]

# This shows which conversion actions generate revenue
```

### Floodlight Activity Performance by Campaign
```python
# See which campaigns drive specific conversion actions
# ⚠️ NOTE: Cannot include cost metrics with floodlight dimensions
dimensions=["FILTER_MEDIA_PLAN_NAME", "FILTER_FLOODLIGHT_ACTIVITY"]
metrics=["METRIC_TOTAL_CONVERSIONS", "METRIC_LAST_CLICKS", "METRIC_LAST_IMPRESSIONS"]
```

### Creative Performance by Device
```python
dimensions=["FILTER_CREATIVE_TYPE", "FILTER_DEVICE_TYPE"]
metrics=["METRIC_IMPRESSIONS", "METRIC_CLICKS", "METRIC_VIEWABLE_IMPRESSIONS"]
```

### Geographic Performance
```python
dimensions=["FILTER_COUNTRY", "FILTER_REGION"]
metrics=["METRIC_IMPRESSIONS", "METRIC_CLICKS", "METRIC_TOTAL_CONVERSIONS", "METRIC_REVENUE_ADVERTISER"]
```

For complete documentation, see:
https://developers.google.com/bid-manager/reference/rest/v2/filters-metrics
"""


def initialize_server():
    """Initialize the MCP server and validate credentials."""
    logger.info("Initializing DV360 MCP Server...")

    try:
        # Validate service account is configured
        get_service()
        logger.info("DV360 MCP Server initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize server: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point for the MCP server."""
    initialize_server()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
