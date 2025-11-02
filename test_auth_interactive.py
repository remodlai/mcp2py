#!/usr/bin/env python3
"""Interactive test script for authentication.

Start the bearer server first:
    python tests/test_server_bearer.py

Then run this script:
    python test_auth_interactive.py
"""

from mcp2py import load

print("=" * 70)
print("Testing mcp2py Authentication")
print("=" * 70)
print()

print("1. Testing Bearer Token Authentication")
print("-" * 70)

try:
    # Test with correct token
    print("Connecting with correct token...")
    server = load(
        "http://localhost:8000/sse",
        headers={"Authorization": "Bearer test-token-12345"}
    )

    print("✓ Connection successful!")

    # Test echo
    result = server.echo(message="Hello from mcp2py!")
    print(f"✓ Echo: {result}")

    # Test add
    result = server.add(a=10, b=32)
    print(f"✓ Add: {result}")

    # Test user info
    result = server.get_user_info()
    print(f"✓ User info: {result}")

    server.close()
    print("✓ Server closed")

except Exception as e:
    print(f"✗ Error: {e}")

print()
print("-" * 70)

# Test with wrong token
print("2. Testing Invalid Token (should fail)")
print("-" * 70)

try:
    print("Connecting with invalid token...")
    server = load(
        "http://localhost:8000/sse",
        headers={"Authorization": "Bearer wrong-token"}
    )
    print("✗ Connection should have failed!")
    server.close()

except RuntimeError as e:
    print(f"✓ Correctly rejected: {type(e).__name__}")

print()
print("-" * 70)

# Test with no token
print("3. Testing No Token (should fail)")
print("-" * 70)

try:
    print("Connecting without token...")
    server = load("http://localhost:8000/sse")
    print("✗ Connection should have failed!")
    server.close()

except RuntimeError as e:
    print(f"✓ Correctly rejected: {type(e).__name__}")

print()
print("=" * 70)
print("✅ All authentication tests completed!")
print("=" * 70)
