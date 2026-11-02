import assert from 'node:assert/strict';
import {readFileSync, readdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {migrateLocationWorkflow} from '../custom_nodes/comfyui_location360/js/location_workflow_v2.mjs';
import {checkComparisonWorkflow} from '../custom_nodes/comfyui_location360/tests/test_comparison_workflow.mjs';

const root = new URL('../', import.meta.url);
const directory = new URL('workflows/', root);
let count = 0;
for (const name of readdirSync(directory).filter(name => name.endsWith('.json'))) {
  const path = new URL(name, directory);
  const graph = JSON.parse(readFileSync(path, 'utf8'));
  migrateLocationWorkflow(graph);
  const nodes = new Map(graph.nodes.map(node => [node.id, node]));
  const links = new Map(graph.links.map(link => [link[0], link]));
  assert.equal(nodes.size, graph.nodes.length, `${name}: duplicate node IDs`);
  assert.equal(links.size, graph.links.length, `${name}: duplicate link IDs`);
  for (const link of graph.links) {
    const source = nodes.get(link[1]), target = nodes.get(link[3]);
    assert.ok(source?.outputs?.[link[2]], `${name}: missing source port`);
    assert.equal(target?.inputs?.[link[4]]?.link, link[0], `${name}: missing target port`);
    assert.ok(source.outputs[link[2]].links.includes(link[0]), `${name}: missing output binding`);
  }
  for (const node of graph.nodes) {
    for (const input of node.inputs || []) {
      if (input.link != null) assert.ok(links.has(input.link), `${name}: dangling input`);
    }
    if (node.type === 'Location360ReferencePack') {
      assert.equal(node.outputs.length, 4, `${name}: extractor output contract`);
      assert.equal(node.widgets_values[3], 115, `${name}: recommended horizontal FOV`);
      assert.equal(node.widgets_values[6], 'Natural Wide', `${name}: recommended projection`);
    }
    if (['ByteDance2ReferenceNodeV2', 'MinimaxHailuo03ReferenceNode'].includes(node.type)) {
      for (let index = 1; index <= 7; index++) {
        const input = node.inputs.find(port => port.name === `model.reference_images.image_${index}`);
        const link = links.get(input?.link);
        assert.ok(link, `${name}: reference ${index} is disconnected`);
        assert.equal(nodes.get(link[1]).type, index <= 5 ? 'Location360SelectView' : 'LocationReferenceImage');
      }
    }
  }
  if (graph.extra?.location_comparison) checkComparisonWorkflow(fileURLToPath(path));
  count++;
}
assert.equal(count, 4);
console.log(`${count} workflow graphs passed link, reference and extractor checks.`);
