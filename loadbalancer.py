from flask import Flask, redirect, request, session
import threading
import random
import requests
import time
import ssl
import json

app = Flask(__name__)
app.secret_key = "super_secret_key" 

backend_servers = [
    {"url": "http://www.google.com/", "weight": 5},
    {"url": "https://www.youtube.com/", "weight": 3},
    {"url": "https://www.instagram.com/", "weight": 4},
    {"url": "https://portals.au.edu.pk/", "weight": 10},
    {"url": "https://chatgpt.com/", "weight": 15}
]

weighted_backend_servers = [
    server["url"] for server in backend_servers for _ in range(server["weight"])
]

health_status = {server["url"]: True for server in backend_servers}

HEALTH_CHECK_INTERVAL = 10

def health_check():
    """Periodically check the health of backend servers and store results in a JSON file."""
    print("Starting health checks for backend servers...\n")
    results = {}
    
    for server in backend_servers:
        url = server["url"]
        print(f"Checking health of: {url}")
        
        try:
            response = requests.head(url, timeout=2)
            if response.status_code == 200:
                health_status[url] = True
                results[url] = {"status": "healthy", "status_code": response.status_code}
                print(f"Backend {url} is healthy (Status: {response.status_code})")
            else:
                health_status[url] = False
                results[url] = {"status": "unhealthy", "status_code": response.status_code}
                print(f"Backend {url} is unhealthy (Status: {response.status_code})")
        except requests.RequestException as e:
            health_status[url] = False
            results[url] = {"status": "unreachable", "error": str(e)}
            print(f"Backend {url} is unreachable or encountered an error: {e}")
    
    with open("healthChecksForBackendServer.json", "w") as f:
        json.dump(results, f, indent=4)
    print("Health checks results have been saved to 'healthChecksForBackendServer.json'.")

def schedule_health_checks():
    def loop():
        while True:
            health_check()
            time.sleep(HEALTH_CHECK_INTERVAL)

    threading.Thread(target=loop, daemon=True).start()

@app.route("/")
def load_balancer():
    """Load balancer redirects requests to backend servers."""
    print("Incoming request for load balancing...")

    if "backend" in session and health_status.get(session["backend"], False):
        print(f"Redirecting to the same backend: {session['backend']}")
        return redirect(session["backend"], code=302)

    healthy_backend_servers = [
        url for url in weighted_backend_servers if health_status.get(url, False)
    ]
    if not healthy_backend_servers:
        print("No healthy backend servers available. Returning 503.")
        return "Service Unavailable", 503

    next_backend_server = random.choice(healthy_backend_servers)
    session["backend"] = next_backend_server
    print(f"Redirecting to a new backend: {next_backend_server}")
    return redirect(next_backend_server, code=302)

@app.route("/status")
def status():
    """Endpoint for monitoring which backend servers are being balanced."""
    print("Status request received, returning health status of backend servers.")
    return {"health_status": health_status}, 200

if __name__ == "__main__":
    print("Starting health checks...")

    health_check()
    schedule_health_checks()

    from os import environ
    port = int(environ.get("PORT", 5000))

    print(f"Health checks running. Starting Flask server on port {port}...\n")
    app.run(host="0.0.0.0", port=port)
