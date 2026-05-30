#!/bin/bash
# Test runner script for AgentWatch
#
# Prerequisites:
#   pip install -r requirements-test.txt
#
# Usage:
#   ./run_tests.sh                    # Run all tests
#   ./run_tests.sh backend           # Run backend tests only
#   ./run_tests.sh sdk               # Run SDK tests only
#   ./run_tests.sh coverage          # Run with coverage report

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}AgentWatch Test Suite${NC}"
echo "================================"

# Check if pytest is installed
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${RED}Error: pytest not installed${NC}"
    echo "Please run: pip install -r requirements-test.txt"
    exit 1
fi

# Default: run all tests
TEST_PATH="tests/"
COV_FLAGS=""

case "${1:-all}" in
    backend)
        echo -e "${YELLOW}Running backend tests only...${NC}"
        TEST_PATH="tests/backend/"
        COV_FLAGS="--cov=backend"
        ;;
    sdk)
        echo -e "${YELLOW}Running SDK tests only...${NC}"
        TEST_PATH="tests/sdk/"
        COV_FLAGS="--cov=sdk"
        ;;
    coverage)
        echo -e "${YELLOW}Running all tests with coverage...${NC}"
        TEST_PATH="tests/"
        COV_FLAGS="--cov=backend --cov=sdk --cov-report=html --cov-report=term-missing"
        ;;
    all)
        echo -e "${YELLOW}Running all tests...${NC}"
        TEST_PATH="tests/"
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo "Usage: $0 [backend|sdk|coverage|all]"
        exit 1
        ;;
esac

# Run tests
python3 -m pytest $TEST_PATH $COV_FLAGS -v

# Print coverage summary
if [ "$1" == "coverage" ]; then
    echo ""
    echo -e "${GREEN}Coverage report generated at: htmlcov/index.html${NC}"
fi

echo ""
echo -e "${GREEN}Tests completed successfully!${NC}"
