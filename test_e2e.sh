#!/bin/bash

# Usage: ./test_e2e.sh [--incremental|--persist] [--no-cache]
# Arguments:
#   --incremental: Run Full Production Flow (scrape then verify as separate executions) - default
#   --persist: Run Loop/Persistent mode (runs continuously)
#   --no-cache: Build Docker images without cache

TEST_MODE=""
BUILD_NO_CACHE="N"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --incremental)
            TEST_MODE="production"
            shift
            ;;
        --persist)
            TEST_MODE="loop"
            shift
            ;;
        --no-cache)
            BUILD_NO_CACHE="y"
            shift
            ;;
        --help|-h)
            echo "Usage: ./test_e2e.sh [--incremental|--persist] [--no-cache]"
            echo ""
            echo "Arguments:"
            echo "  --incremental: Run Full Production Flow (scrape then verify) - default"
            echo "  --persist: Run Loop/Persistent mode (runs continuously)"
            echo "  --no-cache: Build Docker images without cache"
            echo ""
            echo "Environment Variables:"
            echo "  ENABLED_SCRAPERS: Comma-separated list of scrapers (default: BAREKET)"
            echo "  LIMIT: Maximum number of files to download (default: 10)"
            echo "  APP_DATA_PATH: Path for test data (default: ./test_data)"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: ./test_e2e.sh [--incremental|--persist] [--no-cache]"
            echo "Use --help for more information"
            exit 1
            ;;
    esac
done

# If test mode not provided via flags, default to incremental
if [ -z "$TEST_MODE" ]; then
    TEST_MODE="production"
fi

# Colors for output
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
RESET='\033[0m'

# Helper functions
print_step() {
    local step_num=$1
    local message=$2
    echo -e "\n${YELLOW}Step ${step_num}: ${message}${RESET}"
}

print_error() {
    echo -e "${RED}$1${RESET}"
}

print_success() {
    echo -e "${GREEN}✓ $1${RESET}"
}

# Function to check container health
check_container_health() {
    local container_name=$1
    local retries=20
    local wait_seconds=5
    local i=0

    # First, verify container exists (running or stopped)
    if ! docker ps -a --format "{{.Names}}" | grep -q "^${container_name}$"; then
        print_error "$container_name does not exist."
        return 1
    fi

    # Verify container is running
    if ! docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        print_error "$container_name is not running."
        exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$container_name" 2>/dev/null || echo "unknown")
        echo "Container exit code: $exit_code"
        return 1
    fi

    # Check if health check is configured
    has_healthcheck=$(docker inspect --format='{{.Config.Healthcheck}}' "$container_name" 2>/dev/null)
    if [ -z "$has_healthcheck" ] || [ "$has_healthcheck" == "<no value>" ]; then
        # No health check configured, just verify container is running
        print_success "$container_name is running (no health check configured)."
        return 0
    fi

    # Health check is configured, wait for healthy status
    while [ $i -lt $retries ]; do
        health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null)
        if [ "$health_status" == "healthy" ]; then
            print_success "$container_name is healthy."
            return 0
        elif [ "$health_status" == "unhealthy" ]; then
            print_error "$container_name is unhealthy. Exiting."
            return 1
        else
            echo "Waiting for $container_name to become healthy... ($((i+1))/$retries)"
            sleep $wait_seconds
        fi
        i=$((i+1))
    done

    print_error "Timeout waiting for $container_name to become healthy. Exiting."
    return 1
}

