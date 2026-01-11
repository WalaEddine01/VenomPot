// ================== SVG SETUP ==================
const svg = d3.select("svg");
const width = window.innerWidth;
const height = window.innerHeight;

const tooltip = d3.select(".tooltip");

const HONEYPOT_ID = "HONEYPOT";

// ================== DEFS FOR GRADIENTS & FILTERS ==================
const defs = svg.append("defs");

// Glow filter
const glowFilter = defs
  .append("filter")
  .attr("id", "glow")
  .attr("x", "-50%")
  .attr("y", "-50%")
  .attr("width", "200%")
  .attr("height", "200%");

glowFilter
  .append("feGaussianBlur")
  .attr("stdDeviation", "3")
  .attr("result", "coloredBlur");

const glowMerge = glowFilter.append("feMerge");
glowMerge.append("feMergeNode").attr("in", "coloredBlur");
glowMerge.append("feMergeNode").attr("in", "SourceGraphic");

// Server pulse filter
const serverGlow = defs
  .append("filter")
  .attr("id", "server-glow")
  .attr("x", "-100%")
  .attr("y", "-100%")
  .attr("width", "300%")
  .attr("height", "300%");

serverGlow
  .append("feGaussianBlur")
  .attr("stdDeviation", "6")
  .attr("result", "coloredBlur");

const serverMerge = serverGlow.append("feMerge");
serverMerge.append("feMergeNode").attr("in", "coloredBlur");
serverMerge.append("feMergeNode").attr("in", "SourceGraphic");

// Gradients for links
const linkGradient = defs
  .append("linearGradient")
  .attr("id", "link-gradient")
  .attr("gradientUnits", "userSpaceOnUse");

linkGradient
  .append("stop")
  .attr("offset", "0%")
  .attr("stop-color", "#00ff64")
  .attr("stop-opacity", 0.8);
linkGradient
  .append("stop")
  .attr("offset", "100%")
  .attr("stop-color", "#3fa9f5")
  .attr("stop-opacity", 0.3);

// ================== DATA ==================
let nodes = [{ id: HONEYPOT_ID, type: "server" }];
let links = [];

const nodeMap = new Map(); // ip -> node
const countryMap = new Map(); // country -> node

// Stats tracking
let stats = {
  attackers: 0,
  countries: 0,
  highRisk: 0,
  torNodes: 0,
  commands: 0,
};

// ================== ZOOM ==================
const zoomBehavior = d3
  .zoom()
  .scaleExtent([0.3, 4])
  .on("zoom", (event) => {
    mainGroup.attr("transform", event.transform);
  });

svg.call(zoomBehavior);

// Main group for zoom/pan
const mainGroup = svg.append("g");

// ================== FORCE SIMULATION ==================
const simulation = d3
  .forceSimulation(nodes)
  .force(
    "link",
    d3
      .forceLink(links)
      .id((d) => d.id)
      .distance((d) => {
        if (d.source.type === "server") return 150;
        if (d.source.type === "country") return 80;
        return 60;
      })
  )
  .force(
    "charge",
    d3.forceManyBody().strength((d) => {
      if (d.type === "server") return -500;
      if (d.type === "country") return -300;
      return -150;
    })
  )
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force(
    "collision",
    d3.forceCollide().radius((d) => {
      if (d.type === "server") return 40;
      if (d.type === "country") return 25;
      return 15;
    })
  )
  .force("x", d3.forceX(width / 2).strength(0.03))
  .force("y", d3.forceY(height / 2).strength(0.03));

// ================== SVG GROUPS ==================
const gLinks = mainGroup.append("g").attr("class", "links");
const gNodes = mainGroup.append("g").attr("class", "nodes");
const gLabels = mainGroup.append("g").attr("class", "labels");

// ================== COLOR LOGIC ==================
function nodeColor(d) {
  if (d.type === "server") return "#00ff64";
  if (d.type === "country") return "#3fa9f5";

  const colors = {
    TOR: "#d000ff",
    VPN: "#ff4444",
    HOSTING: "#ffaa00",
    RESIDENTIAL: "#4caf50",
  };

  return colors[d.network_type] || "#888";
}

