# Canton Wallet Reports

Automated generation of CSV reports for Canton blockchain wallets.

## Overview

This workflow generates weekly CSV reports for Nethermind Canton wallets, including both validator and non-validator wallets. Reports include transaction details and daily summaries.

## Features

- **Automated Weekly Reports**: Scheduled to run every Monday at 9:00 AM UTC
- **Two Report Types**: 
  - Transfers CSV: Detailed transaction list with dates, amounts, and parties
  - Summary CSV: Daily aggregated data with received, sent, and net balances
- **Dual Wallet Support**: 
  - Validator wallet: `nethermind-angkor-1::12201d94ec4ba973ab5c51e3b769a6aca54f061afc963619a4d6109044eaccafc7ba`
  - Non-validator wallet: `nethermind::1220409a9fcc5ff6422e29ab978c22c004dde33202546b4bcbde24b25b85353366c2`
- **Artifact Storage**: Reports are saved as workflow artifacts with 90-day retention

## Usage

### Basic Usage

```yaml
name: Weekly Canton Reports

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9 AM UTC

jobs:
  generate_reports:
    uses: NethermindEth/github-workflows/.github/workflows/canton-reports.yaml@main
    with:
      output_dir: canton-reports
```

### Advanced Usage

```yaml
name: Canton Reports - Custom Schedule

on:
  schedule:
    - cron: '0 0 * * 0'  # Every Sunday at midnight UTC
  workflow_dispatch:      # Allow manual trigger

jobs:
  validator_reports:
    name: Validator Wallet Reports
    uses: NethermindEth/github-workflows/.github/workflows/canton-reports.yaml@main
    with:
      runner: ubuntu-latest
      output_dir: reports/validator
      validator_only: true
      days: 7
      
  non_validator_reports:
    name: Non-Validator Wallet Reports
    uses: NethermindEth/github-workflows/.github/workflows/canton-reports.yaml@main
    with:
      runner: ubuntu-latest
      output_dir: reports/non-validator
      non_validator_only: true
      days: 7
```

## Workflow Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `runner` | Runner to use | No | `ubuntu-latest` |
| `output_dir` | Directory to save CSV reports | No | `reports` |
| `use_mock_data` | Use mock data instead of API | No | `false` |
| `days` | Number of days of data to fetch | No | `7` |
| `validator_only` | Generate only validator wallet reports | No | `false` |
| `non_validator_only` | Generate only non-validator wallet reports | No | `false` |

## Output Files

The workflow generates the following CSV files:

### Transfers CSV
Contains detailed transaction information:
- Date and Time
- Transaction Hash
- From and To addresses
- Amount and Currency
- Transaction Type (reward, sent, received)
- Status

**Example**: `cantonscan-validator-transfers-20260127.csv`

### Summary CSV
Contains daily aggregated data:
- Date
- Total Received
- Total Sent
- Net Balance Change
- Transaction Count

**Example**: `cantonscan-validator-summary-20260127.csv`

## Schedule Configuration

The workflow can be scheduled using cron expressions:

```yaml
schedule:
  - cron: '0 9 * * 1'  # Every Monday at 9 AM UTC
  - cron: '0 0 1 * *'  # First day of every month at midnight UTC
  - cron: '0 0 * * 0'  # Every Sunday at midnight UTC
```

## Manual Execution

You can manually trigger the workflow:

1. Navigate to **Actions** in your GitHub repository
2. Select **Weekly Canton Wallet Reports**
3. Click **Run workflow**
4. Optionally enable mock data for testing
5. Click **Run workflow** to start

## Accessing Reports

After the workflow completes:

1. Go to the workflow run in **Actions**
2. Scroll to the **Artifacts** section
3. Download `canton-wallet-reports-{run-id}`
4. Extract the ZIP file to access CSV reports

## Local Development

You can run the script locally for testing:

```bash
# Install Python 3.11+
python3 --version

# Run with mock data
python3 scripts/generate_canton_reports.py --output-dir ./reports --mock --days 7

# Run for specific wallet only
python3 scripts/generate_canton_reports.py --output-dir ./reports --mock --validator-only

# View help
python3 scripts/generate_canton_reports.py --help
```

## API Integration

The script fetches data from the Cantonscan API. If the API is unavailable or returns no data, it will automatically fall back to mock data for demonstration purposes.

To update the API endpoints, modify the `CANTONSCAN_API_BASE` constant in `scripts/generate_canton_reports.py`.

## Related Links

- [Linear Issue ANG-812](https://linear.app/nethermind/issue/ANG-812/automate-weekly-csv-reports-for-canton-wallets)
- [Cantonscan Explorer](https://cantonscan.com)

## Troubleshooting

**No reports generated**: Check that the workflow has proper permissions and the API is accessible.

**Mock data being used**: The API may be unavailable or returning no data. Check the workflow logs for details.

**Reports not found**: Verify the `output_dir` input matches the artifact path.
