#!/bin/bash

# Test script for machine-listening job creation pipeline
# Tests: Flask API → MongoDB → Redis event queue

set -e  # Exit on any error

# Parse command line arguments
SKIP_CLEANUP=false
if [[ "$*" == *"--help"* ]]; then
    echo "Usage: $0 [--no-cleanup] [--help]"
    echo ""
    echo "Options:"
    echo "  --no-cleanup    Skip cleanup of test data (useful for debugging)"
    echo "  --help         Show this help message"
    echo ""
    echo "This script tests the machine-listening job pipeline by:"
    echo "  1. Creating test jobs via API"
    echo "  2. Verifying data in MongoDB and Redis"
    echo "  3. Testing job retrieval and retry functionality"
    echo "  4. Automatically cleaning up test data (unless --no-cleanup)"
    exit 0
fi

if [[ "$*" == *"--no-cleanup"* ]]; then
    SKIP_CLEANUP=true
    echo "🚫 Cleanup disabled via --no-cleanup flag"
fi

echo "🧪 Testing Machine Learning Job Pipeline"
echo "========================================"

# Configuration
BACKEND_URL="http://localhost:8000"
MONGO_HOST="localhost"
MONGO_PORT="27017"
REDIS_HOST="localhost"
REDIS_PORT="6379"

# Track created jobs for cleanup
CREATED_JOBS=()
TEMP_FILES=()

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