function linkColor(d) {
  const sourceType = d.source.network_type || d.source.type;
  if (sourceType === "TOR") return "#d000ff";
  if (sourceType === "VPN") return "#ff4444";
  if (sourceType === "HOSTING") return "#ffaa00";
  if (d.source.type === "server") return "#00ff64";
  if (d.source.type === "country") return "#3fa9f5";
  return "#2a3f5f";
}

// ================== UPDATE STATS ==================
function updateStats() {
  stats.attackers = nodeMap.size;
  stats.countries = countryMap.size;
  stats.highRisk = [...nodeMap.values()].filter(
    (n) => n.reputation >= 70
  ).length;
  stats.torNodes = [...nodeMap.values()].filter(
    (n) => n.network_type === "TOR"
  ).length;

  document.getElementById("stat-attackers").textContent = stats.attackers;
  document.getElementById("stat-countries").textContent = stats.countries;
  document.getElementById("stat-high-risk").textContent = stats.highRisk;
  document.getElementById("stat-tor").textContent = stats.torNodes;
  document.getElementById("stat-commands").textContent = stats.commands;
}

// ================== ACTIVITY FEED ==================
function addActivity(data) {
  const list = document.getElementById("activity-list");
  const item = document.createElement("div");

  const riskClass =
    data.risk >= 70 ? "risk-high" : data.risk >= 40 ? "risk-medium" : "";
  item.className = `activity-item ${riskClass}`;

  const time = new Date().toLocaleTimeString();
  const cmd = data.command || data.type || "connection";
  const country = data.geo?.country || "UNK";

  item.innerHTML = `
    <div style="display:flex;justify-content:space-between;">
      <span class="activity-ip">${data.ip}</span>
      <span class="activity-time">${time}</span>
    </div>
    <div class="activity-cmd">${country} → ${cmd.substring(0, 40)}${
    cmd.length > 40 ? "..." : ""
  }</div>
  `;

  list.insertBefore(item, list.firstChild);

  // Keep only last 50 items
  while (list.children.length > 50) {
    list.removeChild(list.lastChild);
  }

  if (data.command) stats.commands++;
}

