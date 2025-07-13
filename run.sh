
#!/bin/bash

# CarMax/Manheim Auction Automation System
# Launcher script with logging and background execution

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
VENV_DIR="$SCRIPT_DIR/venv"
PID_FILE="$LOG_DIR/auction_bot.pid"
LOG_FILE="$LOG_DIR/auction_bot_run.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Function to check if virtual environment exists
check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "Virtual environment not found. Please run setup first:"
        echo "  python3 -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
}

# Function to activate virtual environment
activate_venv() {
    source "$VENV_DIR/bin/activate"
}

# Function to check if process is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Function to start the auction bot
start_bot() {
    if is_running; then
        echo "Auction bot is already running (PID: $(cat $PID_FILE))"
        exit 1
    fi
    
    echo "Starting auction automation system..."
    
    # Check environment
    check_venv
    activate_venv
    
    # Change to script directory
    cd "$SCRIPT_DIR"
    
    # Start the bot in background with nohup
    nohup python3 main.py "$@" >> "$LOG_FILE" 2>&1 &
    local pid=$!
    
    # Save PID
    echo "$pid" > "$PID_FILE"
    
    echo "Auction bot started with PID: $pid"
    echo "Logs: $LOG_FILE"
    echo "To stop: $0 stop"
    echo "To check status: $0 status"
}

# Function to stop the auction bot
stop_bot() {
    if ! is_running; then
        echo "Auction bot is not running"
        exit 1
    fi
    
    local pid=$(cat "$PID_FILE")
    echo "Stopping auction bot (PID: $pid)..."
    
    # Send SIGTERM first
    kill "$pid" 2>/dev/null || true
    
    # Wait for graceful shutdown
    local count=0
    while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 30 ]; do
        sleep 1
        count=$((count + 1))
    done
    
    # Force kill if still running
    if ps -p "$pid" > /dev/null 2>&1; then
        echo "Force killing process..."
        kill -9 "$pid" 2>/dev/null || true
    fi
    
    rm -f "$PID_FILE"
    echo "Auction bot stopped"
}

# Function to show status
show_status() {
    if is_running; then
        local pid=$(cat "$PID_FILE")
        echo "Auction bot is running (PID: $pid)"
        
        # Show recent log entries
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Recent log entries:"
            echo "-------------------"
            tail -10 "$LOG_FILE"
        fi
    else
        echo "Auction bot is not running"
    fi
}

# Function to show logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        if command -v less >/dev/null 2>&1; then
            less "$LOG_FILE"
        else
            cat "$LOG_FILE"
        fi
    else
        echo "No log file found: $LOG_FILE"
    fi
}

# Function to setup the system
setup_system() {
    echo "Setting up auction automation system..."
    
    # Check Python version
    if ! python3 --version | grep -q "Python 3\.[8-9]\|Python 3\.1[0-9]"; then
        echo "Error: Python 3.8+ required"
        exit 1
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    # Activate and install dependencies
    activate_venv
    
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Install Playwright browsers
    echo "Installing Playwright browsers..."
    playwright install chromium firefox webkit
    
    # Create necessary directories
    mkdir -p "$LOG_DIR"
    mkdir -p data
    mkdir -p profiles
    
    # Copy environment file if it doesn't exist
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        echo "Creating .env file from template..."
        cp .env.example .env
        echo "Please edit .env file with your credentials"
    fi
    
    echo "Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your credentials"
    echo "2. Run: $0 start"
}

# Function to run tests
run_tests() {
    echo "Running system tests..."
    
    check_venv
    activate_venv
    cd "$SCRIPT_DIR"
    
    # Basic import test
    python3 -c "
import sys
sys.path.append('.')
try:
    from main import AuctionAutomationOrchestrator
    from utils.config import config
    from utils.logger import logger
    print('✓ All imports successful')
except Exception as e:
    print(f'✗ Import failed: {e}')
    sys.exit(1)
"
    
    # Configuration test
    python3 -c "
import sys
sys.path.append('.')
from utils.config import config
try:
    platforms = config.get('platforms', {})
    if 'carmax' in platforms and 'manheim' in platforms:
        print('✓ Configuration loaded successfully')
    else:
        print('✗ Platform configuration missing')
        sys.exit(1)
except Exception as e:
    print(f'✗ Configuration test failed: {e}')
    sys.exit(1)
"
    
    echo "All tests passed!"
}

# Main script logic
case "${1:-}" in
    start)
        shift
        start_bot "$@"
        ;;
    stop)
        stop_bot
        ;;
    restart)
        if is_running; then
            stop_bot
            sleep 2
        fi
        shift
        start_bot "$@"
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    setup)
        setup_system
        ;;
    test)
        run_tests
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|setup|test} [options]"
        echo ""
        echo "Commands:"
        echo "  start [options]  - Start the auction automation system"
        echo "  stop            - Stop the auction automation system"
        echo "  restart [options] - Restart the auction automation system"
        echo "  status          - Show current status"
        echo "  logs            - Show log files"
        echo "  setup           - Setup the system (first time)"
        echo "  test            - Run system tests"
        echo ""
        echo "Start options:"
        echo "  --platforms carmax manheim  - Specify platforms to search"
        echo "  --max-price 50000          - Maximum bid price"
        echo "  --max-mileage 150000       - Maximum mileage"
        echo "  --min-year 2015            - Minimum year"
        echo ""
        echo "Examples:"
        echo "  $0 setup                                    # First time setup"
        echo "  $0 start                                    # Start with default settings"
        echo "  $0 start --platforms carmax --max-price 30000  # CarMax only, max $30k"
        echo "  $0 status                                   # Check if running"
        echo "  $0 logs                                     # View logs"
        exit 1
        ;;
esac
