"""Generate an interactive HTML visualization of the decision tree."""

import json


def load_tree(path: str = "data/decision_tree.json") -> dict:
    with open(path) as f:
        return json.load(f)


def format_feedback(fb_key: str) -> str:
    """Convert feedback key to colored emoji string."""
    parts = fb_key.split("|")
    labels = ["T1", "T2", "Evo", "Full", "Col", "Hab", "Gen"]
    symbols = []
    for label, status in zip(labels, parts):
        if status == "correct":
            symbols.append(f'<span class="fb-correct">{label}✓</span>')
        elif status == "partial":
            symbols.append(f'<span class="fb-partial">{label}~</span>')
        elif status == "wrong":
            symbols.append(f'<span class="fb-wrong">{label}✗</span>')
        elif status == "wrong_higher":
            symbols.append(f'<span class="fb-wrong">{label}↑</span>')
        elif status == "wrong_lower":
            symbols.append(f'<span class="fb-wrong">{label}↓</span>')
    return " ".join(symbols)


def tree_to_d3(node: dict, fb_label: str = "START") -> dict:
    """Convert our tree format to D3 hierarchy format."""
    name = node["guess"]
    depth = node["depth"]
    pokemon_id = node["number"]

    result = {
        "name": name,
        "pokemonId": pokemon_id,
        "depth": depth,
        "fbLabel": fb_label,
        "children": [],
    }

    if "indistinguishable" in node:
        result["indistinguishable"] = node["indistinguishable"]

    if "children" in node:
        for fb_key, child in node["children"].items():
            result["children"].append(tree_to_d3(child, fb_key))

    return result


def count_descendants(node: dict) -> int:
    """Count total answers reachable from this node."""
    if "indistinguishable" in node:
        return len(node["indistinguishable"])
    if not node.get("children"):
        return 1
    return sum(count_descendants(c) for c in node["children"])


