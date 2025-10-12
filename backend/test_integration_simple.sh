#!/bin/bash

# Quick Integration Test - Financial Advisor AI
# Tests the main integration workflow

API_URL="http://localhost:8000"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzYwOTE2MzU3LCJpYXQiOjE3NjAzMTE1NTcsInR5cGUiOiJzZXNzaW9uIn0.GuaY0kkyVXCjrLpWLPQXddC5zYs_WE_FemWWqku2AhM"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}============================================"
echo "  INTEGRATION TEST - 3 SERVICES"
echo "============================================${NC}\n"

# Test 1: Find Sara Smith in HubSpot
echo -e "${GREEN}TEST 1: HubSpot - Search Contact${NC}"
curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -b "session=$TOKEN" \
  -d '{"message":"Busque Sara Smith no HubSpot"}' | \
  grep -o '"content":"[^"]*"' | head -1 | sed 's/"content":"//;s/"$//'
echo -e "\n"

sleep 2

# Test 2: Schedule meeting
echo -e "${GREEN}TEST 2: Calendar - Schedule Meeting${NC}"
curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -b "session=$TOKEN" \
  -d '{"message":"Agende uma reunião com Sara Smith para amanhã às 14:00, duração 1 hora"}' | \
  grep -o '"content":"[^"]*"' | head -1 | sed 's/"content":"//;s/"$//'
echo -e "\n"

sleep 2

# Test 3: Send email
echo -e "${GREEN}TEST 3: Gmail - Send Email${NC}"
curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -b "session=$TOKEN" \
  -d '{"message":"Envie um email para sara.smith@example.com confirmando a reunião"}' | \
  grep -o '"content":"[^"]*"' | head -1 | sed 's/"content":"//;s/"$//'
echo -e "\n"

sleep 2

# Test 4: Add note to contact
echo -e "${GREEN}TEST 4: HubSpot - Add Note${NC}"
curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -b "session=$TOKEN" \
  -d '{"message":"Adicione uma nota na Sara Smith: Reunião agendada para amanhã"}' | \
  grep -o '"content":"[^"]*"' | head -1 | sed 's/"content":"//;s/"$//'
echo -e "\n"

sleep 2

# Test 5: Complex workflow
echo -e "${GREEN}TEST 5: INTEGRATED - Search + Calendar + Email${NC}"
curl -s -X POST "$API_URL/api/chat" \
  -H "Content-Type: application/json" \
  -b "session=$TOKEN" \
  -d '{"message":"Busque Mike Johnson no HubSpot, veja se tenho reunião com ele, e me envie um resumo"}' | \
  grep -o '"content":"[^"]*"' | head -1 | sed 's/"content":"//;s/"$//'
echo -e "\n"

echo -e "${BLUE}============================================"
echo "  TEST COMPLETED"
echo "============================================${NC}"