# Function to verify container started successfully and check initial health
verify_container_started() {
    local container_name=$1
    local container_id=$2
    local mode=$3  # "production" or "loop"
    local success_message=${4:-""}
    
    # Verify container was created
    if ! docker ps -a --format "{{.Names}}" | grep -q "^${container_name}$"; then
        print_error "Container was not created. Exiting."
        return 1
    fi
    
    # Print success message
    if [ -n "$success_message" ]; then
        print_success "$success_message (ID: ${container_id:0:12})"
    else
        print_success "Container $container_name started (ID: ${container_id:0:12})"
    fi
    
    # Give container a moment to start
    sleep 2
    
    # Mode-specific health checks
    if [ "$mode" == "production" ]; then
        # For production mode, check if container is still running (it might have exited immediately)
        if ! docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
            # Container exited, check why
            exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$container_name" 2>/dev/null || echo "1")
            print_error "Container exited immediately with exit code $exit_code"
            echo "Container logs:"
            docker logs "$container_name" 2>/dev/null || true
            docker rm -f "$container_name" 2>/dev/null || true
            return 1
        fi
    elif [ "$mode" == "loop" ]; then
        # For loop mode, check container health
        if ! check_container_health "$container_name"; then
            print_error "Container health check failed. Exiting."
            docker logs "$container_name" 2>/dev/null || true
            docker rm -f "$container_name" 2>/dev/null || true
            return 1
        fi
    fi
    
    return 0
}

# Function to get folder name from scraper name
# Uses Python to get the mapping from DumpFolderNames enum
get_folder_name() {
    local scraper_name=$1
    python3 -c "
from il_supermarket_scarper.utils.folders_name import DumpFolderNames
try:
    print(DumpFolderNames[$scraper_name].value)
except (KeyError, AttributeError):
    print('$scraper_name')
" 2>/dev/null || echo "$scraper_name"
}

# Function to verify scraping results
verify_scraping_results() {
    local data_path=$1
    local enabled_scrapers=$2
    local limit=$3
    
    echo ""
    echo "Verifying scraping results..."
    
    if [ ! -d "$data_path" ]; then
        print_error "Dumps folder does not exist: $data_path"
        return 1
    fi
    
    local all_good=true
    IFS=',' read -ra SCRAPER_ARRAY <<< "$enabled_scrapers"
    
    for scraper_name in "${SCRAPER_ARRAY[@]}"; do
        scraper_name=$(echo "$scraper_name" | xargs)  # trim whitespace
        folder_name=$(get_folder_name "$scraper_name")
        scraper_folder="$data_path/$folder_name"
        
        if [ ! -d "$scraper_folder" ]; then
            print_error "Scraper folder $scraper_folder does not exist"
            all_good=false
            continue
        fi
        
        # Count files (excluding .json status files)
        file_count=$(find "$scraper_folder" -type f ! -name "*.json" | wc -l)
        
        if [ "$file_count" -eq 0 ]; then
            print_error "No downloaded files found in $scraper_folder"
            all_good=false
        elif [ -n "$limit" ] && [ "$file_count" -gt "$limit" ]; then
            print_error "Found $file_count files in $scraper_folder, but limit was $limit"
            all_good=false
        else
            print_success "Scraper $scraper_name ($folder_name): Found $file_count file(s)"
        fi
        
        # Check status file exists
        status_folder="$data_path/status/$folder_name"
        if [ -d "$status_folder" ]; then
            status_files=$(find "$status_folder" -name "*.json" | wc -l)
            if [ "$status_files" -gt 0 ]; then
                print_success "Status file found for $scraper_name"
            else
                echo "Note: No status files found for $scraper_name (may be using MongoDB)"
            fi
        else
            echo "Note: Status folder not found for $scraper_name (may be using MongoDB)"
        fi
    done
    
    if [ "$all_good" = true ]; then
        return 0
    else
        return 1
    fi
}

# Wait with progress bar
wait_with_progress() {
    local seconds=$1
    local message=${2:-"Waiting"}
    echo "$message $seconds seconds..."
    local bar_length=90
    for ((i=1; i<=seconds; i++)); do
        filled=$((i * bar_length / seconds))
        bar=$(printf '#%.0s' $(seq 1 $filled))
        printf "\r[%-${bar_length}s] %d/%d seconds" "$bar" "$i" "$seconds"
        sleep 1
    done
    echo ""
}

echo ""
echo "=================================================================================="
echo "End-to-End Test - Mode: $(echo "$TEST_MODE" | tr '[:lower:]' '[:upper:]')"
echo "=================================================================================="
echo ""

