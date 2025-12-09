# DV360 MCP Server

A Model Context Protocol (MCP) server for Display & Video 360 (DV360) that provides entity management and performance reporting capabilities.

## Sample Report Demo

**[View Sample Performance Report](https://caspercrause.github.io/dv360-ads-mcp-server/templates/dv360_performance_report.html)** - See what's possible with this MCP server.

The sample report demonstrates:
- Campaign and Insertion Order performance analysis
- Age group segmentation from Line Item targeting
- Floodlight conversion funnel (Find Branch → Product View → Add to Cart → Purchase)
- Creative banner size performance comparison

## Architecture

This server integrates with two Google APIs to provide comprehensive DV360 access:

- **Display & Video 360 API (v4)**: Entity management (campaigns, insertion orders, creatives)
- **Bid Manager API (v2)**: Performance reporting (impressions, clicks, conversions, costs)

## Features

- **Floodlight Conversion Tracking**: Segment conversions by specific floodlight activities (product views, add-to-cart, purchases, etc.)
- **Entity Management**: List and retrieve campaigns, insertion orders, and creatives with filtering and ordering
- **Performance Reporting**: Run synchronous reports with comprehensive metrics
- **Advanced Filtering**: Filter entities by status, dates, and other properties
- **Custom Ordering**: Sort results by any field in ascending or descending order
- **Flexible Input Types**: Accepts dimensions/metrics as lists or comma-separated strings
- **Comprehensive Metrics**: Access all DV360 metrics and dimensions

## Prerequisites

### 1. Google Cloud Project Setup

1. Create or select a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the required APIs:
   - **Display & Video 360 API** (for entity management)
   - **DoubleClick Bid Manager API** (for reporting)
3. Create a service account:
   - Go to IAM & Admin > Service Accounts
   - Create a new service account
   - Download the JSON key file

### 2. DV360 Platform Setup

Your service account needs to be granted access in the DV360 platform:

1. Log into [Display & Video 360](https://displayvideo.google.com/)
2. Navigate to **Settings** > **Access Management**
3. Click **Add User**
4. Enter the service account email (found in your JSON key file: `client_email`)
5. Assign appropriate permissions:
   - **Read & Write** access for entity management tools
   - **Read** access is sufficient if you only need reporting
6. Select the partner(s) and advertiser(s) the service account should access

![DV360 Partner ID Location](Add-Service-Account.png)

**Note**: The service account email looks like: `your-service-account@your-project.iam.gserviceaccount.com`

### 3. Find Your Partner ID (Optional)

If you want to use `list_advertisers` without specifying a partner ID each time:

**Method 1: From any DV360 URL**
1. Log into DV360
2. Look at the URL: `https://displayvideo.google.com/ng_nav/p/[PARTNER_ID]/...`
3. The number after `/p/` is your Partner ID

**Method 2: From Partner Settings**
1. Log into DV360
2. Navigate to **Partner Settings** > **Basic Details**
3. The URL will be: `https://displayvideo.google.com/ng_nav/p/{partner-id}/details`
4. Your Partner ID is visible in the URL
5. Or Locate using the below image as reference

![DV360 Partner ID Location](DV-360-Partner-ID.png)

Once you have your Partner ID, add it to your `.env` file:
```bash
DV360_PARTNER_ID=your_partner_id
```

## Installation

### Step 1: Create a Virtual Environment

Create a dedicated virtual environment for the DV360 MCP server:

```bash
# Create virtual environment
python3 -m venv dv360_venv

# Activate the virtual environment
source dv360_venv/bin/activate  # On macOS/Linux
# OR
dv360_venv\Scripts\activate     # On Windows
```

**Important**: Keep the virtual environment activated for all subsequent commands.

### Step 2: Clone and Install

```bash
# Clone the repository
git clone <repository-url>
cd dv360-ads-mcp-server

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create the environment configuration file:

```bash
# Copy the example file
cp .env.example .env
```

Edit the `.env` file with your credentials:

```bash
# REQUIRED: Your service account JSON (MUST be a single line)
DV360_SERVICE_ACCOUNT={"type":"service_account","project_id":"your-project","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"your-service-account@your-project.iam.gserviceaccount.com","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"}

# OPTIONAL: Your DV360 Partner ID (speeds up advertiser listing)
DV360_PARTNER_ID=your_partner_id
```

**REMEMBER**: The `DV360_SERVICE_ACCOUNT` value MUST be the entire JSON content on a single line. Do NOT format it with line breaks.

**How to get the service account JSON:**
1. Go to Google Cloud Console → IAM & Admin → Service Accounts
2. Select your DV360 service account
3. Go to "Keys" tab → "Add Key" → "Create new key" → JSON
4. Open the downloaded JSON file
5. Copy the entire content and paste it as one line in the .env file

### Step 4: Configure MCP in Your AI Client

#### For Claude Desktop:

1. Open your Claude Desktop configuration file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add the DV360 MCP server configuration:

**Important**: Replace `/full/path/to/` with the actual paths on your system.

#### For Cursor:

1. Open Cursor settings or the Command Palette `⌘ + ⇧ + P`
2. Go to "MCP Servers" section
3. Add a new server with:
   - **Name**: `dv360`
   - **Command**: `/full/path/to/dv360-ads-mcp-server/dv360_venv/bin/python`
   - **Arguments**: `/full/path/to/dv360-ads-mcp-server/server.py`
   
   **_Optional_**:
   add Current Working Directory (cwd):
    - **Current Working Directory**: `/full/path/to/dv360-ads-mcp-server`

#### Example file:
```json
{
  "mcpServers": {
    "dv360": {
      "command": "/full/path/to/dv360-ads-mcp-server/dv360_venv/bin/python/python",
      "args": ["/full/path/to/dv360-ads-mcp-server/server.py"],
      "cwd": "/full/path/to/dv360-ads-mcp-server"
    }
  }
}
```

### Step 5: Restart and Test

1. **Restart your AI client** (Claude Desktop or Cursor) completely
2. **Test the connection** by asking about DV360 in a new chat

**Expected behavior**: You should see DV360 tools available when you mention DV360-related topics.

### Troubleshooting Setup Issues

#### Virtual Environment Issues:
```bash
# Make sure you're in the right directory and venv is activated
pwd  # Should show dv360-ads-mcp-server
which python  # Should show path to dv360_venv/bin/python (/full/path/to/dv360-ads-mcp-server)
```

#### Service Account JSON Issues:
- Verify the JSON is exactly one line in your `.env` file
- Check that there are no extra quotes around the JSON
- Ensure the service account has DV360 API access

#### MCP Configuration Issues:
- Double-check file paths in the MCP config
- Ensure the virtual environment Python path is correct
- Try restarting your AI client after configuration changes

#### Testing the Setup:
Once configured, try asking: *"List my DV360 advertisers"* in a new chat. If you get a response with advertiser data, the setup is working.


## Available Tools

### Entity Management Tools

#### Campaigns

**list_campaigns** - List all campaigns for an advertiser
```python
list_campaigns(
    advertiser_id="123456",
    filter='entityStatus="ENTITY_STATUS_ACTIVE"',
    order_by="displayName",
    page_size=100
)
```

**get_campaign** - Get detailed information about a specific campaign
```python
get_campaign(
    advertiser_id="123456",
    campaign_id="789012"
)
```

#### Insertion Orders

**list_insertion_orders** - List all insertion orders for an advertiser
```python
list_insertion_orders(
    advertiser_id="123456",
    filter='entityStatus="ENTITY_STATUS_ACTIVE"',
    order_by="displayName",
    page_size=100
)
```

**get_insertion_order** - Get detailed information about a specific insertion order
```python
get_insertion_order(
    advertiser_id="123456",
    insertion_order_id="789012"
)
```

#### Creatives

**list_creatives** - List all creatives for an advertiser
```python
list_creatives(
    advertiser_id="123456",
    filter='entityStatus="ENTITY_STATUS_ACTIVE"',
    order_by="displayName",
    page_size=100
)
```

**get_creative** - Get detailed information about a specific creative
```python
get_creative(
    advertiser_id="123456",
    creative_id="789012"
)
```

#### Advertisers

**list_advertisers** - List all advertisers under a partner
```python
list_advertisers(
    partner_id="123456",  # Optional if DV360_PARTNER_ID is set
    order_by="displayName",
    page_size=100
)
```

### Filtering Examples

All list tools support filtering by various criteria:

**Entity Status:**
- `entityStatus="ENTITY_STATUS_ACTIVE"`
- `entityStatus="ENTITY_STATUS_PAUSED"`
- `entityStatus="ENTITY_STATUS_ARCHIVED"`

**Date Ranges:**
- `updateTime>"2025-01-01T00:00:00Z"`
- `updateTime<"2025-12-31T23:59:59Z"`

**Ordering:**
- `displayName` (ascending)
- `displayName desc` (descending)
- `updateTime desc`

### Reporting Tools

## Usage

### Running a Report

The main tool is `run_report`, which creates a query, runs it synchronously, downloads the CSV, and returns JSON data:

```python
run_report(
    start_date="2025-01-01",
    end_date="2025-01-31",
    dimensions=["FILTER_DATE", "FILTER_ADVERTISER_NAME", "FILTER_MEDIA_PLAN_NAME"],
    metrics=["METRIC_IMPRESSIONS", "METRIC_CLICKS", "METRIC_CTR", "METRIC_TOTAL_CONVERSIONS"],
    advertiser_ids="123456789"
)
```

### Available Parameters

- **start_date** (required): Start date in YYYY-MM-DD format
- **end_date** (required): End date in YYYY-MM-DD format
- **dimensions** (required): Dimensions to group by (list or comma-separated string)
- **metrics** (required): Metrics to retrieve (list or comma-separated string)
- **advertiser_ids** (optional): Filter by advertiser ID(s)
- **campaign_ids** (optional): Filter by campaign ID(s)
- **insertion_order_ids** (optional): Filter by insertion order ID(s)
- **line_item_ids** (optional): Filter by line item ID(s)
- **report_name** (optional): Name for the report (default: "MCP Report")

### Flexible Input Types

You can provide dimensions and metrics in multiple ways:

```python
# As a list
dimensions=["FILTER_DATE", "FILTER_ADVERTISER_NAME"]

# As a comma-separated string
dimensions="FILTER_DATE, FILTER_ADVERTISER_NAME"

# Same for IDs
advertiser_ids=["123", "456"]  # or
advertiser_ids="123, 456"
```

## Available Dimensions

### Floodlight Conversion Dimensions

**Segment conversions by specific floodlight activities:**

- `FILTER_FLOODLIGHT_ACTIVITY_ID`: Floodlight Activity ID (unique identifier)
- `FILTER_FLOODLIGHT_ACTIVITY`: Floodlight Activity Name (human-readable name)
- `FILTER_ADVERTISER_CURRENCY`: Required when tracking revenue/conversion value

⚠️ **IMPORTANT LIMITATION**: Floodlight dimensions can **ONLY** be used with conversion metrics.
You **CANNOT** query impressions, clicks, or costs by floodlight activity.

**Compatible metrics with Floodlight dimensions:**
- ✅ `METRIC_TOTAL_CONVERSIONS` - Total conversions (all attribution)
- ✅ `METRIC_LAST_CLICKS` - Post-click conversions
- ✅ `METRIC_LAST_IMPRESSIONS` - Post-view conversions
- ✅ `METRIC_REVENUE_ADVERTISER` - Conversion value (requires `FILTER_ADVERTISER_CURRENCY`)
- ❌ Impressions, Clicks, Costs - NOT compatible

**Example conversion actions you can track:**
- `product_view` - Product page views
- `add_to_cart` - Items added to cart
- `purchase` - Purchase completions
- `sign_up` - Sign up for a service

### Entity Dimensions
- `FILTER_ADVERTISER`: Advertiser ID
- `FILTER_ADVERTISER_NAME`: Advertiser name
- `FILTER_MEDIA_PLAN`: Campaign ID
- `FILTER_MEDIA_PLAN_NAME`: Campaign name
- `FILTER_INSERTION_ORDER`: Insertion Order ID
- `FILTER_INSERTION_ORDER_NAME`: Insertion Order name
- `FILTER_LINE_ITEM`: Line Item ID
- `FILTER_LINE_ITEM_NAME`: Line Item name
- `FILTER_CREATIVE`: Creative ID
- `FILTER_CREATIVE_TYPE`: Creative type

### Time Dimensions
- `FILTER_DATE`: Date
- `FILTER_WEEK`: Week
- `FILTER_MONTH`: Month
- `FILTER_YEAR`: Year

### Geographic Dimensions
- `FILTER_COUNTRY`: Country
- `FILTER_REGION`: Region/State
- `FILTER_CITY`: City
- `FILTER_DMA`: Designated Market Area

### Device Dimensions
- `FILTER_DEVICE_TYPE`: Device type
- `FILTER_BROWSER`: Browser
- `FILTER_OS`: Operating system
- `FILTER_ENVIRONMENT`: Environment (App/Web)

## Available Metrics

### Impression Metrics
- `METRIC_IMPRESSIONS`: Total impressions
- `METRIC_VIEWABLE_IMPRESSIONS`: Viewable impressions
- `METRIC_MEASURABLE_IMPRESSIONS`: Measurable impressions

### Click Metrics
- `METRIC_CLICKS`: Total clicks
- `METRIC_CTR`: Click-through rate

### Conversion Metrics (ONLY these work with Floodlight Dimensions)
- `METRIC_TOTAL_CONVERSIONS`: Total conversions (all types)
- `METRIC_LAST_CLICKS`: Post-click conversions
- `METRIC_LAST_IMPRESSIONS`: Post-view conversions
- `METRIC_REVENUE_ADVERTISER`: Revenue/conversion value (requires `FILTER_ADVERTISER_CURRENCY` dimension)

**Important**: These are the ONLY metrics that can be combined with `FILTER_FLOODLIGHT_ACTIVITY` dimensions!

**Note**: The API uses `METRIC_LAST_CLICKS` and `METRIC_LAST_IMPRESSIONS` (not `METRIC_POST_CLICK_CONVERSIONS` or `METRIC_POST_VIEW_CONVERSIONS`).

### Cost Metrics
- `METRIC_MEDIA_COST_ADVERTISER`: Media cost
- `METRIC_BILLABLE_COST_ADVERTISER`: Billable cost
- `METRIC_TOTAL_MEDIA_COST_ADVERTISER`: Total media cost

### Revenue Metrics
- `METRIC_REVENUE_ADVERTISER`: Revenue
- `METRIC_PROFIT_ADVERTISER`: Profit
- `METRIC_ROI_RATIO`: ROI ratio

### Video Metrics
- `METRIC_VIDEO_COMPLETION_RATE`: Video completion rate
- `METRIC_TRUEVIEW_VIEWS`: TrueView views
- `METRIC_VIDEO_QUARTILE_25_RATE`: 25% completion
- `METRIC_VIDEO_QUARTILE_50_RATE`: 50% completion
- `METRIC_VIDEO_QUARTILE_75_RATE`: 75% completion
- `METRIC_VIDEO_QUARTILE_100_RATE`: 100% completion

For the complete list, see: https://developers.google.com/bid-manager/reference/rest/v2/filters-metrics

## Using Tools Together for Performance Analysis

How it comes together (no code needed):
- Discover entities: campaigns, insertion orders, line items, creatives.
- Pull performance: impressions, clicks, conversions, cost, and revenue-ready metrics with currency included.
- Break down results: by funnel step (Floodlight), age (from line items), creative size, geography, or device.
- Ship it: generate the HTML report and host it (e.g., GitHub Pages) to share with stakeholders.

What you can explore
- Campaign/IO performance with view vs click conversions.
- Funnel health: Find Branch → Product View → Add to Cart → Purchase.
- Which creatives and sizes are most efficient.
- Which age groups (from line items) respond best.
- Geographic or device splits to refine targeting.

Want hands-on examples?
- Run the sample report locally: `python3 -m http.server 8000` and open `http://localhost:8000/dv360_performance_report.html`.
- Or view the live sample: https://caspercrause.github.io/dv360-ads-mcp-server/templates/dv360_performance_report.html

## Response Format

The server returns a JSON response with the following structure:

```json
{
  "success": true,
  "data": [
    {
      "Date": "2025-01-01",
      "Advertiser": "My Advertiser",
      "Campaign": "My Campaign",
      "Impressions": 10000,
      "Clicks": 150,
      "CTR": 1.5,
      "Total Conversions": 10
    }
  ],
  "metadata": {
    "query_id": "12345",
    "report_id": "67890",
    "date_range": {
      "start_date": "2025-01-01",
      "end_date": "2025-01-31"
    },
    "dimensions": ["FILTER_DATE", "FILTER_ADVERTISER_NAME", "FILTER_MEDIA_PLAN_NAME"],
    "metrics": ["METRIC_IMPRESSIONS", "METRIC_CLICKS", "METRIC_CTR", "METRIC_TOTAL_CONVERSIONS"],
    "row_count": 31
  }
}
```

## Troubleshooting

### Service Account Errors
- Ensure your service account has access to your DV360 account
- Verify the service account JSON is correctly formatted in the DV360_SERVICE_ACCOUNT environment variable
- Check that the service account has the Display & Video 360 API enabled
- Make sure the JSON string is properly escaped and quoted in your .env file

### Query Errors
- Some dimension/metric combinations are not compatible
- Test your query in the DV360 UI first to ensure it works
- Check the [official documentation](https://developers.google.com/bid-manager/reference/rest/v2/filters-metrics) for valid combinations

### Rate Limits
- Google enforces rate limits on the Bid Manager API
- If you hit rate limits, reduce query frequency or batch your requests

## Resources

- [DV360 Bid Manager API Documentation](https://developers.google.com/bid-manager)
- [Filters and Metrics Reference](https://developers.google.com/bid-manager/reference/rest/v2/filters-metrics)
- [FastMCP Documentation](https://github.com/anthropics/fastmcp)