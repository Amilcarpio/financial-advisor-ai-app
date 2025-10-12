#!/bin/bash

# Financial Advisor AI - Complete Service Integration Test
# Tests: Gmail, Google Calendar, HubSpot CRM
# Date: 2025-10-12

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# API Config
API_URL="http://localhost:8000"
SESSION_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzYwOTE2MzU3LCJpYXQiOjE3NjAzMTE1NTcsInR5cGUiOiJzZXNzaW9uIn0.GuaY0kkyVXCjrLpWLPQXddC5zYs_WE_FemWWqku2AhM"

# Helper function to make chat requests
chat() {
    local message="$1"
    echo -e "${BLUE}[REQUEST]${NC} $message"
    
    response=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -b "session=$SESSION_TOKEN" \
        -d "{\"message\": \"$message\"}" \
        --no-buffer)
    
    # Extract content from streaming response
    content=$(echo "$response" | grep -o '"content":"[^"]*"' | head -1 | sed 's/"content":"//;s/"$//' | sed 's/\\n/\n/g')
    
    if [ -n "$content" ]; then
        echo -e "${GREEN}[RESPONSE]${NC} $content\n"
    else
        echo -e "${YELLOW}[RESPONSE]${NC} (streaming/tool execution)\n"
    fi
    
    sleep 2
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  FINANCIAL ADVISOR AI - SERVICE TEST  ${NC}"
echo -e "${BLUE}========================================${NC}\n"

# ============================================
# TEST 1: HubSpot CRM - Contact Management
# ============================================
echo -e "${YELLOW}=== TEST 1: HubSpot CRM - Contact Search ===${NC}"

echo -e "\n${BLUE}1.1 - Searching for existing contact: Sara Smith${NC}"
chat "Busque o contato Sara Smith no HubSpot"

echo -e "\n${BLUE}1.2 - List all contacts${NC}"
chat "Liste todos os meus contatos do HubSpot"

echo -e "\n${BLUE}1.3 - Search contact by email${NC}"
chat "Busque o contato com email sara.smith@example.com"

# ============================================
# TEST 2: HubSpot CRM - Create Note
# ============================================
echo -e "\n${YELLOW}=== TEST 2: HubSpot CRM - Create Note ===${NC}"

echo -e "\n${BLUE}2.1 - Add note to Sara Smith${NC}"
chat "Adicione uma nota no contato da Sara Smith: Cliente VIP - Reunião agendada para discutir investimentos"

# ============================================
# TEST 3: HubSpot CRM - Update Contact
# ============================================
echo -e "\n${YELLOW}=== TEST 3: HubSpot CRM - Update Contact ===${NC}"

echo -e "\n${BLUE}3.1 - Update Sara Smith lifecycle stage${NC}"
chat "Atualize o contato Sara Smith para lifecycle stage 'customer'"

# ============================================
# TEST 4: Google Calendar - Search Events
# ============================================
echo -e "\n${YELLOW}=== TEST 4: Google Calendar - Search Events ===${NC}"

echo -e "\n${BLUE}4.1 - List upcoming events${NC}"
chat "Quais são meus próximos eventos no calendário?"

echo -e "\n${BLUE}4.2 - Search events with Sara Smith${NC}"
chat "Busque eventos com Sara Smith no calendário"

# ============================================
# TEST 5: Google Calendar - Create Event
# ============================================
echo -e "\n${YELLOW}=== TEST 5: Google Calendar - Create Event ===${NC}"

echo -e "\n${BLUE}5.1 - Schedule meeting with Sara Smith${NC}"
chat "Agende uma reunião com Sara Smith para amanhã às 15:00, duração de 1 hora, título: 'Revisão de Portfólio', localização: Google Meet"

# ============================================
# TEST 6: Google Calendar - Update Event
# ============================================
echo -e "\n${YELLOW}=== TEST 6: Google Calendar - Update Event ===${NC}"

echo -e "\n${BLUE}6.1 - Update meeting time${NC}"
chat "Remarca a reunião 'Revisão de Portfólio' para 16:00"

