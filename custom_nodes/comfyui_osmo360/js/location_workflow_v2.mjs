// Keep existing workflow IDs while moving casting and direction out of extraction.
export const EXTRACTION_KEYS = [
  "panorama", "preset", "yaw_zero", "fov", "pitch", "roll", "projection", "strength",
  "width", "height", "view_count", "spacing", "starting_yaw", "upscale", "profile",
  "hdr_capture", "include_original", "location", "pair_secondary", "pair_same_position",
  "process_all", "queue_json"
];

const DEFAULT_VIDEO_PROMPT = "Create one 10-second cinematic video with exactly four shots and three cuts. " +
  "Images 1–5 are overlapping directions of one location. Preserve its architecture, vehicles, props and daylight. " +
  "Image 6 is Talent A and image 7 is Talent B; each identity sheet describes one person. Match their faces and wardrobe. " +
  "Keep both people on fixed marks facing each other. Shot 1, 0–3s: wide two-person establishing pan. " +
  "Shot 2, 3–5s: three-quarter over Talent A's shoulder onto Talent B. " +
  "Shot 3, 5–7s: reverse over Talent B's shoulder onto Talent A. " +
  "Shot 4, 7–10s: one continuous camera arc across their dialogue axis, ending in a wider environment pan " +
  "with both people still visible. Keep the same physical location and actor positions through every cut. " +
  "Full-frame live-action footage, no collage or text.";

function loadImage(node, filename, links, label) {
  node.type = "LocationReferenceImage";
  node.title = label;
  node.inputs = [];
  node.outputs = [{name:"IMAGE",type:"IMAGE",links}, {name:"MASK",type:"MASK",links:[]}];
  node.widgets_values = [filename, "image"];
  node.widgets_values_named = {image:filename};
  node.properties = {...node.properties, "Node name for S&R":"LocationReferenceImage"};
  node.size = [320, 300];
}

export function migrateLocationWorkflow(graph) {
  if (!Array.isArray(graph?.nodes) || !Array.isArray(graph.links)) return graph;
  const packs = graph.nodes.filter(n => n.type === "Osmo360ReferencePack");
  if (!packs.length) return graph;
  let nextId = Math.max(Number(graph.last_node_id)||0, ...graph.nodes.map(n=>Number(n.id)||0));
  const removed = new Set(), talentNodes = [];
  for (const pack of packs) {
    const values = pack.widgets_values || [];
    const named = pack.widgets_values_named || {};
    const legacy = values.length > EXTRACTION_KEYS.length || pack.outputs?.length > 4;
    const talents = [named.talent_a ?? values[22] ?? "", named.talent_b ?? values[23] ?? ""];
    if (legacy) {
      for (const link of graph.links.filter(l=>l[1]===pack.id && l[2]>=4)) {
        const target = graph.nodes.find(n=>n.id===link[3]);
        if (!target) { removed.add(link[0]); continue; }
        if (link[2]===4) {
          removed.add(link[0]);
          const input = target.inputs?.[link[4]];
          if (input) {
            input.link = null;
            delete target.properties?.osmo360Bindings?.[input.name];
            if (input.name === "model.prompt") {
              target.widgets_values ||= [];
              target.widgets_values[1] ||= DEFAULT_VIDEO_PROMPT;
              target.widgets_values_named ||= {};
              target.widgets_values_named[input.name] = target.widgets_values[1];
            }
          }
        } else if (link[2]===5 || link[2]===6) {
          const index = link[2]-5, filename = talents[index], label = "TALENT " + (index+1) + " / upload identity reference";
          if (target.type === "Osmo360SelectView") {
            const outgoing = graph.links.filter(l=>l[1]===target.id).map(l=>l[0]);
            loadImage(target, filename, outgoing, label);
            talentNodes.push(target);
            removed.add(link[0]);
          } else {
            const node = {id:++nextId,pos:[pack.pos[0]+500,pack.pos[1]+850+index*340],
              flags:{},order:0,mode:0,properties:{}};
            loadImage(node,filename,[link[0]],label);
            graph.nodes.push(node);talentNodes.push(node);
            link[1]=node.id;link[2]=0;
          }
        }
      }
      pack.widgets_values = values.slice(0, EXTRACTION_KEYS.length);
      pack.widgets_values_named = Object.fromEntries(EXTRACTION_KEYS.map((key,i)=>[key,named[key]??values[i]]));
      pack.outputs = (pack.outputs || []).slice(0,4);
      pack.size = [Math.max(pack.size?.[0]||400,400),780];
    }
    pack.title = "360 LOCATION EXTRACTOR / image and lens controls";
  }
  graph.links = graph.links.filter(l=>!removed.has(l[0]));
  for (const node of graph.nodes) {
    if (node.type === "LoadImage" && /^TALENT [12] \/ upload identity reference$/.test(node.title || ""))
      loadImage(node,node.widgets_values?.[0] || "",node.outputs?.[0]?.links || [],node.title);
    if (node.title) node.title = node.title.replace(/Osmo\s*360/gi,"360 Location");
    for (const output of node.outputs || []) output.links=[];
    for (const [name,binding] of Object.entries(node.properties?.osmo360Bindings||{})) {
      if (packs.some(p=>Number(p.id)===Number(binding.node)) && binding.slot>=4)
        delete node.properties.osmo360Bindings[name];
    }
  }
  for (const link of graph.links) {
    const source=graph.nodes.find(n=>n.id===link[1]), target=graph.nodes.find(n=>n.id===link[3]);
    source?.outputs?.[link[2]]?.links.push(link[0]);
    const input=target?.inputs?.[link[4]];
    if(input) {
      input.link=link[0];
      if(target.properties?.osmo360Bindings &&
          (input.name.startsWith("model.reference_") || target.properties.osmo360Bindings[input.name]))
        target.properties.osmo360Bindings[input.name]={node:link[1],slot:link[2]};
    }
  }
  if (talentNodes.length) {
    const xs=talentNodes.map(n=>n.pos[0]),ys=talentNodes.map(n=>n.pos[1]);
    for (const group of graph.groups || []) {
      if (/TILES.*TALENT/i.test(group.title)) {
        group.title="2: LOCATION REFERENCE TILES";
        if(group.bounding) group.bounding[3]=Math.max(100,Math.min(...ys)-group.bounding[1]-15);
      }
      if (/GENERATE AND REVIEW VIDEO/i.test(group.title)) group.title="4: VIDEO PROMPT AND GENERATION";
    }
    graph.groups ||= [];
    graph.groups.push({title:"3: TALENT INPUTS / VIDEO STAGE",bounding:[Math.min(...xs)-20,Math.min(...ys)-40,
      Math.max(...talentNodes.map(n=>n.pos[0]+n.size[0]))-Math.min(...xs)+40,
      Math.max(...talentNodes.map(n=>n.pos[1]+n.size[1]))-Math.min(...ys)+60],color:"#665b76",font_size:22,flags:{}});
  }
  graph.last_node_id=nextId;
  graph.extra ||= {};
  graph.extra.location_extractor_version="0.2.0";
  return graph;
}
