// orgchart.js - JavaScript for organizational chart visualization

document.addEventListener('DOMContentLoaded', function() {
    // Initialize org chart if container exists
    initializeOrgChart();
    
    // Set up department filter
    setupDepartmentFilter();
});

// Function to initialize organizational chart
function initializeOrgChart() {
    const chartContainer = document.getElementById('orgChartContainer');
    if (!chartContainer) return;
    
    // First show loading state
    chartContainer.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading organizational chart...</p>
        </div>
    `;
    
    // Fetch chart data
    fetch('/organization/chart-data' + window.location.search)
        .then(response => response.json())
        .then(data => {
            // Clear loading state
            chartContainer.innerHTML = '';
            
            if (data.length === 0) {
                chartContainer.innerHTML = `
                    <div class="text-center py-5">
                        <p class="text-muted">No employees found for the selected criteria</p>
                    </div>
                `;
                return;
            }
            
            // Initialize OrgChart from orgchart.js
            // We're using a placeholder implementation here, as we can't load external libraries
            renderSimpleOrgChart(chartContainer, data);
        })
        .catch(error => {
            console.error('Error loading org chart data:', error);
            chartContainer.innerHTML = `
                <div class="text-center py-5">
                    <p class="text-danger">Error loading organizational chart</p>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="initializeOrgChart()">
                        Try Again
                    </button>
                </div>
            `;
        });
}

// Function to render a simple org chart (placeholder for full library)
function renderSimpleOrgChart(container, data) {
    // Create a map for quick lookup
    const nodeMap = new Map();
    data.forEach(node => {
        nodeMap.set(node.id, { ...node, children: [] });
    });
    
    // Build the tree structure
    const rootNodes = [];
    data.forEach(node => {
        if (node.pid) {
            const parent = nodeMap.get(node.pid);
            if (parent) {
                parent.children.push(nodeMap.get(node.id));
            } else {
                rootNodes.push(nodeMap.get(node.id));
            }
        } else {
            rootNodes.push(nodeMap.get(node.id));
        }
    });
    
    // Create chart container
    const chartDiv = document.createElement('div');
    chartDiv.className = 'org-chart';
    container.appendChild(chartDiv);
    
    // Render the tree starting from root nodes
    rootNodes.forEach(rootNode => {
        const rootElement = createNodeElement(rootNode);
        chartDiv.appendChild(rootElement);
    });
}

// Function to create a node element in the org chart
function createNodeElement(node) {
    const nodeDiv = document.createElement('div');
    nodeDiv.className = 'org-node';
    
    // Node content
    nodeDiv.innerHTML = `
        <div class="card org-card">
            <div class="card-body text-center">
                <h6 class="card-title mb-0">${node.name}</h6>
                <p class="card-text small text-muted">${node.title}</p>
                <span class="badge bg-info">${node.department}</span>
            </div>
        </div>
    `;
    
    // If there are children, create a container for them
    if (node.children && node.children.length > 0) {
        const childrenContainer = document.createElement('div');
        childrenContainer.className = 'org-children';
        
        // Add each child
        node.children.forEach(child => {
            const childElement = createNodeElement(child);
            childrenContainer.appendChild(childElement);
        });
        
        nodeDiv.appendChild(childrenContainer);
    }
    
    return nodeDiv;
}

// Function to set up department filter
function setupDepartmentFilter() {
    const filterForm = document.getElementById('departmentFilterForm');
    const departmentSelect = document.getElementById('departmentFilter');
    
    if (!filterForm || !departmentSelect) return;
    
    // When department selection changes, submit the form
    departmentSelect.addEventListener('change', function() {
        filterForm.submit();
    });
}

// Function to export org chart
function exportOrgChart(format) {
    alert(`Exporting org chart as ${format}`);
    // This would be implemented with the org chart library's export functionality
}

// Function to zoom controls
function zoomOrgChart(zoomAction) {
    // This would interact with the org chart library to zoom in/out
    console.log(`Zoom ${zoomAction}`);
}

// Function to switch between different chart layouts
function changeChartLayout(layout) {
    // This would change the org chart layout (e.g., vertical, horizontal)
    console.log(`Changing layout to ${layout}`);
}
