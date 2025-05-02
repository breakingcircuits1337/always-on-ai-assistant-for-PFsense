import requests

def call_api(endpoint: str, method: str, headers: dict = None, data: dict = None):
    """
    Calls an API endpoint with the specified method, headers, and data.

    Args:
        endpoint: The API endpoint URL.
        method: The HTTP method (e.g., "GET", "POST").
        headers: A dictionary of HTTP headers.
        data: A dictionary of data to send in the request body (for POST/PUT).

    Returns:
        The response from the API call.
    """
    if method.upper() == "GET":
        response = requests.get(endpoint, headers=headers)
    elif method.upper() == "POST":
        response = requests.post(endpoint, headers=headers, json=data)
    elif method.upper() == "PUT":
        response = requests.put(endpoint, headers=headers, json=data)
    elif method.upper() == "DELETE":
        response = requests.delete(endpoint, headers=headers)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

    response.raise_for_status()
    return response