def generate_html(tree_data: dict) -> str:
    d3_tree = tree_to_d3(tree_data)
    tree_json = json.dumps(d3_tree)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pokedle Decision Tree</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #1a1a2e;
    color: #e0e0e0;
    overflow: hidden;
  }}
  #header {{
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    background: linear-gradient(135deg, #16213e, #1a1a2e);
    padding: 12px 24px;
    display: flex; align-items: center; gap: 20px;
    border-bottom: 1px solid #333;
    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
  }}
  #header h1 {{
    font-size: 18px; font-weight: 600;
    background: linear-gradient(90deg, #e74c3c, #f39c12, #2ecc71, #3498db, #9b59b6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }}
  #header .stats {{
    font-size: 13px; color: #888;
    display: flex; gap: 16px;
  }}
  #header .stats span {{ color: #aaa; }}
  #header .stats b {{ color: #f0f0f0; }}
  #legend {{
    display: flex; gap: 12px; margin-left: auto; font-size: 12px;
  }}
  .legend-item {{
    display: flex; align-items: center; gap: 4px;
  }}
  .legend-dot {{
    width: 10px; height: 10px; border-radius: 50%;
  }}
  #controls {{
    position: fixed; bottom: 20px; right: 20px; z-index: 100;
    display: flex; flex-direction: column; gap: 8px;
  }}
  #controls button {{
    background: #16213e; border: 1px solid #444; color: #ddd;
    padding: 8px 12px; border-radius: 6px; cursor: pointer;
    font-size: 13px; transition: all 0.2s;
  }}
  #controls button:hover {{ background: #1f3460; border-color: #666; }}
  #tree-container {{
    width: 100vw; height: 100vh; padding-top: 52px;
  }}
  .node circle {{
    stroke-width: 2px;
    cursor: pointer;
    transition: all 0.2s;
  }}
  .node circle:hover {{
    filter: brightness(1.3);
    stroke-width: 3px;
  }}
  .node text {{
    font-size: 11px;
    fill: #ddd;
    pointer-events: none;
  }}
  .node .pokemon-name {{
    font-weight: 600;
    font-size: 12px;
  }}
  .link {{
    fill: none;
    stroke-opacity: 0.4;
    stroke-width: 1.5px;
  }}
  .fb-label {{
    font-size: 9px;
    fill: #888;
  }}
  .tooltip {{
    position: fixed;
    background: #16213e;
    border: 1px solid #444;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 13px;
    pointer-events: none;
    z-index: 200;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    max-width: 300px;
    display: none;
  }}
  .tooltip .pokemon-header {{
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 8px; font-size: 16px; font-weight: 600;
  }}
  .tooltip img {{
    width: 48px; height: 48px; image-rendering: pixelated;
  }}
  .tooltip .fb-correct {{ color: #2ecc71; font-weight: 600; }}
  .tooltip .fb-partial {{ color: #f39c12; font-weight: 600; }}
  .tooltip .fb-wrong {{ color: #e74c3c; font-weight: 600; }}
  .tooltip .info-line {{
    margin: 4px 0; color: #aaa;
  }}
  .tooltip .indist {{
    margin-top: 8px; padding-top: 8px; border-top: 1px solid #333;
    color: #f39c12; font-size: 12px;
  }}
</style>
</head>
<body>
<div id="header">
  <h1>Pokedle Optimal Decision Tree</h1>
  <div class="stats">
    <span>First guess: <b>Nidorina</b></span>
    <span>Avg: <b>2.93</b></span>
    <span>Worst: <b>6</b></span>
    <span>Pokemon: <b>151</b></span>
  </div>
  <div id="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#2ecc71"></div> Depth 1</div>
    <div class="legend-item"><div class="legend-dot" style="background:#3498db"></div> Depth 2</div>
    <div class="legend-item"><div class="legend-dot" style="background:#9b59b6"></div> Depth 3</div>
    <div class="legend-item"><div class="legend-dot" style="background:#e74c3c"></div> Depth 4</div>
    <div class="legend-item"><div class="legend-dot" style="background:#f39c12"></div> Depth 5+</div>
    <div class="legend-item"><div class="legend-dot" style="background:#f39c12; border: 2px solid #e74c3c;"></div> Indistinguishable</div>
  </div>
</div>

<div id="controls">
  <button onclick="expandAll()">Expand All</button>
  <button onclick="collapseAll()">Collapse All</button>
  <button onclick="expandToDepth(2)">Depth 2</button>
  <button onclick="expandToDepth(3)">Depth 3</button>
  <button onclick="resetZoom()">Reset Zoom</button>
</div>

<div id="tooltip" class="tooltip"></div>
<div id="tree-container"></div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const treeData = {tree_json};

const depthColors = {{
  1: "#2ecc71",
  2: "#3498db",
  3: "#9b59b6",
  4: "#e74c3c",
  5: "#f39c12",
  6: "#f39c12",
}};

const margin = {{ top: 20, right: 120, bottom: 20, left: 120 }};
const container = document.getElementById("tree-container");
const width = window.innerWidth;
const height = window.innerHeight - 52;

const svg = d3.select("#tree-container")
  .append("svg")
  .attr("width", width)
  .attr("height", height);

const g = svg.append("g");

const zoom = d3.zoom()
  .scaleExtent([0.1, 4])
  .on("zoom", (event) => g.attr("transform", event.transform));
svg.call(zoom);

const treemap = d3.tree().nodeSize([22, 220]);

const root = d3.hierarchy(treeData, d => d.children && d.children.length > 0 ? d.children : null);
root.x0 = height / 2;
root.y0 = 0;

// Initially collapse all except root's children
root.children?.forEach(c => collapse(c));

function collapse(d) {{
  if (d.children) {{
    d._children = d.children;
    d._children.forEach(collapse);
    d.children = null;
  }}
}}

function expand(d) {{
  if (d._children) {{
    d.children = d._children;
    d._children = null;
    d.children.forEach(expand);
  }}
}}

function expandToDepthHelper(d, targetDepth) {{
  if (d.data.depth < targetDepth) {{
    if (d._children) {{
      d.children = d._children;
      d._children = null;
    }}
    if (d.children) d.children.forEach(c => expandToDepthHelper(c, targetDepth));
  }} else {{
    if (d.children) {{
      d._children = d.children;
      d._children.forEach(collapse);
      d.children = null;
    }}
  }}
}}

let i = 0;
const duration = 400;
const tooltip = document.getElementById("tooltip");

function spriteUrl(id) {{
  return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${{id}}.png`;
}}

function formatFeedback(fbKey) {{
  const parts = fbKey.split("|");
  const labels = ["T1", "T2", "Evo", "Full", "Col", "Hab", "Gen"];
  return parts.map((s, i) => {{
    if (s === "correct") return `<span class="fb-correct">${{labels[i]}}✓</span>`;
    if (s === "partial") return `<span class="fb-partial">${{labels[i]}}~</span>`;
    if (s === "wrong") return `<span class="fb-wrong">${{labels[i]}}✗</span>`;
    if (s === "wrong_higher") return `<span class="fb-wrong">${{labels[i]}}↑</span>`;
    if (s === "wrong_lower") return `<span class="fb-wrong">${{labels[i]}}↓</span>`;
    return s;
  }}).join(" ");
}}

function countDescendants(d) {{
  if (d.data.indistinguishable) return d.data.indistinguishable.length;
  if (!d.children && !d._children) return 1;
  const kids = d.children || d._children || [];
  return kids.reduce((sum, c) => sum + countDescendants(c), 0);
}}

function update(source) {{
  const treeLayout = treemap(root);
  const nodes = treeLayout.descendants();
  const links = treeLayout.links();

  // Normalize for fixed depth
  nodes.forEach(d => {{ d.y = d.depth * 220; }});

  // Nodes
  const node = g.selectAll("g.node")
    .data(nodes, d => d.id || (d.id = ++i));

  const nodeEnter = node.enter().append("g")
    .attr("class", "node")
    .attr("transform", d => `translate(${{source.y0}},${{source.x0}})`)
    .on("click", (event, d) => {{
      if (d.children) {{
        d._children = d.children;
        d.children = null;
      }} else if (d._children) {{
        d.children = d._children;
        d._children = null;
      }}
      update(d);
    }})
    .on("mouseover", (event, d) => {{
      const data = d.data;
      let html = `<div class="pokemon-header">
        <img src="${{spriteUrl(data.pokemonId)}}" alt="${{data.name}}">
        <span>${{data.name}} #${{data.pokemonId}}</span>
      </div>`;
      html += `<div class="info-line">Depth: ${{data.depth}} | Descendants: ${{countDescendants(d)}}</div>`;
      if (data.fbLabel !== "START") {{
        html += `<div style="margin:6px 0">${{formatFeedback(data.fbLabel)}}</div>`;
      }}
      if (data.indistinguishable) {{
        html += `<div class="indist">⚠ Indistinguishable (${{data.indistinguishable.length}}): ${{data.indistinguishable.join(", ")}}</div>`;
      }}
      const hasKids = d.children || d._children;
      if (hasKids) {{
        const kids = d.children || d._children;
        html += `<div class="info-line">${{kids.length}} branches</div>`;
      }}
      tooltip.innerHTML = html;
      tooltip.style.display = "block";
      tooltip.style.left = (event.clientX + 16) + "px";
      tooltip.style.top = (event.clientY - 16) + "px";
    }})
    .on("mousemove", (event) => {{
      tooltip.style.left = (event.clientX + 16) + "px";
      tooltip.style.top = (event.clientY - 16) + "px";
    }})
    .on("mouseout", () => {{ tooltip.style.display = "none"; }});

  nodeEnter.append("circle")
    .attr("r", 1e-6)
    .style("fill", d => {{
      if (d.data.indistinguishable) return "#f39c12";
      return d._children ? depthColors[d.data.depth] || "#f39c12" : "#1a1a2e";
    }})
    .style("stroke", d => {{
      if (d.data.indistinguishable) return "#e74c3c";
      return depthColors[d.data.depth] || "#f39c12";
    }});

  nodeEnter.append("text")
    .attr("class", "pokemon-name")
    .attr("dy", ".35em")
    .attr("x", d => (d.children || d._children) ? -14 : 14)
    .attr("text-anchor", d => (d.children || d._children) ? "end" : "start")
    .text(d => {{
      let label = d.data.name;
      if (d.data.indistinguishable) label += ` (+${{d.data.indistinguishable.length - 1}})`;
      return label;
    }});

  // UPDATE
  const nodeUpdate = nodeEnter.merge(node);

  nodeUpdate.transition().duration(duration)
    .attr("transform", d => `translate(${{d.y}},${{d.x}})`);

  nodeUpdate.select("circle")
    .attr("r", d => d.data.indistinguishable ? 7 : 5)
    .style("fill", d => {{
      if (d.data.indistinguishable) return "#f39c12";
      return d._children ? depthColors[d.data.depth] || "#f39c12" : "#1a1a2e";
    }})
    .style("stroke", d => {{
      if (d.data.indistinguishable) return "#e74c3c";
      return depthColors[d.data.depth] || "#f39c12";
    }});

  nodeUpdate.select("text")
    .attr("x", d => (d.children || d._children) ? -14 : 14)
    .attr("text-anchor", d => (d.children || d._children) ? "end" : "start");

  // EXIT
  const nodeExit = node.exit().transition().duration(duration)
    .attr("transform", d => `translate(${{source.y}},${{source.x}})`)
    .remove();
  nodeExit.select("circle").attr("r", 1e-6);
  nodeExit.select("text").style("fill-opacity", 1e-6);

  // Links
  const link = g.selectAll("path.link")
    .data(links, d => d.target.id);

  const linkEnter = link.enter().insert("path", "g")
    .attr("class", "link")
    .style("stroke", d => depthColors[d.target.data.depth] || "#f39c12")
    .attr("d", d => {{
      const o = {{ x: source.x0, y: source.y0 }};
      return diagonal(o, o);
    }});

  linkEnter.merge(link).transition().duration(duration)
    .attr("d", d => diagonal(d.source, d.target));

  link.exit().transition().duration(duration)
    .attr("d", d => {{
      const o = {{ x: source.x, y: source.y }};
      return diagonal(o, o);
    }}).remove();

  nodes.forEach(d => {{ d.x0 = d.x; d.y0 = d.y; }});
}}

function diagonal(s, d) {{
  return `M ${{s.y}} ${{s.x}}
    C ${{(s.y + d.y) / 2}} ${{s.x}},
      ${{(s.y + d.y) / 2}} ${{d.x}},
      ${{d.y}} ${{d.x}}`;
}}

function expandAll() {{ expand(root); update(root); }}
function collapseAll() {{ root.children?.forEach(collapse); update(root); }}
function expandToDepth(d) {{ expandToDepthHelper(root, d); update(root); }}
function resetZoom() {{
  svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(100, height / 2));
}}

// Initial render
update(root);
resetZoom();
</script>
</body>
</html>"""


def main():
    tree = load_tree()
    html = generate_html(tree)
    with open("tree_visualization.html", "w") as f:
        f.write(html)
    print("Saved to tree_visualization.html")


if __name__ == "__main__":
    main()
