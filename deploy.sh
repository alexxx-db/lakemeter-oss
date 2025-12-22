#!/bin/bash
# Lakemeter Deployment Script
# Builds frontend, bundles with backend, and deploys to Databricks Apps

set -e  # Exit on error

echo "🚀 Lakemeter Deployment Script"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="${LAKEMETER_APP_NAME:-lakemeter}"
WORKSPACE_HOST="${DATABRICKS_HOST:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

# Step 1: Build Frontend
echo -e "\n${YELLOW}Step 1: Building frontend...${NC}"
cd frontend

# Update API URL for production (same origin, no CORS needed)
echo "Updating API URL for production..."
cat > .env.production << EOF
VITE_API_URL=
EOF

npm ci --silent 2>/dev/null || npm install --silent
npm run build

if [ ! -d "dist" ]; then
    echo -e "${RED}Error: Frontend build failed - dist directory not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Frontend built successfully${NC}"

# Step 2: Copy frontend build to backend
echo -e "\n${YELLOW}Step 2: Copying frontend to backend/static...${NC}"
cd "$SCRIPT_DIR"
rm -rf backend/static
mkdir -p backend/static
cp -r frontend/dist/* backend/static/
echo -e "${GREEN}✓ Frontend copied to backend/static${NC}"

# Step 3: Verify the bundle
echo -e "\n${YELLOW}Step 3: Verifying bundle...${NC}"
if [ -f "backend/static/index.html" ]; then
    echo -e "${GREEN}✓ index.html found${NC}"
else
    echo -e "${RED}Error: index.html not found in backend/static${NC}"
    exit 1
fi

if [ -d "backend/static/assets" ]; then
    JS_COUNT=$(find backend/static/assets -name "*.js" | wc -l | xargs)
    CSS_COUNT=$(find backend/static/assets -name "*.css" | wc -l | xargs)
    echo -e "${GREEN}✓ Assets directory found (${JS_COUNT} JS, ${CSS_COUNT} CSS files)${NC}"
else
    echo -e "${RED}Error: assets directory not found in backend/static${NC}"
    exit 1
fi

# Step 4: Deploy to Databricks Apps (if host is configured)
if [ -n "$WORKSPACE_HOST" ]; then
    echo -e "\n${YELLOW}Step 4: Deploying to Databricks Apps...${NC}"
    
    # Check if databricks CLI is installed
    if ! command -v databricks &> /dev/null; then
        echo -e "${RED}Error: Databricks CLI not installed${NC}"
        echo "Install with: pip install databricks-cli"
        exit 1
    fi
    
    # Check auth
    echo "Checking Databricks authentication..."
    if ! databricks auth describe 2>/dev/null; then
        echo -e "${RED}Error: Not authenticated with Databricks${NC}"
        echo "Run: databricks configure --token"
        exit 1
    fi
    
    cd backend
    
    # Deploy using Databricks Apps
    echo "Deploying app '${APP_NAME}'..."
    databricks apps deploy ${APP_NAME} --source-code-path .
    
    echo -e "${GREEN}✓ Deployed to Databricks Apps${NC}"
    echo -e "\n${GREEN}🎉 Deployment complete!${NC}"
    echo -e "App URL: ${BLUE}https://${WORKSPACE_HOST}/apps/${APP_NAME}${NC}"
else
    echo -e "\n${YELLOW}Step 4: Skipping deployment (DATABRICKS_HOST not set)${NC}"
    echo ""
    echo "To deploy, set environment variables:"
    echo -e "  ${BLUE}export DATABRICKS_HOST=your-workspace.cloud.databricks.com${NC}"
    echo -e "  ${BLUE}export LAKEMETER_APP_NAME=lakemeter${NC}"
    echo ""
    echo "Then run the deployment command:"
    echo -e "  ${BLUE}cd backend && databricks apps deploy \$LAKEMETER_APP_NAME --source-code-path .${NC}"
    echo -e "\n${GREEN}✓ Build complete - ready for manual deployment${NC}"
fi

echo ""
echo "📦 Bundle contents:"
echo "===================="
du -sh backend/static/
ls -la backend/static/

echo ""
echo "📋 Next steps for Databricks Apps deployment:"
echo "1. Ensure your Databricks workspace has Apps enabled"
echo "2. Create a secret scope and add DATABASE_URL secret"
echo "3. Run: databricks apps deploy lakemeter --source-code-path backend/"
