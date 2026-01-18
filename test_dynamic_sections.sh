#!/bin/bash

# Test script for dynamic section creation functionality

echo "Testing Dynamic Section Creation API..."

# Get authentication token
echo "Getting auth token..."
TOKEN=$(curl -s -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"superadmin","password":"superadmin"}' | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "Failed to get authentication token"
  exit 1
fi

echo "Auth token obtained successfully"

# Test creating a dynamic table
echo "Creating test dynamic table..."
RESPONSE=$(curl -s -X POST http://localhost:5000/admin/dynamic/tables \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "table_name": "test_education_sector",
    "fields": ["school_name", "student_count", "budget", "is_accredited"],
    "data_types": ["string", "int", "float", "bool"],
    "show_ui": [true, true, false, true]
  }')

echo "Create table response: $RESPONSE"

# Check if table was created successfully
if echo "$RESPONSE" | grep -q "created successfully"; then
  echo "✅ Table created successfully"

  # Test inserting data
  echo "Testing data insertion..."
  INSERT_RESPONSE=$(curl -s -X POST http://localhost:5000/admin/dynamic/tables/test_education_sector/data \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{
      "school_name": "Test School",
      "student_count": 500,
      "budget": 150000.50,
      "is_accredited": true
    }')

  echo "Insert data response: $INSERT_RESPONSE"

  # Test fetching data
  echo "Testing data retrieval..."
  FETCH_RESPONSE=$(curl -s -X GET http://localhost:5000/admin/dynamic/tables/test_education_sector/data \
    -H "Authorization: Bearer $TOKEN")

  echo "Fetch data response: $FETCH_RESPONSE"

  # Test metadata
  echo "Testing metadata retrieval..."
  META_RESPONSE=$(curl -s -X GET http://localhost:5000/admin/dynamic/tables/test_education_sector/metadata \
    -H "Authorization: Bearer $TOKEN")

  echo "Metadata response: $META_RESPONSE"

else
  echo "❌ Table creation failed"
fi

echo "Test completed!"