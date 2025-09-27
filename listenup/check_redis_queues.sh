#!/bin/bash

# Script to check Redis queue contents
echo "🔍 Checking Redis queue contents..."

# Function to check a specific queue
check_queue() {
    local queue_name=$1
    echo ""
    echo "📋 Queue: $queue_name"
    echo "   Length: $(docker-compose exec -T redis redis-cli LLEN "$queue_name")"
    
    # Show first few items in queue
    local length=$(docker-compose exec -T redis redis-cli LLEN "$queue_name")
    if [ "$length" -gt 0 ]; then
        echo "   First item:"
        docker-compose exec -T redis redis-cli LINDEX "$queue_name" 0 | head -5
        echo "   ..."
    fi
}

# Check all relevant queues
check_queue "flucoma_service_queue"
check_queue "librosa_service_queue"
check_queue "job_step_events"
check_queue "job_status_events"

echo ""
echo "🗃️  All Redis keys:"
docker-compose exec -T redis redis-cli KEYS "*queue*"

echo ""
echo "📊 Queue lengths summary:"
for queue in flucoma_service_queue librosa_service_queue job_step_events job_status_events; do
    length=$(docker-compose exec -T redis redis-cli LLEN "$queue")
    echo "   $queue: $length items"
done
