"""External account integration for fetching real account balances."""
from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AccountBalance:
    """Represents a balance from an external account."""
    account_name: str
    payment_method: str
    balance: float
    currency: str = "KES"
    last_updated: Optional[str] = None


class AccountIntegrationError(Exception):
    """Exception raised for account integration errors."""
    pass


class ExternalAccountManager:
    """Manages integration with external accounts for balance fetching."""

    def __init__(self, config_file: str = "external_accounts.json"):
        self.config_file = config_file
        self.accounts_config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load external accounts configuration."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"External accounts config file {self.config_file} not found. Using default config.")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing external accounts config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for external accounts."""
        return {
            "accounts": [
                {
                    "name": "Cash Register 1",
                    "type": "cash_register",
                    "payment_method": "Cash",
                    "api_endpoint": "http://localhost:8080/api/cash_balance",
                    "api_key": "",
                    "enabled": True
                },
                {
                    "name": "M-Pesa Business",
                    "type": "mpesa",
                    "payment_method": "M-Pesa",
                    "api_endpoint": "https://api.safaricom.co.ke/mpesa/b2b/v1/accountbalance",
                    "api_key": "",
                    "enabled": False
                },
                {
                    "name": "Bank Account",
                    "type": "bank",
                    "payment_method": "Bank Transfer",
                    "api_endpoint": "",
                    "api_key": "",
                    "enabled": False
                }
            ],
            "cache_timeout_minutes": 5
        }

    def get_account_balances(self) -> List[AccountBalance]:
        """Fetch balances from all enabled external accounts."""
        balances = []

        for account_config in self.accounts_config.get("accounts", []):
            if not account_config.get("enabled", False):
                continue

            try:
                balance = self._fetch_account_balance(account_config)
                if balance:
                    balances.append(balance)
            except Exception as e:
                logger.error(f"Error fetching balance for {account_config['name']}: {e}")

        return balances

    def _fetch_account_balance(self, account_config: Dict[str, Any]) -> Optional[AccountBalance]:
        """Fetch balance from a specific account."""
        account_type = account_config.get("type")
        account_name = account_config.get("name")

        if account_type == "cash_register":
            return self._fetch_cash_register_balance(account_config)
        elif account_type == "mpesa":
            return self._fetch_mpesa_balance(account_config)
        elif account_type == "bank":
            return self._fetch_bank_balance(account_config)
        else:
            logger.warning(f"Unknown account type: {account_type}")
            return None

    def _fetch_cash_register_balance(self, account_config: Dict[str, Any]) -> Optional[AccountBalance]:
        """Fetch balance from cash register API."""
        api_endpoint = account_config.get("api_endpoint")
        api_key = account_config.get("api_key")

        if not api_endpoint:
            # Simulate cash register balance for demo
            return AccountBalance(
                account_name=account_config["name"],
                payment_method=account_config["payment_method"],
                balance=15000.00,  # Demo balance
                currency="KES",
                last_updated=datetime.now().isoformat()
            )

        try:
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            response = requests.get(api_endpoint, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            return AccountBalance(
                account_name=account_config["name"],
                payment_method=account_config["payment_method"],
                balance=float(data.get("balance", 0)),
                currency=data.get("currency", "KES"),
                last_updated=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Error fetching cash register balance: {e}")
            return None

    def _fetch_mpesa_balance(self, account_config: Dict[str, Any]) -> Optional[AccountBalance]:
        """Fetch balance from M-Pesa API."""
        # This would integrate with M-Pesa's actual API
        # For now, return a demo balance
        return AccountBalance(
            account_name=account_config["name"],
            payment_method=account_config["payment_method"],
            balance=25000.00,  # Demo M-Pesa balance
            currency="KES",
            last_updated=datetime.now().isoformat()
        )

    def _fetch_bank_balance(self, account_config: Dict[str, Any]) -> Optional[AccountBalance]:
        """Fetch balance from bank API."""
        # This would integrate with bank APIs
        # For now, return a demo balance
        return AccountBalance(
            account_name=account_config["name"],
            payment_method=account_config["payment_method"],
            balance=50000.00,  # Demo bank balance
            currency="KES",
            last_updated=datetime.now().isoformat()
        )

    def get_balances_by_payment_method(self) -> Dict[str, float]:
        """Get total balances grouped by payment method."""
        balances = self.get_account_balances()
        grouped_balances = {}

        for balance in balances:
            payment_method = balance.payment_method
            if payment_method not in grouped_balances:
                grouped_balances[payment_method] = 0.0
            grouped_balances[payment_method] += balance.balance

        return grouped_balances

    def save_config(self) -> None:
        """Save the current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.accounts_config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving external accounts config: {e}")


# Global instance for easy access
account_manager = ExternalAccountManager()