# Step 1: Load environment variables
print_step 1 "Loading environment variables from .env.test if exists"
if [ -f .env.test ]; then
    export $(cat .env.test | grep -v '^#' | xargs)
    echo "Loaded environment variables from .env.test"
fi

# Step 2: Set up test environment variables
print_step 2 "Setting up test environment variables"
export ENABLED_SCRAPERS=${ENABLED_SCRAPERS:-BAREKET}
export LIMIT=${LIMIT:-10}
export OUTPUT_DESTINATION=${OUTPUT_DESTINATION:-disk}
export NUM_OF_OCCASIONS=${NUM_OF_OCCASIONS:-1}

ENABLED_SCRAPERS_VAL=$ENABLED_SCRAPERS
LIMIT_VAL=$LIMIT

# Get paths from environment or use defaults
APP_DATA_PATH=${APP_DATA_PATH:-./test_data}
# Create directory if it doesn't exist before getting absolute path
mkdir -p "$APP_DATA_PATH"
APP_DATA_PATH_ABS=$(cd "$APP_DATA_PATH" && pwd)

# Step 3: Clean existing Docker containers
print_step 3 "Stopping and removing existing Docker containers"
docker ps -q --filter "name=supermarket-scraper" | xargs -r docker stop 2>/dev/null || true
docker ps -aq --filter "name=supermarket-scraper" | xargs -r docker rm 2>/dev/null || true
docker ps -q --filter "ancestor=supermarket-scraper:test" | xargs -r docker stop 2>/dev/null || true
docker ps -aq --filter "ancestor=supermarket-scraper:test" | xargs -r docker rm 2>/dev/null || true

# Step 4: Clean app data directory
print_step 4 "Cleaning app data directory"
if [ -d "$APP_DATA_PATH" ]; then
    rm -rf "$APP_DATA_PATH"
    echo "Cleaned app data directory: $APP_DATA_PATH"
fi
mkdir -p "$APP_DATA_PATH"

# Step 5: Build Docker image
print_step 5 "Building Docker image"
BUILD_CMD=("docker" "build" "-t" "supermarket-scraper:test" "--target" "prod" ".")
if [[ "$BUILD_NO_CACHE" =~ ^[Yy]$ ]]; then
    BUILD_CMD=("docker" "build" "--no-cache" "-t" "supermarket-scraper:test" "--target" "prod" ".")
fi

if ! "${BUILD_CMD[@]}"; then
    print_error "Docker build failed. Exiting."
    exit 1
fi
print_success "Docker image built successfully"

# Step 6: Run scraping operation
print_step 6 "Running scraping operation"

if [ "$TEST_MODE" == "production" ]; then
    # Single pass mode (incremental) - default behavior
    echo "Running in single-pass mode (incremental)"
    
    container_id=$(docker run -d \
        --name supermarket-scraper-production \
        -v "$APP_DATA_PATH_ABS:/usr/src/app/dumps" \
        -e "ENABLED_SCRAPERS=$ENABLED_SCRAPERS_VAL" \
        -e "LIMIT=$LIMIT_VAL" \
        -e "OUTPUT_MODE=disk" \
        -e "STORAGE_PATH=/usr/src/app/dumps" \
        -e "STATUS_DATABASE_TYPE=json" \
        -e "SINGLE_PASS=true" \
        supermarket-scraper:test 2>&1)
    
    if [ $? -ne 0 ]; then
        print_error "Failed to start scraper container. Exiting."
        echo "Error: $container_id"
        exit 1
    fi
    
    # Verify container started and check initial health
    if ! verify_container_started "supermarket-scraper-production" "$container_id" "production" "Scraper container started"; then
        exit 1
    fi
    
    # Container is running, wait for it to complete
    echo "Waiting for scraping operation to complete..."
    docker wait supermarket-scraper-production > /dev/null
    exit_code=$(docker inspect --format='{{.State.ExitCode}}' supermarket-scraper-production 2>/dev/null || echo "1")
    
    if [ "$exit_code" != "0" ]; then
        print_error "Scraping operation failed with exit code $exit_code"
        echo "Container logs:"
        docker logs supermarket-scraper-production 2>/dev/null || true
        docker rm -f supermarket-scraper-production 2>/dev/null || true
        exit 1
    fi
    
    print_success "Scraping operation completed successfully"
    
    # Clean up container
    docker rm -f supermarket-scraper-production 2>/dev/null || true
    
    # Verify results
    if ! verify_scraping_results "$APP_DATA_PATH" "$ENABLED_SCRAPERS_VAL" "$LIMIT_VAL"; then
        print_error "Scraping results verification failed. Exiting."
        exit 1
    fi
    
