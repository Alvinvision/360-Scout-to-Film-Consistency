import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {comparisonTargets} from "../js/comparison_controls_v1.mjs";

export function checkComparisonWorkflow(path) {
assert.ok(path, "Pass the combined workflow JSON path.");
const graph = JSON.parse(readFileSync(path, "utf8"));
const nodes = new Map(graph.nodes.map(n => [n.id, n]));
const links = new Map(graph.links.map(l => [l[0], l]));
function source(id, input) {
  const node = nodes.get(id), port = node.inputs.find(p => p.name === input);
  const link = links.get(port?.link);
  return link && [link[1], link[2]];
}
function dependencies(targets) {
  const found = new Set();
  function visit(id) {
    id = Number(id); if (found.has(id)) return; found.add(id);
    for (const input of nodes.get(id).inputs || []) {
      const link = links.get(input.link); if (link) visit(link[1]);
    }
  }
  targets.forEach(visit); return found;
}
for (const link of graph.links) {
  assert.equal(nodes.get(link[3]).inputs[link[4]].link, link[0]);
  assert.ok(nodes.get(link[1]).outputs[link[2]].links.includes(link[0]));
}
for (let i=1; i<=7; i++) {
  const name = `model.reference_images.image_${i}`;
  assert.deepEqual(source(5010,name), source(2010,name), `Reference ${i} must be identical.`);
}
assert.equal(source(5010,"model.reference_images.image_8"), undefined);
assert.deepEqual(source(5010,"model.prompt"), [5090,0]);
assert.deepEqual(source(2010,"model.prompt"), [5090,0]);
assert.deepEqual(comparisonTargets(graph,"both"), ["5020","2020"]);
const seed = dependencies(comparisonTargets(graph,"seedance"));
const mini = dependencies(comparisonTargets(graph,"minimax"));
const preview = dependencies(comparisonTargets(graph,"preview"));
assert.ok(seed.has(5010) && !seed.has(2010));
assert.ok(mini.has(2010) && !mini.has(5010));
assert.ok(!preview.has(5010) && !preview.has(2010));
assert.ok(preview.has(5045) && preview.has(5046) && preview.has(5025));
const missing = structuredClone(graph); missing.nodes = missing.nodes.filter(n => n.id !== 2020);
assert.throws(() => comparisonTargets(missing,"minimax"), /branch is missing/);
return "Shared references, shared prompt, links and all four execution selections passed.";
}
if (typeof process !== "undefined" && process.argv[1]?.endsWith("test_comparison_workflow.mjs")) console.log(checkComparisonWorkflow(process.argv[2]));
