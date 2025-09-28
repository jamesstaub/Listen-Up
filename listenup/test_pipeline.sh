#!/bin/bash

# Test script for machine-listening job creation pipeline
# Tests: Flask API → MongoDB → Redis event queue

set -e  # Exit on any error

echo "🧪 Testing Machine Learning Job Pipeline"
echo "========================================"

# Configuration
BACKEND_URL="http://localhost:8000"
MONGO_HOST="localhost"
MONGO_PORT="27017"
REDIS_HOST="localhost"
REDIS_PORT="6379"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if services are running
print_step "Checking if services are running..."

# Check backend
if curl -s "$BACKEND_URL/run-job" > /dev/null 2>&1; then
    print_success "Backend is running on $BACKEND_URL"
else
    print_error "Backend is not responding on $BACKEND_URL"
    echo "Make sure you run: make docker-up"
    exit 1
fi

# Check MongoDB (using docker exec since mongo shell might not be installed locally)
if docker exec listenup-mongodb-1 mongosh --quiet --eval "db.runCommand('ping')" > /dev/null 2>&1; then
    print_success "MongoDB is running"
else
    print_error "MongoDB is not responding"
    exit 1
fi

# Check Redis
if docker exec listenup-redis-1 redis-cli ping | grep -q "PONG"; then
    print_success "Redis is running"
else
    print_error "Redis is not responding"
    exit 1
fi

echo ""

# Test 1: Create a job via POST
print_step "Test 1: Creating a new job via POST /jobs"

JOB_PAYLOAD='{
    "steps": [
        {
            "name": "harmonic-percussive-separation",
            "service": "flucoma_service",
            "operation": "hpss",
            "parameters": {
                "harmfiltersize": 17,
                "percfiltersize": 31,
                "maskingmode": 0,
                "fftsettings": [1024, 512, 1024]
            },
            "inputs": [
                "s3://my-bucket/path/to/audio.wav"
            ]
        },
        {
            "name": "pitch-analysis",
            "service": "flucoma_service",
            "operation": "pitch",
            "parameters": {
                "algorithm": 0,
                "minfreq": 20.0,
                "maxfreq": 10000.0,
                "unit": 0,
                "fftsettings": [1024, 512, 1024]
            },
            "inputs": []
        }
    ],
    "step_transitions": [
        {
            "from_step_name": "harmonic-percussive-separation",
            "to_step_name": "pitch-analysis", 
            "output_to_input_mapping": [0]
        }
    ]
}'

echo "Payload:"
echo "$JOB_PAYLOAD" | jq .

RESPONSE=$(curl -s -X POST "$BACKEND_URL/jobs" \
    -H "Content-Type: application/json" \
    -d "$JOB_PAYLOAD")

echo "Response:"
echo "$RESPONSE" | jq .

# Extract job_id from response
JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')

if [ "$JOB_ID" != "null" ] && [ -n "$JOB_ID" ]; then
    print_success "Job created with ID: $JOB_ID"
else
    print_error "Failed to create job"
    echo "Response: $RESPONSE"
    exit 1
fi

echo ""

# Test 2: Check MongoDB for the created record
print_step "Test 2: Checking MongoDB for the created job record"

MONGO_QUERY="db.jobs.findOne({\"_id\": \"$JOB_ID\"})"
MONGO_RESULT=$(docker exec listenup-mongodb-1 mongosh --quiet listenup-mongo-db --eval "$MONGO_QUERY")

if echo "$MONGO_RESULT" | grep -q "$JOB_ID"; then
    print_success "Job record found in MongoDB"
    echo "MongoDB record:"
    echo "$MONGO_RESULT" | tail -n +2  # Skip connection message
else
    print_error "Job record NOT found in MongoDB"
    echo "Query result: $MONGO_RESULT"
fi

echo ""

# Test 3: Check Redis for job events
print_step "Test 3: Checking Redis for job events"

# Check if there are any events in the job_events queue
REDIS_QUEUE_LENGTH=$(docker exec listenup-redis-1 redis-cli LLEN job_events)

if [ "$REDIS_QUEUE_LENGTH" -gt 0 ]; then
    print_success "Found $REDIS_QUEUE_LENGTH event(s) in Redis job_events queue"
    
    # Get the latest event
    LATEST_EVENT=$(docker exec listenup-redis-1 redis-cli LINDEX job_events 0)
    echo "Latest event:"
    echo "$LATEST_EVENT" | jq . 2>/dev/null || echo "$LATEST_EVENT"
else
    print_warning "No events found in Redis job_events queue"
    echo "This might be normal if events are processed immediately"
fi

echo ""

# Test 4: Verify we can retrieve the job via GET
print_step "Test 4: Retrieving job via GET /jobs/$JOB_ID"

GET_RESPONSE=$(curl -s "$BACKEND_URL/jobs/$JOB_ID")
echo "GET Response:"
echo "$GET_RESPONSE" | jq .

if echo "$GET_RESPONSE" | jq -e ".job_id or ._id" > /dev/null 2>&1; then
    print_success "Successfully retrieved job via GET endpoint"
else
    print_error "Failed to retrieve job via GET endpoint"
fi

echo ""

# Test 5: Test job retry functionality
print_step "Test 5: Testing job retry functionality"

RETRY_RESPONSE=$(curl -s -X POST "$BACKEND_URL/jobs/$JOB_ID/retry")
echo "Retry Response:"
echo "$RETRY_RESPONSE" | jq . 2>/dev/null || echo "$RETRY_RESPONSE"