else
    # Loop mode (persist) - run in background
    echo "Running in Loop/Persistent mode"
    
    container_id=$(docker run --rm -d \
        --name supermarket-scraper-loop \
        -v "$APP_DATA_PATH_ABS:/usr/src/app/dumps" \
        -e "ENABLED_SCRAPERS=$ENABLED_SCRAPERS_VAL" \
        -e "LIMIT=$LIMIT_VAL" \
        -e "OUTPUT_MODE=disk" \
        -e "STORAGE_PATH=/usr/src/app/dumps" \
        -e "STATUS_DATABASE_TYPE=json" \
        -e "SINGLE_PASS=false" \
        -e "TIMEOUT_IN_SECONDS=${TIMEOUT_IN_SECONDS:-1800}" \
        supermarket-scraper:test 2>&1)
    if [ $? -ne 0 ]; then
        print_error "Failed to start scraper in loop mode. Exiting."
        echo "Error: $container_id"
        exit 1
    fi
    
    # Verify container started and check initial health
    if ! verify_container_started "supermarket-scraper-loop" "$container_id" "loop" "Scraper started in background (running continuously)"; then
        exit 1
    fi
    
    # Wait 2 minutes before checking results
    wait_with_progress 120 "Waiting 2 minutes before proceeding"
    
    # Check if container is still running
    if ! docker ps --filter "name=supermarket-scraper-loop" --format "{{.Names}}" | grep -q "supermarket-scraper-loop"; then
        print_error "Container stopped unexpectedly"
        echo "Container logs:"
        docker logs supermarket-scraper-loop 2>/dev/null || true
        exit 1
    fi
    
    print_success "Container is still running after 2 minutes"
    
    # Verify some results were created (no strict limit check in loop mode)
    if ! verify_scraping_results "$APP_DATA_PATH" "$ENABLED_SCRAPERS_VAL" ""; then
        print_error "Scraping results verification failed. Exiting."
        exit 1
    fi
fi

# Step 7: Run system tests
print_step 7 "Running system tests"

# Build test image
if ! docker build -t supermarket-testing --target test .; then
    print_error "Failed to build test image. Exiting."
    exit 1
fi

# Run tests
if ! docker run --rm \
    -v "$APP_DATA_PATH_ABS:/usr/src/app/dumps" \
    -e "ENABLED_SCRAPERS=$ENABLED_SCRAPERS_VAL" \
    -e "LIMIT=$LIMIT_VAL" \
    -e "OUTPUT_MODE=disk" \
    -e "STORAGE_PATH=/usr/src/app/dumps" \
    -e "STATUS_DATABASE_TYPE=json" \
    supermarket-testing; then
    print_error "System tests failed. Exiting."
    exit 1
fi

print_success "System tests passed"

# Step 8: Cleanup verification (if in production mode)
if [ "$TEST_MODE" == "production" ]; then
    print_step 8 "Cleanup verification"
    echo "Note: Cleanup verification skipped - cleanup operations not implemented in this version"
    print_success "Test data remains for inspection"
fi

# Step 9: Stop containers (if in loop mode)
if [ "$TEST_MODE" == "loop" ]; then
    print_step 9 "Stopping containers"
    docker stop supermarket-scraper-loop 2>/dev/null || true
    docker rm supermarket-scraper-loop 2>/dev/null || true
    print_success "Containers stopped"
fi

echo ""
echo "=================================================================================="
print_success "All tests completed successfully!"
echo "=================================================================================="
echo ""
