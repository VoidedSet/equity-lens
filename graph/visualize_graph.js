// Graph Visualization Logic using D3.js v7

// Color mapping for node types
const colors = {
    COMPANY: "var(--node-company)",
    PERSON: "var(--node-person)",
    TOPIC: "var(--node-topic)",
    BRAND: "var(--node-brand)",
    LOCATION: "var(--node-location)",
    STRATEGY: "var(--node-strategy)",
    TIME_PERIOD: "var(--node-time_period)"
};

let rawData = null;
let currentSimulation = null;
let svgRef, gRef;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    // Setup file input listener for local fallback
    document.getElementById("json-file-input").addEventListener("change", handleFileUpload);
    
    // Try fetching directly first
    fetch('graph_data.json')
        .then(response => {
            if (!response.ok) throw new Error("HTTP error " + response.status);
            return response.json();
        })
        .then(data => {
            document.getElementById("file-loader").style.display = "none";
            document.getElementById("app-container").style.display = "flex";
            initApp(data);
        })
        .catch(err => {
            console.warn("Could not fetch graph_data.json via HTTP (expected for local file:// protocol). Please use the file picker.");
            // Keep file loader visible
        });
});

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const data = JSON.parse(e.target.result);
                document.getElementById("file-loader").style.display = "none";
                document.getElementById("app-container").style.display = "flex";
                initApp(data);
            } catch (err) {
                alert("Invalid JSON file");
            }
        };
        reader.readAsText(file);
    }
}

function initApp(data) {
    rawData = data;
    
    // Populate dropdowns with exact ticker codes used in nodes
    const companiesSet = new Set();
    data.nodes.forEach(n => {
        if (n.companies) n.companies.forEach(c => companiesSet.add(c));
    });
    const companies = Array.from(companiesSet).sort();
    const cFilter = document.getElementById("company-filter");
    const comp1 = document.getElementById("compare-c1");
    const comp2 = document.getElementById("compare-c2");
    
    companies.forEach(c => {
        cFilter.add(new Option(c, c));
        comp1.add(new Option(c, c));
        comp2.add(new Option(c, c));
    });

    // Populate Legend
    const legend = document.getElementById("legend-container");
    Object.keys(colors).forEach(type => {
        legend.innerHTML += `
            <div class="legend-item">
                <div class="legend-color" style="background-color: ${colors[type]}"></div>
                <span>${type}</span>
            </div>
        `;
    });

    // Event Listeners
    document.getElementById("search-input").addEventListener("input", e => filterGraph());
    document.getElementById("company-filter").addEventListener("change", e => filterGraph());
    document.getElementById("type-filter").addEventListener("change", e => filterGraph());
    document.getElementById("weight-filter").addEventListener("input", e => {
        document.getElementById("weight-val").innerText = parseFloat(e.target.value).toFixed(1);
        filterGraph();
    });
    document.getElementById("reset-btn").addEventListener("click", () => {
        document.getElementById("search-input").value = "";
        document.getElementById("company-filter").value = "ALL";
        document.getElementById("type-filter").value = "ALL";
        document.getElementById("weight-filter").value = "2.0";
        document.getElementById("weight-val").innerText = "2.0";
        filterGraph();
        hideDetails();
    });
    document.getElementById("compare-btn").addEventListener("click", doCompare);

    // Initial render using the default edge filter to prevent massive lag
    filterGraph();
}

function doCompare() {
    const c1 = document.getElementById("compare-c1").value;
    const c2 = document.getElementById("compare-c2").value;
    
    if (!c1 || !c2 || c1 === c2) {
        alert("Please select two different companies.");
        return;
    }

    // Find nodes belonging to these companies
    const filteredNodes = rawData.nodes.filter(n => 
        n.type !== "COMPANY" && n.type !== "TIME_PERIOD" &&
        (n.companies.includes(c1) || n.companies.includes(c2))
    );
    
    // Create a set of their IDs
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    
    // Filter edges
    const weightFilter = parseFloat(document.getElementById("weight-filter").value) || 0;
    const filteredEdges = rawData.edges.filter(e => 
        nodeIds.has(e.source.id || e.source) && 
        nodeIds.has(e.target.id || e.target) &&
        e.weight >= weightFilter
    );

    renderGraph(filteredNodes, filteredEdges, true, c1, c2);
    
    // Update Details panel
    showDetails({_isCompareMode: true, c1, c2});
}

