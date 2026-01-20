#!/bin/bash
# Build documentation using Docker container
# Usage: ./build-docs.sh [command]
#
# Commands:
#   build   - Build static HTML documentation (default)
#   serve   - Start local development server on http://localhost:8000
#   clean   - Remove generated documentation
#   help    - Show this help message

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "${SCRIPT_DIR}")"
IMAGE_NAME="bake-linter-docs"
OUTPUT_DIR="_site"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    echo "Bake Linter Documentation Builder"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build   - Build static HTML documentation (default)"
    echo "  serve   - Start local development server on http://localhost:8000"
    echo "  clean   - Remove generated documentation"
    echo "  rebuild - Rebuild the Docker image"
    echo "  help    - Show this help message"
    echo ""
    echo "Output directory: ${PARENT_DIR}/${OUTPUT_DIR}"
}

build_image() {
    print_info "Building Docker image..."
    docker build -t "${IMAGE_NAME}" "${SCRIPT_DIR}"
    print_success "Docker image built successfully"
}

build_docs() {
    print_info "Building documentation..."
    
    # Build the Docker image if it doesn't exist
    if ! docker image inspect "${IMAGE_NAME}" &> /dev/null; then
        build_image
    fi
    
    # Run the container to build docs
    # Mount the parent directory since output goes to ../_site
    # Use current user ID to avoid permission issues
    docker run --rm \
        --user "$(id -u):$(id -g)" \
        -v "${PARENT_DIR}:/workspace:Z" \
        -w /workspace/docs \
        "${IMAGE_NAME}" \
        mkdocs build --config-file mkdocs.yml
    
    print_success "Documentation built successfully!"
    print_info "Output: ${PARENT_DIR}/${OUTPUT_DIR}/index.html"
}

serve_docs() {
    print_info "Starting documentation server..."
    print_info "Documentation will be available at: http://localhost:8001"
    print_info "Press Ctrl+C to stop"
    
    # Build the Docker image if it doesn't exist
    if ! docker image inspect "${IMAGE_NAME}" &> /dev/null; then
        build_image
    fi
    
    # Run the container with the development server
    # Mount the parent directory since output goes to ../_site
    # Use current user ID to avoid permission issues
    docker run --rm -it \
        --user "$(id -u):$(id -g)" \
        -v "${PARENT_DIR}:/workspace:Z" \
        -w /workspace/docs \
        -p 8001:8001 \
        "${IMAGE_NAME}" \
        mkdocs serve --config-file mkdocs.yml --dev-addr 0.0.0.0:8001
}

clean_docs() {
    print_info "Cleaning generated documentation..."
    
    if [ -d "${PARENT_DIR}/${OUTPUT_DIR}" ]; then
        rm -rf "${PARENT_DIR}/${OUTPUT_DIR}"
        print_success "Cleaned ${OUTPUT_DIR} directory"
    else
        print_warning "Nothing to clean - ${OUTPUT_DIR} directory does not exist"
    fi
}

rebuild_image() {
    print_info "Rebuilding Docker image..."
    docker rmi "${IMAGE_NAME}" 2>/dev/null || true
    build_image
}

# Main script logic
case "${1:-build}" in
    build)
        build_docs
        ;;
    serve)
        serve_docs
        ;;
    clean)
        clean_docs
        ;;
    rebuild)
        rebuild_image
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