// ================== RENDER ==================
function render() {
  // ---- LINKS ----
  const link = gLinks
    .selectAll("line")
    .data(
      links,
      (d) => `${d.source.id || d.source}-${d.target.id || d.target}`
    );

  const linkEnter = link
    .enter()
    .append("line")
    .attr("stroke", linkColor)
    .attr("stroke-width", (d) => {
      if (d.source.type === "server" || d.source === HONEYPOT_ID) return 2;
      return 1.5;
    })
    .attr("stroke-opacity", 0.6)
    .style("stroke-linecap", "round");

  link.merge(linkEnter).attr("stroke", linkColor);

  link.exit().remove();

  // ---- NODES ----
  const node = gNodes.selectAll("g.node").data(nodes, (d) => d.id);

  const nodeEnter = node
    .enter()
    .append("g")
    .attr("class", "node")
    .style("cursor", "pointer")
    .call(
      d3.drag().on("start", dragStart).on("drag", dragDrag).on("end", dragEnd)
    );

  // Add circle to node group
  nodeEnter
    .append("circle")
    .attr("r", (d) => {
      if (d.type === "server") return 25;
      if (d.type === "country") return 14;
      return 8;
    })
    .attr("fill", nodeColor)
    .attr("stroke", (d) => d3.color(nodeColor(d)).brighter(0.5))
    .attr("stroke-width", (d) => (d.type === "server" ? 3 : 2))
    .attr("filter", (d) =>
      d.type === "server" ? "url(#server-glow)" : "url(#glow)"
    );

  // Add icon/text inside nodes
  nodeEnter
    .filter((d) => d.type === "server")
    .append("image")
    .attr("xlink:href", "assets/honeypy-logo-white.png")
    .attr("width", 50)
    .attr("height", 50)
    .attr("x", -25)
    .attr("y", -25)
    .style("pointer-events", "none");

  nodeEnter
    .filter((d) => d.type === "country")
    .append("text")
    .attr("text-anchor", "middle")
    .attr("dy", "0.35em")
    .attr("fill", "#fff")
    .attr("font-size", "9px")
    .attr("font-weight", "600")
    .text((d) => d.id.replace("country => ", ""));

  // Tooltip events
  nodeEnter
    .on("mouseover", (event, d) => {
      const riskColor =
        d.reputation >= 70
          ? "risk-high"
          : d.reputation >= 40
          ? "risk-medium"
          : "risk-low";
      tooltip
        .style("opacity", 1)
        .html(
          `
          <strong>${d.id}</strong><br/>
          <span class="label">Location:</span> ${d.country || ""} ${
            d.city || ""
          }<br/>
          <span class="label">ASN:</span> ${d.asn || "N/A"}<br/>
          <span class="label">Org:</span> ${d.org || "N/A"}<br/>
          <span class="label">Type:</span> <strong>${
            d.network_type || d.type
          }</strong><br/>
          <span class="label">Risk:</span> <span class="${riskColor}">${
            d.reputation ?? "N/A"
          }</span>
        `
        )
        .style("left", event.pageX + 15 + "px")
        .style("top", event.pageY + 15 + "px");

      // Highlight connected links
      gLinks
        .selectAll("line")
        .attr("stroke-opacity", (l) =>
          l.source.id === d.id || l.target.id === d.id ? 1 : 0.2
        )
        .attr("stroke-width", (l) =>
          l.source.id === d.id || l.target.id === d.id ? 3 : 1.5
        );
    })
    .on("mousemove", (event) => {
      tooltip
        .style("left", event.pageX + 15 + "px")
        .style("top", event.pageY + 15 + "px");
    })
    .on("mouseout", () => {
      tooltip.style("opacity", 0);
      gLinks
        .selectAll("line")
        .attr("stroke-opacity", 0.6)
        .attr("stroke-width", (d) => {
          if (d.source.type === "server") return 2;
          return 1.5;
        });
    });

  // Update existing nodes
  node
    .select("circle")
    .attr("fill", nodeColor)
    .attr("stroke", (d) => d3.color(nodeColor(d)).brighter(0.5));

  node.exit().remove();

  // ---- LABELS for countries ----
  const labels = gLabels.selectAll("text.country-label").data(
    nodes.filter((n) => n.type === "country"),
    (d) => d.id
  );

  labels
    .enter()
    .append("text")
    .attr("class", "country-label")
    .attr("text-anchor", "middle")
    .attr("dy", 28)
    .attr("fill", "#888")
    .attr("font-size", "10px")
    .attr("font-family", "'Fira Code', monospace")
    .text((d) => d.id.replace("country => ", ""));

  labels.exit().remove();

  // Update simulation
  simulation.nodes(nodes);
  simulation.force("link").links(links);
  simulation.alpha(0.5).restart();

  updateStats();
}

// ================== TICK ==================
simulation.on("tick", () => {
  gLinks
    .selectAll("line")
    .attr("x1", (d) => d.source.x)
    .attr("y1", (d) => d.source.y)
    .attr("x2", (d) => d.target.x)
    .attr("y2", (d) => d.target.y);

  gNodes
    .selectAll("g.node")
    .attr("transform", (d) => `translate(${d.x},${d.y})`);

  gLabels
    .selectAll("text.country-label")
    .attr("x", (d) => d.x)
    .attr("y", (d) => d.y);
});

// ================== DRAG ==================
function dragStart(event, d) {
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
}
function dragDrag(event, d) {
  d.fx = event.x;
  d.fy = event.y;
}
function dragEnd(event, d) {
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null;
  d.fy = null;
}

// ================== RISK PULSING ==================
function pulseRisk() {
  gNodes
    .selectAll("g.node")
    .filter((d) => d.reputation >= 40)
    .select("circle")
    .classed("risk-glow", (d) => d.reputation >= 70)
    .transition()
    .duration((d) => (d.reputation >= 70 ? 700 : 1200))
    .ease(d3.easeSinInOut)
    .attr("r", (d) => {
      const base = d.type === "server" ? 25 : d.type === "country" ? 14 : 8;
      return base + Math.min(d.reputation / 15, 6);
    })
    .transition()
    .duration((d) => (d.reputation >= 70 ? 700 : 1200))
    .ease(d3.easeSinInOut)
    .attr("r", (d) =>
      d.type === "server" ? 25 : d.type === "country" ? 14 : 8
    )
    .on("end", pulseRisk);
}

