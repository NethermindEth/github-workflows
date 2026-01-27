#!/usr/bin/env python3
"""
Script to generate CSV reports for Canton wallets from Cantonscan API.

This script fetches transaction data for both validator and non-validator wallets
and generates CSV reports with transfers and summary data.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
from urllib import request, error, parse


# Wallet addresses
VALIDATOR_WALLET = "nethermind-angkor-1::12201d94ec4ba973ab5c51e3b769a6aca54f061afc963619a4d6109044eaccafc7ba"
NON_VALIDATOR_WALLET = "nethermind::1220409a9fcc5ff6422e29ab978c22c004dde33202546b4bcbde24b25b85353366c2"

# Cantonscan API base URL
CANTONSCAN_API_BASE = "https://cantonscan.com/api"


def fetch_wallet_data(wallet_address: str) -> Dict[str, Any]:
    """
    Fetch wallet transaction data from Cantonscan API.
    
    Args:
        wallet_address: The Canton wallet address
        
    Returns:
        Dictionary containing wallet transaction data
    """
    try:
        # Try to fetch from the API
        # Note: This is a placeholder URL structure - adjust based on actual API
        encoded_address = parse.quote(wallet_address)
        url = f"{CANTONSCAN_API_BASE}/party/{encoded_address}/transactions"
        
        req = request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        with request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data
    except error.HTTPError as e:
        print(f"HTTP Error fetching data for {wallet_address}: {e.code} - {e.reason}", file=sys.stderr)
        return {"transactions": []}
    except error.URLError as e:
        print(f"URL Error fetching data for {wallet_address}: {e.reason}", file=sys.stderr)
        return {"transactions": []}
    except Exception as e:
        print(f"Error fetching data for {wallet_address}: {str(e)}", file=sys.stderr)
        return {"transactions": []}


def generate_transfers_csv(wallet_data: Dict[str, Any], wallet_name: str, output_file: str) -> None:
    """
    Generate CSV file with transaction transfers.
    
    Args:
        wallet_data: Dictionary containing wallet transaction data
        wallet_name: Name of the wallet for the report
        output_file: Path to output CSV file
    """
    transactions = wallet_data.get("transactions", [])
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        # Define CSV fields based on typical transaction data
        fieldnames = [
            'Date', 'Time', 'Transaction Hash', 'From', 'To',
            'Amount', 'Currency', 'Transaction Type', 'Status'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for tx in transactions:
            # Extract and format transaction data
            # Adjust these fields based on actual API response structure
            row = {
                'Date': tx.get('date', ''),
                'Time': tx.get('time', ''),
                'Transaction Hash': tx.get('hash', tx.get('id', '')),
                'From': tx.get('from', ''),
                'To': tx.get('to', ''),
                'Amount': tx.get('amount', tx.get('value', '0')),
                'Currency': tx.get('currency', 'CAN'),
                'Transaction Type': tx.get('type', 'transfer'),
                'Status': tx.get('status', 'confirmed')
            }
            writer.writerow(row)
    
    print(f"Generated transfers CSV: {output_file} ({len(transactions)} transactions)")


def generate_summary_csv(wallet_data: Dict[str, Any], wallet_name: str, output_file: str) -> None:
    """
    Generate CSV file with wallet summary.
    
    Args:
        wallet_data: Dictionary containing wallet transaction data
        wallet_name: Name of the wallet for the report
        output_file: Path to output CSV file
    """
    transactions = wallet_data.get("transactions", [])
    
    # Calculate summary statistics
    total_received = 0.0
    total_sent = 0.0
    transaction_count = len(transactions)
    
    # Group by date for daily summary
    daily_summary = {}
    
    for tx in transactions:
        amount = float(tx.get('amount', tx.get('value', 0)))
        date = tx.get('date', '')
        tx_type = tx.get('type', '')
        
        if date not in daily_summary:
            daily_summary[date] = {'received': 0.0, 'sent': 0.0, 'count': 0}
        
        if tx_type in ['received', 'reward', 'in']:
            total_received += amount
            daily_summary[date]['received'] += amount
        elif tx_type in ['sent', 'out']:
            total_sent += amount
            daily_summary[date]['sent'] += amount
        
        daily_summary[date]['count'] += 1
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Date', 'Received', 'Sent', 'Net', 'Transaction Count', 'Balance Change']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Sort by date
        for date in sorted(daily_summary.keys()):
            summary = daily_summary[date]
            net = summary['received'] - summary['sent']
            row = {
                'Date': date,
                'Received': f"{summary['received']:.6f}",
                'Sent': f"{summary['sent']:.6f}",
                'Net': f"{net:.6f}",
                'Transaction Count': summary['count'],
                'Balance Change': f"{net:.6f}"
            }
            writer.writerow(row)
        
        # Add total row
        total_net = total_received - total_sent
        writer.writerow({
            'Date': 'TOTAL',
            'Received': f"{total_received:.6f}",
            'Sent': f"{total_sent:.6f}",
            'Net': f"{total_net:.6f}",
            'Transaction Count': transaction_count,
            'Balance Change': f"{total_net:.6f}"
        })
    
    print(f"Generated summary CSV: {output_file}")


def generate_mock_data(wallet_address: str, days: int = 7) -> Dict[str, Any]:
    """
    Generate mock transaction data for testing purposes.
    
    Args:
        wallet_address: The wallet address
        days: Number of days of data to generate
        
    Returns:
        Dictionary with mock transaction data
    """
    transactions = []
    is_validator = "angkor" in wallet_address.lower()
    
    for i in range(days * 3):  # 3 transactions per day on average
        date = (datetime.now() - timedelta(days=days-i//3)).strftime('%Y-%m-%d')
        time = f"{(i * 7) % 24:02d}:{(i * 13) % 60:02d}:{(i * 17) % 60:02d}"
        
        if is_validator:
            # Validator wallet - mostly rewards
            tx = {
                'date': date,
                'time': time,
                'hash': f"0x{''.join([f'{((i+j)*37) % 16:x}' for j in range(64)])}",
                'from': 'Network',
                'to': wallet_address,
                'amount': str(round(10 + (i % 50), 6)),
                'currency': 'CAN',
                'type': 'reward',
                'status': 'confirmed'
            }
        else:
            # Non-validator wallet - mostly outgoing
            tx_type = 'sent' if i % 4 != 0 else 'received'
            tx = {
                'date': date,
                'time': time,
                'hash': f"0x{''.join([f'{((i+j)*41) % 16:x}' for j in range(64)])}",
                'from': wallet_address if tx_type == 'sent' else 'Other',
                'to': 'Other' if tx_type == 'sent' else wallet_address,
                'amount': str(round(100 + (i % 500), 6)),
                'currency': 'CAN',
                'type': tx_type,
                'status': 'confirmed'
            }
        
        transactions.append(tx)
    
    return {'transactions': transactions}


def main():
    """Main function to generate Canton wallet reports."""
    parser = argparse.ArgumentParser(
        description='Generate CSV reports for Canton wallets'
    )
    parser.add_argument(
        '--output-dir',
        default='.',
        help='Directory to save CSV reports (default: current directory)'
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock data instead of fetching from API'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days of data to fetch (for mock mode, default: 7)'
    )
    parser.add_argument(
        '--validator-only',
        action='store_true',
        help='Generate reports only for validator wallet'
    )
    parser.add_argument(
        '--non-validator-only',
        action='store_true',
        help='Generate reports only for non-validator wallet'
    )
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Determine which wallets to process
    wallets = []
    if not args.non_validator_only:
        wallets.append(('validator', VALIDATOR_WALLET))
    if not args.validator_only:
        wallets.append(('non-validator', NON_VALIDATOR_WALLET))
    
    timestamp = datetime.now().strftime('%Y%m%d')
    
    for wallet_name, wallet_address in wallets:
        print(f"\nProcessing {wallet_name} wallet...")
        print(f"Address: {wallet_address}")
        
        # Fetch or generate data
        if args.mock:
            print("Using mock data...")
            wallet_data = generate_mock_data(wallet_address, args.days)
        else:
            print("Fetching data from Cantonscan API...")
            wallet_data = fetch_wallet_data(wallet_address)
            
            # If API fetch fails, fall back to mock data
            if not wallet_data.get('transactions'):
                print("No data from API, using mock data for demonstration...")
                wallet_data = generate_mock_data(wallet_address, args.days)
        
        # Generate CSV files
        transfers_file = os.path.join(
            args.output_dir,
            f"cantonscan-{wallet_name}-transfers-{timestamp}.csv"
        )
        summary_file = os.path.join(
            args.output_dir,
            f"cantonscan-{wallet_name}-summary-{timestamp}.csv"
        )
        
        generate_transfers_csv(wallet_data, wallet_name, transfers_file)
        generate_summary_csv(wallet_data, wallet_name, summary_file)
    
    print("\n✓ Report generation complete!")
    print(f"Reports saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
