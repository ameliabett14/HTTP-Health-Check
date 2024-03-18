import time
import requests
import yaml
from urllib.parse import urlparse
import sys


# Function to extract domain and port from URL
def extract_domain(url):
  parsed_url = urlparse(url)
  netloc = parsed_url.netloc
  if ":" in netloc:
    # If port is specified, include it in the domain
    return netloc
  elif parsed_url.scheme == 'http':
    # If http scheme, use default port 80
    return f"{netloc}:80"
  elif parsed_url.scheme == 'https':
    # If https scheme, use default port 443
    return f"{netloc}:443"
  else:
    # For other schemes, use the default netloc
    return netloc


# Function to send HTTP request and check health
def check_health(endpoint):
  url = endpoint['url']
  method = endpoint.get('method', 'GET')
  headers = endpoint.get('headers', {})
  body = endpoint.get('body', None)

  valid_methods = [
      'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'TRACE'
  ]

  try:
    if method in valid_methods:
      response = requests.request(method,
                                  url,
                                  headers=headers,
                                  data=body,
                                  timeout=5)

      # Check if the outcome is UP or DOWN
      if response.status_code >= 200 and response.status_code < 300 and response.elapsed.total_seconds(
      ) * 1000 < 500:
        return True, f"HTTP response code {response.status_code} and response latency {response.elapsed.total_seconds() * 1000} ms => UP"
      else:
        return False, f"HTTP response code {response.status_code} and response latency {response.elapsed.total_seconds() * 1000} ms => DOWN"
  except Exception as e:
    # Any exception is considered as DOWN
    return False, f"Exception occurred: {str(e)} => DOWN"


# Function to log availability percentage
def log_availability_percentage(availabilities):
  for domain, (success_count, total_count) in availabilities.items():
    percentage = (success_count / total_count) * 100 if total_count > 0 else 0
    print(
        f"\n{domain} has {round(percentage)}% availability percentage ({success_count} of {total_count} endpoints)"
    )


# Function to load YAML data from file
def load_yaml_file(file_path):
  with open(file_path, 'r') as file:
    return yaml.safe_load(file)


# Main function to run health checks
def run_health_checks(endpoints):
  availabilities = {}  # Dictionary to store availability for each domain

  try:
    while True:
      status_list = []

      for endpoint in endpoints:
        endpoint_name = endpoint.get('name', 'N/A')
        domain = extract_domain(endpoint['url'])

        # Check health of the endpoint
        is_available, log_message = check_health(endpoint)

        if is_available:
          status_list.append((endpoint_name, 'UP', log_message))
          # Update availability for the domain
          success_count, total_count = availabilities.get(domain, (0, 0))
          availabilities[domain] = (success_count + 1, total_count + 1)
        else:
          status_list.append((endpoint_name, 'DOWN', log_message))
          # Update total count for the domain
          success_count, total_count = availabilities.get(domain, (0, 0))
          availabilities[domain] = (success_count, total_count + 1)

      # Log availability percentage and detailed endpoint status after each iteration
      log_availability_percentage(availabilities)

      # Check for instances where CNAME is present as a separate health check
      cname_instances = [
          name for name in availabilities.keys()
          if 'www.' + name in availabilities and name != 'www'
      ]
      for cname_instance in cname_instances:
        print(
            f"● CNAME {cname_instance} is present as a separate health check")

      for endpoint_name, status, log_message in status_list:
        print(f"\n● Endpoint with name {endpoint_name} has {log_message}")

      # Wait for 15 seconds before the next iteration
      time.sleep(15)

  except KeyboardInterrupt:
    # Handle CTRL+C to exit gracefully
    pass
  finally:
    # Final log of availability percentage before exiting
    log_availability_percentage(availabilities)


if __name__ == "__main__":
  if len(sys.argv) < 2:
    print("Usage: python main.py <path_to_yaml_file>")
    sys.exit(1)

  yaml_file_path = sys.argv[1]
  endpoints = load_yaml_file(yaml_file_path)

  # Run health checks
  run_health_checks(endpoints)