// ================== WEBSOCKET ==================
const wsProtocol = location.protocol === "https:" ? "wss:" : "ws:";
const ws = new WebSocket(`${wsProtocol}//${location.hostname}:8765`);

const connectionDot = document.getElementById("connection-dot");
const connectionText = document.getElementById("connection-text");

ws.onopen = () => {
  console.log("[WS] Connected");
  connectionDot.classList.add("connected");
  connectionText.textContent = "Live";
};

ws.onerror = (e) => {
  console.error("[WS] Error", e);
  connectionText.textContent = "Error";
};

ws.onclose = () => {
  console.warn("[WS] Connection closed");
  connectionDot.classList.remove("connected");
  connectionText.textContent = "Disconnected";
};

// Process a single event and add to graph
function processEvent(data) {
  if (!data.ip) return;

  const geo = data.geo || data.data?.geo || {};
  const ip = data.ip || data.data?.ip;
  if (!ip) return;

  const country = geo.country || "UNK";

  // ---- COUNTRY NODE ----
  let countryNode = countryMap.get(country);
  if (!countryNode) {
    countryNode = {
      id: `country => ${country}`,
      type: "country",
    };
    countryMap.set(country, countryNode);
    nodes.push(countryNode);
    links.push({ source: HONEYPOT_ID, target: countryNode.id });
  }

  // Determine network type from geo flags
  let network_type = "RESIDENTIAL";
  if (geo.tor) network_type = "TOR";
  else if (geo.vpn) network_type = "VPN";
  else if (geo.hosting) network_type = "HOSTING";

  // ---- IP NODE ----
  let ipNode = nodeMap.get(ip);
  if (!ipNode) {
    ipNode = {
      id: ip,
      type: "attacker",
      country: country,
      city: geo.city || "UNK",
      asn: geo.asn || "UNK",
      org: geo.org || "UNK",
      network_type: network_type,
      reputation: data.risk ?? 0,
    };
    nodeMap.set(ip, ipNode);
    nodes.push(ipNode);
    links.push({ source: countryNode.id, target: ipNode.id });
  } else {
    ipNode.reputation = data.risk ?? ipNode.reputation;
    ipNode.network_type = network_type;
  }

  // Add to activity feed
  addActivity({ ...data, ip, geo });
}

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  // Handle history batch
  if (msg.type === "history" && Array.isArray(msg.events)) {
    console.log(`[WS] Loading ${msg.events.length} historical events`);
    for (const evt of msg.events) {
      const eventData = evt.data
        ? { ...evt, ...evt.data, ip: evt.data.ip }
        : evt;
      processEvent(eventData);
    }
    render();
    return;
  }

  // Handle real-time event
  processEvent(msg);
  render();
};

// ================== KEYBOARD SHORTCUTS ==================
document.addEventListener("keydown", (e) => {
  // R - Reset zoom
  if (e.key === "r" || e.key === "R") {
    svg
      .transition()
      .duration(500)
      .call(zoomBehavior.transform, d3.zoomIdentity.translate(0, 0).scale(1));
  }
  // F - Fit to screen
  if (e.key === "f" || e.key === "F") {
    const bounds = mainGroup.node().getBBox();
    const fullWidth = width;
    const fullHeight = height;
    const widthScale = fullWidth / bounds.width;
    const heightScale = fullHeight / bounds.height;
    const scale = Math.min(widthScale, heightScale) * 0.8;
    const tx = (fullWidth - bounds.width * scale) / 2 - bounds.x * scale;
    const ty = (fullHeight - bounds.height * scale) / 2 - bounds.y * scale;

    svg
      .transition()
      .duration(500)
      .call(
        zoomBehavior.transform,
        d3.zoomIdentity.translate(tx, ty).scale(scale)
      );
  }
});

// ================== INITIAL RENDER ==================
render();
pulseRisk();

// Center on honeypot initially
setTimeout(() => {
  const honeypotNode = nodes.find((n) => n.id === HONEYPOT_ID);
  if (honeypotNode) {
    svg
      .transition()
      .duration(1000)
      .call(
        zoomBehavior.transform,
        d3.zoomIdentity.translate(
          width / 2 - honeypotNode.x,
          height / 2 - honeypotNode.y
        )
      );
  }
}, 500);