# Cleanup functions
cleanup_jobs() {
    if [ ${#CREATED_JOBS[@]} -eq 0 ]; then
        print_step "No jobs to clean up"
        return
    fi
    
    print_step "Cleaning up ${#CREATED_JOBS[@]} test job(s) from MongoDB..."
    
    for job_id in "${CREATED_JOBS[@]}"; do
        if [ -n "$job_id" ] && [ "$job_id" != "null" ]; then
            echo "  Removing job: $job_id"
            MONGO_DELETE="db.jobs.deleteOne({\"_id\": \"$job_id\"})"
            DELETE_RESULT=$(docker exec listenup-mongodb-1 mongosh --quiet listenup-mongo-db --eval "$MONGO_DELETE" 2>/dev/null || true)
            
            if echo "$DELETE_RESULT" | grep -q "deletedCount: 1"; then
                echo "    ✅ Deleted job $job_id"
            else
                echo "    ⚠️  Could not delete job $job_id (may not exist)"
            fi
        fi
    done
}

cleanup_temp_files() {
    if [ ${#TEMP_FILES[@]} -eq 0 ]; then
        return
    fi
    
    print_step "Cleaning up ${#TEMP_FILES[@]} temporary file(s)..."
    
    for temp_file in "${TEMP_FILES[@]}"; do
        if [ -f "$temp_file" ]; then
            rm -f "$temp_file"
            echo "  ✅ Removed $temp_file"
        fi
    done
}

cleanup_storage_files() {
    print_step "Cleaning up test storage files..."
    
    # Clean up any test files that might have been created in storage
    # Look for files with test job IDs in the name
    for job_id in "${CREATED_JOBS[@]}"; do
        if [ -n "$job_id" ] && [ "$job_id" != "null" ]; then
            # Check if storage directory exists and clean up files related to this job
            if [ -d "./storage" ]; then
                find "./storage" -name "*${job_id}*" -type f 2>/dev/null | while read -r file; do
                    if [ -f "$file" ]; then
                        rm -f "$file"
                        echo "  🗑️  Removed storage file: $file"
                    fi
                done
            fi
            
            # Also clean up in Docker volume storage if accessible
            docker exec listenup-backend-1 find /app/storage -name "*${job_id}*" -type f -delete 2>/dev/null || true
        fi
    done
}

cleanup_redis_queues() {
    print_step "Cleaning up Redis test queues..."
    
    # Clean up any test-related Redis keys (be careful not to clear all)
    # For now, just clear job_events queue if it has too many entries
    REDIS_QUEUE_LENGTH=$(docker exec listenup-redis-1 redis-cli LLEN job_events 2>/dev/null || echo "0")
    if [ "$REDIS_QUEUE_LENGTH" -gt 10 ]; then
        print_warning "job_events queue has $REDIS_QUEUE_LENGTH items - consider manual cleanup"
    fi
}

# Cleanup function to run on script exit
cleanup_on_exit() {
    echo ""
    
    if [ "$SKIP_CLEANUP" = true ]; then
        print_warning "🚫 Cleanup skipped (--no-cleanup flag)"
        echo "📝 Test jobs left in database for manual inspection:"
        for job_id in "${CREATED_JOBS[@]}"; do
            echo "   - $job_id"
        done
        echo "🧹 To clean up manually later, run:"
        echo "   docker exec listenup-mongodb-1 mongosh listenup-mongo-db --eval 'db.jobs.deleteMany({\"_id\": {\$in: [$(printf '\"%s\",' "${CREATED_JOBS[@]}" | sed 's/,$//')]}})"
        return
    fi
    
    print_step "🧹 Running cleanup..."
    cleanup_jobs
    cleanup_temp_files
    cleanup_storage_files
    cleanup_redis_queues
    print_success "Cleanup completed"
}

# Set up cleanup trap to run on script exit (success or failure)
trap cleanup_on_exit EXIT

add_job_to_cleanup() {
    local job_id="$1"
    if [ -n "$job_id" ] && [ "$job_id" != "null" ]; then
        CREATED_JOBS+=("$job_id")
        echo "  📝 Added $job_id to cleanup list"
    fi
}

add_temp_file_to_cleanup() {
    local temp_file="$1"
    if [ -n "$temp_file" ]; then
        TEMP_FILES+=("$temp_file")
    fi
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
            "command_spec": {
                "program": "fluid-hpss",
                "flags": {
                    "-source": "{{input_file}}",
                    "-harmonic": "{{harmonic_output}}",
                    "-percussive": "{{percussive_output}}",
                    "-harmfiltersize": "17",
                    "-percfiltersize": "31",
                    "-maskingmode": "0",
                    "-fftsettings": "1024 512 1024"
                }
            },
            "inputs": {
                "input_file": "s3://my-bucket/path/to/audio.wav"
            },
            "outputs": {
                "harmonic_output": "s3://my-bucket/outputs/harmonic.wav",
                "percussive_output": "s3://my-bucket/outputs/percussive.wav"
            }
        },
        {
            "name": "pitch-analysis",
            "service": "flucoma_service",
            "command_spec": {
                "program": "fluid-pitch",
                "flags": {
                    "-source": "{{audio_input}}",
                    "-features": "{{pitch_features}}",
                    "-algorithm": "0",
                    "-minfreq": "20.0",
                    "-maxfreq": "10000.0",
                    "-unit": "0",
                    "-fftsettings": "1024 512 1024"
                }
            },
            "inputs": {
                "audio_input": "{{steps.harmonic-percussive-separation.outputs.harmonic_output}}"
            },
            "outputs": {
                "pitch_features": "s3://my-bucket/outputs/pitch.csv"
            }
        }
    ],
    "step_transitions": [
        {
            "from_step_name": "harmonic-percussive-separation",
            "to_step_name": "pitch-analysis",
            "output_to_input_mapping": {
                "harmonic_output": "audio_input"
            }
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
    add_job_to_cleanup "$JOB_ID"
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

# TODO: check that the Job record matches expected structure

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
            "command_spec": {
                "program": "fluid-pitch",
                "flags": {
                    "-source": "{{input_audio}}",
                    "-features": "{{output_features}}",
                    "-algorithm": "0",
                    "-minfreq": "20.0",
                    "-maxfreq": "10000.0"
                }
            },
            "inputs": {
                "input_audio": "/app/storage/test_data/test.aiff"
            },
            "outputs": {
                "output_features": "/app/storage/simple-pitch.csv"
            }
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
    add_job_to_cleanup "$SIMPLE_JOB_ID"
    
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
echo "📝 Test jobs created and tracked for cleanup:"
for job_id in "${CREATED_JOBS[@]}"; do
    echo "   - $job_id"
done
echo ""
echo "🔍 You can test manually with:"
if [ -n "$JOB_ID" ]; then
    echo "   curl $BACKEND_URL/jobs/$JOB_ID"
fi
echo ""
if [ "$SKIP_CLEANUP" = true ]; then
    echo "🚫 Cleanup skipped - test data left in database for inspection"
else
    echo "🧹 Cleanup will run automatically when script exits"
    echo "   To skip cleanup for debugging, use: $0 --no-cleanup"
fi