function filterGraph() {
    const search = document.getElementById("search-input").value.toLowerCase();
    const compFilter = document.getElementById("company-filter").value;
    const typeFilter = document.getElementById("type-filter").value;
    const weightFilter = parseFloat(document.getElementById("weight-filter").value) || 0;

    let filteredNodes = rawData.nodes.filter(n => {
        let matchSearch = search === "" || n.label.toLowerCase().includes(search);
        let matchComp = compFilter === "ALL" || n.companies.includes(compFilter);
        let matchType = typeFilter === "ALL" || n.type === typeFilter;
        return matchSearch && matchComp && matchType;
    });

    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = rawData.edges.filter(e => 
        nodeIds.has(e.source.id || e.source) && 
        nodeIds.has(e.target.id || e.target) &&
        e.weight >= weightFilter
    );

    renderGraph(filteredNodes, filteredEdges);
}

function renderGraph(nodesData, edgesData, isCompareMode=false, c1="", c2="") {
    const container = document.getElementById("graph-container");
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Clear previous
    d3.select("#network-viz").selectAll("*").remove();
    if(currentSimulation) currentSimulation.stop();

    const svg = d3.select("#network-viz")
        .attr("viewBox", [0, 0, width, height]);

    // Zoom setup
    const g = svg.append("g");
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on("zoom", (e) => g.attr("transform", e.transform));
    svg.call(zoom);

    // Copy data to avoid mutation issues during restarts
    const nodes = nodesData.map(d => ({...d}));
    const edges = edgesData.map(d => ({...d}));

    // Setup Simulation
    currentSimulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(edges).id(d => d.id).distance(180))
        .force("charge", d3.forceManyBody().strength(-250))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collide", d3.forceCollide().radius(d => Math.sqrt(d.count || 1) * 4 + 18).iterations(3));

    // Draw Edges
    const link = g.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(edges)
        .join("line")
        .attr("class", "link")
        .attr("stroke-width", d => Math.max(1, Math.min(5, d.weight * 2)))
        .on("click", (e, d) => showDetails(d, "edge"))
        .on("mouseover", function(e, d) {
            // Edge Tooltip
            const tt = document.getElementById("edge-tooltip");
            let ctx = d.contexts && d.contexts.length ? `<i>"${d.contexts[0].replace(/</g,"&lt;").replace(/>/g,"&gt;").substring(0, 180)}..."</i>` : "Click for details";
            tt.innerHTML = `<strong>${d.source.label} &rarr; ${d.target.label}</strong><br><span style="color:#8b949e">Weight: ${d.weight.toFixed(2)}</span><br><br>${ctx}`;
            tt.style.display = "block";
            tt.style.left = (e.pageX + 15) + "px";
            tt.style.top = (e.pageY + 15) + "px";
            
            // Relational Highlight
            d3.selectAll(".link").classed("dimmed", l => l !== d);
            d3.select(this).classed("highlighted", true);
            d3.selectAll(".node").classed("dimmed", n => n.id !== d.source.id && n.id !== d.target.id);
        })
        .on("mouseout", function() {
            document.getElementById("edge-tooltip").style.display = "none";
            d3.selectAll(".link").classed("dimmed", false).classed("highlighted", false);
            d3.selectAll(".node").classed("dimmed", false);
        });

    // Draw Nodes
    const node = g.append("g")
        .attr("class", "nodes")
        .selectAll("g")
        .data(nodes)
        .join("g")
        .attr("class", "node")
        .call(drag(currentSimulation))
        .on("click", (e, d) => showDetails(d, "node", isCompareMode, c1, c2))
        .on("mouseover", function(e, d) {
            // Find all connected node IDs
            const connectedIds = new Set();
            connectedIds.add(d.id);
            edges.forEach(l => {
                if (l.source.id === d.id) connectedIds.add(l.target.id);
                if (l.target.id === d.id) connectedIds.add(l.source.id);
            });
            
            // Highlight connections
            d3.selectAll(".node").classed("dimmed", n => !connectedIds.has(n.id));
            d3.selectAll(".link")
                .classed("dimmed", l => l.source.id !== d.id && l.target.id !== d.id)
                .classed("highlighted", l => l.source.id === d.id || l.target.id === d.id);
            d3.select(this).classed("highlighted", true);
        })
        .on("mouseout", function() {
            d3.selectAll(".node").classed("dimmed", false).classed("highlighted", false);
            d3.selectAll(".link").classed("dimmed", false).classed("highlighted", false);
        });

    // Color logic for compare mode
    node.append("circle")
        .attr("r", d => Math.max(8, Math.min(25, Math.sqrt(d.count || 1) * 3)))
        .attr("fill", d => {
            if (isCompareMode) {
                const inC1 = d.companies.includes(c1);
                const inC2 = d.companies.includes(c2);
                if (inC1 && inC2) return "url(#stripes)"; // Shared
                if (inC1) return "#ff7b72"; // C1 only (Red-ish)
                if (inC2) return "#58a6ff"; // C2 only (Blue-ish)
            }
            return colors[d.type] || "#ffffff";
        });

    node.append("text")
        .attr("dx", d => Math.max(12, Math.min(30, Math.sqrt(d.count || 1) * 3 + 5)))
        .attr("dy", ".35em")
        .style("font-size", d => Math.max(11, Math.min(18, Math.sqrt(d.count || 1) * 2 + 8)) + "px")
        .style("font-weight", d => d.count > 50 ? "600" : "400")
        .style("opacity", d => d.count > 10 ? 1 : 0.6)
        .text(d => d.label);

    // If compare mode, add SVG pattern
    if (isCompareMode) {
        const defs = svg.append("defs");
        const pattern = defs.append("pattern")
            .attr("id", "stripes")
            .attr("width", 8)
            .attr("height", 8)
            .attr("patternUnits", "userSpaceOnUse")
            .attr("patternTransform", "rotate(45)");
        pattern.append("rect").attr("width", 4).attr("height", 8).attr("fill", "#ff7b72");
        pattern.append("rect").attr("x", 4).attr("width", 4).attr("height", 8).attr("fill", "#58a6ff");
    }

    currentSimulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("transform", d => `translate(${d.x},${d.y})`);
    });
}

