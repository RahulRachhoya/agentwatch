#!/usr/bin/env python3
"""
Validate security changes in the codebase without running the server.
This script checks that security controls are properly implemented.
"""

import os
import re
import sys

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def check_passed(message):
    print(f"{GREEN}✓ PASS{NC}: {message}")
    return True


def check_failed(message):
    print(f"{RED}✗ FAIL{NC}: {message}")
    return False


def check_info(message):
    print(f"{YELLOW}ℹ INFO{NC}: {message}")


def main():
    print(f"\n{YELLOW}{'=' * 60}{NC}")
    print(f"{YELLOW}AgentWatch Security Validation{NC}")
    print(f"{YELLOW}{'=' * 60}{NC}\n")

    passed = 0
    failed = 0

    backend_main = os.path.join(os.path.dirname(__file__), "..", "backend", "main.py")
    backend_auth = os.path.join(os.path.dirname(__file__), "..", "backend", "auth.py")
    requirements = os.path.join(os.path.dirname(__file__), "..", "backend", "requirements.txt")
    readme = os.path.join(os.path.dirname(__file__), "..", "README.md")

    # Check 1: WebSocket authentication
    print("\n1. Checking WebSocket authentication...")
    with open(backend_main, "r") as f:
        content = f.read()
        if "verify_websocket_api_key" in content and "websocket.close" in content:
            if check_passed("WebSocket authentication function implemented"):
                passed += 1
        else:
            if check_failed("WebSocket authentication missing"):
                failed += 1

    # Check 2: Rate limiting
    print("\n2. Checking rate limiting...")
    with open(backend_main, "r") as f:
        content = f.read()
        if "@limiter.limit" in content and "slowapi" in content:
            if check_passed("Rate limiting decorator applied"):
                passed += 1
        else:
            if check_failed("Rate limiting not configured"):
                failed += 1

    # Check 3: slowapi dependency
    print("\n3. Checking slowapi dependency...")
    with open(requirements, "r") as f:
        content = f.read()
        if "slowapi" in content:
            if check_passed("slowapi dependency added to requirements.txt"):
                passed += 1
        else:
            if check_failed("slowapi missing from requirements.txt"):
                failed += 1

    # Check 4: CORS configuration
    print("\n4. Checking CORS configuration...")
    with open(backend_main, "r") as f:
        content = f.read()
        if "ALLOWED_ORIGINS" in content and 'os.getenv("ALLOWED_ORIGINS"' in content:
            if check_passed("CORS configuration uses environment variable"):
                passed += 1
        else:
            if check_failed("CORS not properly configured"):
                failed += 1

    # Check 5: Global exception handler
    print("\n5. Checking global exception handler...")
    with open(backend_main, "r") as f:
        content = f.read()
        if "@app.exception_handler(Exception)" in content and "global_exception_handler" in content:
            if check_passed("Global exception handler implemented"):
                passed += 1
        else:
            if check_failed("Global exception handler missing"):
                failed += 1

    # Check 6: Timing-safe comparison
    print("\n6. Checking timing-safe comparison in auth...")
    with open(backend_auth, "r") as f:
        content = f.read()
        if "secrets.compare_digest" in content:
            if check_passed("Timing-safe comparison used in auth"):
                passed += 1
        else:
            if check_failed("Not using timing-safe comparison"):
                failed += 1

    # Check 7: Security documentation
    print("\n7. Checking README security documentation...")
    with open(readme, "r") as f:
        content = f.read()
        if "Security Configuration" in content and "AGENTWATCH_API_KEY" in content:
            if check_passed("Security configuration documented in README"):
                passed += 1
        else:
            if check_failed("Security documentation missing from README"):
                failed += 1

    # Check 8: No hardcoded secrets
    print("\n8. Checking for hardcoded secrets...")
    hardcoded_patterns = [
        (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
        (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
        (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
    ]

    found_secrets = False
    with open(backend_main, "r") as f:
        content = f.read()
        for pattern, desc in hardcoded_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            # Filter out false positives (env var usage, comments)
            matches = [m for m in matches if "os.getenv" not in m and "environ" not in m]
            if matches:
                check_failed(f"{desc} found: {matches[0][:50]}")
                found_secrets = True
                failed += 1

    if not found_secrets:
        if check_passed("No hardcoded secrets detected"):
            passed += 1

    # Check 9: Rate limit on high-volume endpoint
    print("\n9. Checking rate limit on /v1/spans/batch...")
    with open(backend_main, "r") as f:
        content = f.read()
        # Find the create_spans function
        spans_func_match = re.search(
            r'@app\.post\("/v1/spans/batch".*?\n.*?@limiter\.limit.*?\n.*?async def create_spans',
            content,
            re.DOTALL
        )
        if spans_func_match:
            if check_passed("Rate limit applied to /v1/spans/batch endpoint"):
                passed += 1
        else:
            if check_failed("Rate limit missing on /v1/spans/batch"):
                failed += 1

    # Check 10: WebSocket API key verification
    print("\n10. Checking WebSocket endpoint calls auth verification...")
    with open(backend_main, "r") as f:
        content = f.read()
        ws_func_match = re.search(
            r'@app\.websocket\("/ws"\).*?verify_websocket_api_key',
            content,
            re.DOTALL
        )
        if ws_func_match:
            if check_passed("WebSocket endpoint verifies API key"):
                passed += 1
        else:
            if check_failed("WebSocket endpoint doesn't verify API key"):
                failed += 1

    # Summary
    print(f"\n{YELLOW}{'=' * 60}{NC}")
    print(f"{YELLOW}Validation Summary{NC}")
    print(f"{YELLOW}{'=' * 60}{NC}\n")

    total = passed + failed
    print(f"Total Checks: {total}")
    print(f"{GREEN}Passed: {passed}{NC}")
    print(f"{RED}Failed: {failed}{NC}")
    print()

    if failed == 0:
        print(f"{GREEN}✓ All security controls properly implemented!{NC}\n")
        return 0
    else:
        print(f"{RED}✗ Some security checks failed. Review the output above.{NC}\n")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n{RED}Validation failed with error: {e}{NC}\n")
        sys.exit(1)