# ============================================
# TEST 7: Gmail - Search Emails
# ============================================
echo -e "\n${YELLOW}=== TEST 7: Gmail - Search Emails ===${NC}"

echo -e "\n${BLUE}7.1 - Search emails from Sara Smith${NC}"
chat "Busque emails de sara.smith@example.com"

echo -e "\n${BLUE}7.2 - Search recent emails${NC}"
chat "Mostre os últimos 5 emails recebidos"

# ============================================
# TEST 8: Gmail - Send Email
# ============================================
echo -e "\n${YELLOW}=== TEST 8: Gmail - Send Email ===${NC}"

echo -e "\n${BLUE}8.1 - Send confirmation email${NC}"
chat "Envie um email para sara.smith@example.com com assunto 'Confirmação de Reunião' e corpo: 'Olá Sara, confirmo nossa reunião de amanhã às 16:00 para revisar seu portfólio. Até lá!'"

# ============================================
# TEST 9: Google Calendar - Cancel Event
# ============================================
echo -e "\n${YELLOW}=== TEST 9: Google Calendar - Cancel Event ===${NC}"

echo -e "\n${BLUE}9.1 - Cancel meeting${NC}"
chat "Cancele a reunião 'Revisão de Portfólio'"

# ============================================
# TEST 10: INTEGRATED WORKFLOW
# ============================================
echo -e "\n${YELLOW}=== TEST 10: INTEGRATED WORKFLOW ===${NC}"
echo -e "${BLUE}Full workflow: Search contact → Schedule meeting → Send email${NC}\n"

echo -e "\n${BLUE}10.1 - Search contact Mike Johnson${NC}"
chat "Busque o contato Mike Johnson no HubSpot"

echo -e "\n${BLUE}10.2 - Schedule meeting with Mike${NC}"
chat "Agende uma reunião com Mike Johnson para segunda-feira às 10:00, duração 30 minutos, título: 'Follow-up Investimentos'"

echo -e "\n${BLUE}10.3 - Send confirmation email to Mike${NC}"
chat "Envie um email para mike.johnson@example.com confirmando a reunião de segunda-feira às 10:00"

echo -e "\n${BLUE}10.4 - Add note to Mike's contact${NC}"
chat "Adicione uma nota no Mike Johnson: Follow-up agendado - Cliente demonstrou interesse em diversificação"

# ============================================
# TEST 11: COMPLEX MULTI-SERVICE QUERY
# ============================================
echo -e "\n${YELLOW}=== TEST 11: COMPLEX QUERY ===${NC}"

echo -e "\n${BLUE}11.1 - Multi-step workflow${NC}"
chat "Busque o contato Sara Smith no HubSpot, verifique se tenho alguma reunião agendada com ela, e se tiver, me mostre os últimos emails que trocamos"

# ============================================
# TEST 12: Error Handling
# ============================================
echo -e "\n${YELLOW}=== TEST 12: ERROR HANDLING ===${NC}"

echo -e "\n${BLUE}12.1 - Search non-existent contact${NC}"
chat "Busque o contato João da Silva no HubSpot"

echo -e "\n${BLUE}12.2 - Try to create duplicate contact${NC}"
chat "Crie um contato no HubSpot com email sara.smith@example.com, nome Sara, sobrenome Smith"

# ============================================
# SUMMARY
# ============================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  TEST SUITE COMPLETED${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${BLUE}Services Tested:${NC}"
echo -e "  ✓ HubSpot CRM (search, create note, update)"
echo -e "  ✓ Google Calendar (list, create, update, cancel)"
echo -e "  ✓ Gmail (search, send)"
echo -e "  ✓ Integrated workflows"
echo -e "  ✓ Error handling\n"

echo -e "${YELLOW}Check the responses above for any errors or unexpected behavior.${NC}"
echo -e "${YELLOW}You can review backend logs with: docker-compose logs backend --tail=100${NC}\n"