function drag(simulation) {
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
    return d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
}

function showDetails(data, type="node", isCompare=false, c1="", c2="") {
    document.getElementById("default-msg").style.display = "none";
    const panel = document.getElementById("node-details");
    panel.style.display = "block";

    // Re-highlight logic
    d3.selectAll('.node').classed('selected', false);

    if (data._isCompareMode) {
        panel.innerHTML = `
            <div class="detail-title">Compare Mode</div>
            <div class="detail-meta">${data.c1} vs ${data.c2}</div>
            <p>Nodes are colored to show uniqueness:</p>
            <ul>
                <li><span style="color:#ff7b72; font-weight:bold;">Red:</span> Unique to ${data.c1}</li>
                <li><span style="color:#58a6ff; font-weight:bold;">Blue:</span> Unique to ${data.c2}</li>
                <li><span style="background: repeating-linear-gradient(45deg, #ff7b72, #ff7b72 5px, #58a6ff 5px, #58a6ff 10px); padding:0 5px; color:white;">Striped:</span> Shared topics</li>
            </ul>
        `;
        return;
    }

    if (type === "node") {
        let tagsHtml = data.companies.map(c => `<span class="tag">${c}</span>`).join("");
        
        let compareHtml = "";
        if (isCompare) {
            const inC1 = data.companies.includes(c1);
            const inC2 = data.companies.includes(c2);
            if (inC1 && inC2) compareHtml = `<div style="color:var(--accent-color);margin-bottom:10px;">⭐ SHARED by both</div>`;
            else if (inC1) compareHtml = `<div style="color:#ff7b72;margin-bottom:10px;">🔒 Unique to ${c1}</div>`;
            else if (inC2) compareHtml = `<div style="color:#58a6ff;margin-bottom:10px;">🔒 Unique to ${c2}</div>`;
        }

        panel.innerHTML = `
            <div class="detail-title">${data.label}</div>
            <div class="detail-meta">${data.type} &bull; ${data.count} mentions</div>
            ${compareHtml}
            <div class="detail-section">
                <h3>Discussed By</h3>
                ${tagsHtml || "None"}
            </div>
        `;
    } 
    else if (type === "edge") {
        let contextsHtml = "";
        if (data.contexts && data.contexts.length > 0) {
            contextsHtml = data.contexts.map(c => `<div class="quote">"...${c.replace(/</g, "&lt;").replace(/>/g, "&gt;")}..."</div>`).join("");
        }

        panel.innerHTML = `
            <div class="detail-title">Connection</div>
            <div class="detail-meta">${data.source.label} &harr; ${data.target.label}</div>
            <div class="detail-section">
                <h3>Edge Weight: ${data.weight.toFixed(2)}</h3>
                <p>Co-occurrences: ${data.count}</p>
            </div>
            ${contextsHtml ? `
            <div class="detail-section">
                <h3>Sample Contexts</h3>
                ${contextsHtml}
            </div>` : ""}
        `;
    }
}

function hideDetails() {
    document.getElementById("default-msg").style.display = "block";
    document.getElementById("node-details").style.display = "none";
    d3.selectAll('.node').classed('selected', false);
}
