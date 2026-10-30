const TYPES = {seedance:"ByteDance2ReferenceNodeV2", minimax:"MinimaxHailuo03ReferenceNode"};

// Select output nodes only; Comfy resolves their upstream dependencies.
export function comparisonTargets(graph, selection) {
  const config = graph.extra?.location_comparison;
  if (!config) throw new Error("This workflow has no comparison configuration.");
  const nodes = graph._nodes || graph.nodes || [];
  const find = id => nodes.find(node => String(node.id) === String(id));
  if (selection === "preview") {
    return config.preview_nodes.map(id => {
      if (!find(id)) throw new Error("An input preview node is missing.");
      return String(id);
    });
  }
  const models = selection === "both" ? Object.keys(TYPES) : [selection];
  return models.map(model => {
    const branch = config[model];
    if (!branch || find(branch.model)?.type !== TYPES[model] || find(branch.output)?.type !== "SaveVideo")
      throw new Error("The selected video branch is missing. Reload the comparison workflow.");
    return String(branch.output);
  });
}

export function installComparisonControls(app) {
  const graph = app.graph, config = graph.extra?.location_comparison;
  if (!config) return;
  const node = graph.getNodeById(Number(config.prompt_node));
  if (!node || node.widgets?.some(widget => widget.name === "location_comparison_controls")) return;
  const host = document.createElement("div");
  host.style.cssText = "padding:10px;color:#e8eef6;font:12px system-ui;box-sizing:border-box";
  const label = document.createElement("div");
  label.textContent = "Shared inputs → choose a video model";
  label.style.cssText = "font-weight:600;margin-bottom:8px";
  host.append(label);
  const row = document.createElement("div");
  row.style.cssText = "display:grid;grid-template-columns:1fr 1fr;gap:6px";
  const status = document.createElement("div");
  status.textContent = "Input previews are local. Video runs use the selected Comfy workspace credits.";
  status.style.cssText = "margin-top:8px;line-height:1.4;color:#bdd0e4";
  const buttons = [];
  for (const [selection, text] of [["preview","Preview inputs · local"],["both","Run both · credits"],
      ["seedance","Run Seedance · credits"],["minimax","Run MiniMax · credits"]]) {
    const button = document.createElement("button");
    button.type = "button"; button.textContent = text;
    button.style.cssText = "padding:9px 5px;border:1px solid #64748b;border-radius:6px;background:#263d54;color:white;cursor:pointer;font:12px system-ui";
    button.onclick = async () => {
      buttons.forEach(item => item.disabled = true);
      try {
        const targets = comparisonTargets(graph, selection);
        const accepted = await app.queuePrompt(0, 1, {queueNodeIds:targets});
        status.textContent = accepted === false ? "Check ComfyUI's queue or error message." :
          selection === "preview" ? "Input previews queued locally; no video generation requested." :
          "Video request queued. Check the queue and the selected model's video preview.";
      } catch (error) { status.textContent = error.message; }
      finally { buttons.forEach(item => item.disabled = false); }
    };
    buttons.push(button); row.append(button);
  }
  host.append(row, status);
  node.addDOMWidget("location_comparison_controls", "location_comparison", host, {serialize:false});
  node.setSize([Math.max(node.size[0], 500), Math.max(node.size[1], 680)]);
  graph.setDirtyCanvas(true, true);
}