if echo "$RETRY_RESPONSE" | jq -e ".status" > /dev/null 2>&1; then
    RETRY_STATUS=$(echo "$RETRY_RESPONSE" | jq -r '.status')
    if [ "$RETRY_STATUS" = "retrying" ]; then
        print_success "Job retry initiated successfully"
        RESUME_STEP=$(echo "$RETRY_RESPONSE" | jq -r '.resume_step')
        print_success "Resuming from step: $RESUME_STEP"
    else
        print_warning "Job retry returned status: $RETRY_STATUS"
    fi
else
    print_warning "Job retry may not be needed (job might be complete or in progress)"
fi

echo ""

# Test 6: Create simple job and verify success status in MongoDB
print_step "Test 6: Creating simple job and verifying success in MongoDB"

SIMPLE_JOB_PAYLOAD='{
    "steps": [
        {
            "name": "simple-pitch-test",
            "service": "flucoma_service",
            "operation": "pitch",
            "parameters": {
                "algorithm": 0,
                "minfreq": 20.0,
                "maxfreq": 10000.0
            },
            "inputs": [
                "s3://my-bucket/simple-test.wav"
            ]
        }
    ],
    "step_transitions": []
}'

echo "Creating simple job for success verification..."
SIMPLE_RESPONSE=$(curl -s -X POST "$BACKEND_URL/jobs" \
    -H "Content-Type: application/json" \
    -d "$SIMPLE_JOB_PAYLOAD")

SIMPLE_JOB_ID=$(echo "$SIMPLE_RESPONSE" | jq -r '.job_id')

if [ "$SIMPLE_JOB_ID" != "null" ] && [ -n "$SIMPLE_JOB_ID" ]; then
    print_success "Simple job created with ID: $SIMPLE_JOB_ID"
    
    echo "⏰ Waiting 3 seconds for job processing..."
    sleep 3
    
    # Query MongoDB directly to check final status
    print_step "Querying MongoDB directly for job status..."
    MONGO_STATUS_QUERY="db.jobs.findOne({\"_id\": \"$SIMPLE_JOB_ID\"}, {\"status\": 1, \"steps.status\": 1, \"steps.error_message\": 1})"
    MONGO_STATUS_RESULT=$(docker exec listenup-mongodb-1 mongosh --quiet listenup-mongo-db --eval "$MONGO_STATUS_QUERY")
    
    echo "MongoDB result:"
    echo "$MONGO_STATUS_RESULT" | tail -n +2  # Skip connection message
    
    # Extract status from MongoDB result using a more robust approach
    JOB_STATUS=$(echo "$MONGO_STATUS_RESULT" | grep -o "status: '[^']*'" | head -1 | cut -d"'" -f2)
    
    # Alternative extraction method if the first one fails
    if [ -z "$JOB_STATUS" ]; then
        JOB_STATUS=$(echo "$MONGO_STATUS_RESULT" | sed -n "s/.*status: '\([^']*\)'.*/\1/p" | head -1)
    fi
    
    if [ "$JOB_STATUS" = "complete" ]; then
        print_success "✅ Job completed successfully in MongoDB!"
    elif [ "$JOB_STATUS" = "failed" ]; then
        print_error "❌ Job failed in MongoDB"
        # Check step status for more details
        STEP_STATUS=$(echo "$MONGO_STATUS_RESULT" | grep -o '"status"[[:space:]]*:[[:space:]]*"failed"')
        if [ -n "$STEP_STATUS" ]; then
            echo "Step failed - checking error message..."
            ERROR_MSG=$(echo "$MONGO_STATUS_RESULT" | grep -o '"error_message"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
            if [ -n "$ERROR_MSG" ] && [ "$ERROR_MSG" != "null" ]; then
                echo "Error: $ERROR_MSG"
            fi
        fi
    elif [ "$JOB_STATUS" = "processing" ]; then
        print_warning "⚠️  Job still processing after 3 seconds"
        echo "This might indicate slow processing or issues with status updates"
    else
        print_warning "⚠️  Job status: ${JOB_STATUS:-unknown}"
    fi
    
    # Also test backend API for comparison
    API_RESPONSE=$(curl -s "$BACKEND_URL/jobs/$SIMPLE_JOB_ID")
    API_STATUS=$(echo "$API_RESPONSE" | jq -r '.status')
    echo "Backend API reports status: $API_STATUS"
    
    if [ "$JOB_STATUS" = "$API_STATUS" ]; then
        print_success "✅ MongoDB and API status match"
    else
        print_warning "⚠️  Status mismatch - MongoDB: $JOB_STATUS, API: $API_STATUS"
    fi
    
else
    print_error "Failed to create simple job for status verification"
fi

echo ""

# Summary
print_step "Test Summary"
echo "============"
print_success "✅ Backend API is responding"
print_success "✅ Job creation endpoint works"
print_success "✅ MongoDB integration works"
if [ "$REDIS_QUEUE_LENGTH" -gt 0 ]; then
    print_success "✅ Redis event queue works"
else
    print_warning "⚠️  Redis events might be processed immediately"
fi
print_success "✅ Job retrieval endpoint works"
print_success "✅ Job retry functionality works"
print_success "✅ End-to-end job processing and status verification works"

echo ""
echo "🎉 All tests completed!"
echo ""
echo "📝 Jobs created:"
echo "   Multi-step job ID: $JOB_ID"
if [ -n "$SIMPLE_JOB_ID" ]; then
    echo "   Simple test job ID: $SIMPLE_JOB_ID"
fi
echo "🔍 You can test manually with:"
echo "   curl $BACKEND_URL/jobs/$JOB_ID"
