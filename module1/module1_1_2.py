from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"\n--- Incoming Request ---")
        print(f"Method: GET")
        print(f"Path: {self.path}")
        print(f"Headers: \n{self.headers}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        body = {"message": "hello, Master", "path_you_hit": self.path}
        self.wfile.write(json.dumps(body).encode())

    def do_POST(self):
        length = int(self.headers.get ("Content-Length", 0))
        raw_body = self.rfile.read(length)
        print(f"\n--- Incoming POST ---")
        print(f"Body received: {raw_body.decode()}")

        self.send_response(201)
        self.send_header ("Content-Type", "application/jason")
        self.end_headers ()
        self.wfile.write(json.dumps({"status": "created", "you_sent": raw_body.decode()}).encode())

    def do_PATCH(self):
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length)
        print(f"\n--- Incoming PATCH ---")
        print(f"Updating with: {raw_body.decode()}")


        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "updated"}).encode())

    def do_DELETE(self):
        print(f"\n--- Incoming DELETE ---")
        print(f"Path: {self.path}")

        self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    server = HTTPServer(("localhost", 8000), Handler)
    print("Server listening on http:///localhost:8000...") 
    server.serve_forever() 