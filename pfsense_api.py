import requests

class PfSenseAPI:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_status(self):
        """Example: Get pfSense system status."""
        endpoint = f"{self.base_url}/api/v1/system/status"
        response = requests.get(endpoint, headers=self.headers)
        return response.json()

    def update_firewall_rule(self, rule_id, data):
        """Example: Update a firewall rule."""
        endpoint = f"{self.base_url}/api/v1/firewall/rule/{rule_id}"
        response = requests.put(endpoint, json=data, headers=self.headers)
        return response.json()

# Example usage
if __name__ == "__main__":
    pfsense = PfSenseAPI(base_url="https://pfsense.example.com", api_key="your_api_key_here")
    status = pfsense.get_status()
    print(status)
