#!/bin/bash

# ============================================================================
# Quick Test Runner Script
# Usage: ./run-tests.sh [service] [options]
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}AI-Assistant Test Runner${NC}"
echo "======================================"

# Parse arguments
SERVICE=${1:-all}
COVERAGE=${2:-yes}

# Function to run tests for a service
run_service_tests() {
    local service=$1
    local test_path=$2
    
    echo -e "\n${YELLOW}Testing $service...${NC}"
    
    if [ ! -d "$test_path" ]; then
        echo -e "${RED}Test directory not found: $test_path${NC}"
        return 1
    fi
    
    cd "$test_path/.." || return 1
    
    if [ "$COVERAGE" = "yes" ]; then
        pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing
    else
        pytest tests/ -v
    fi
    
    cd - > /dev/null || return 1
}

# Install test dependencies if needed
install_test_deps() {
    if ! command -v pytest &> /dev/null; then
        echo -e "${YELLOW}Installing test dependencies...${NC}"
        pip install pytest pytest-cov pytest-mock pytest-flask requests-mock
    fi
}

# Main execution
main() {
    install_test_deps
    
    case $SERVICE in
        chatbot|ChatBot)
            run_service_tests "ChatBot" "ChatBot/tests"
            ;;
        text2sql|Text2SQL)
            run_service_tests "Text2SQL" "Text2SQL Services/tests"
            ;;
        speech2text|Speech2Text)
            run_service_tests "Speech2Text" "Speech2Text Services/tests"
            ;;
        document|DocumentIntelligence|dis)
            run_service_tests "Document Intelligence" "Document Intelligence Service/tests"
            ;;
        rag|RAG|RAGServices)
            run_service_tests "RAG Services" "RAG Services/tests"
            ;;
        all)
            echo -e "${GREEN}Running all tests...${NC}"
            run_service_tests "ChatBot" "ChatBot/tests"
            run_service_tests "Text2SQL" "Text2SQL Services/tests"
            run_service_tests "Speech2Text" "Speech2Text Services/tests"
            run_service_tests "Document Intelligence" "Document Intelligence Service/tests"
            run_service_tests "RAG Services" "RAG Services/tests"
            ;;
        *)
            echo -e "${RED}Unknown service: $SERVICE${NC}"
            echo "Available services: chatbot, text2sql, speech2text, document, rag, all"
            exit 1
            ;;
    esac
    
    echo -e "\n${GREEN}✓ Tests completed!${NC}"
}

# Run main
main
