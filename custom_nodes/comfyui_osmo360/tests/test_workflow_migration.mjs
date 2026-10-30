import assert from "node:assert/strict";
import { migrateLocationWorkflow, EXTRACTION_KEYS } from "../js/location_workflow_v2.mjs";

export function verifyMigration() {
  const settings = EXTRACTION_KEYS.map((name,i)=>name==="fov"?105:i);
  const graph = {nodes:[
    {id:30,type:"Osmo360ReferencePack",pos:[0,0],size:[400,900],
      widgets_values:[...settings,"cast/A.png","cast/B.png",216,70,50,1.6,60],
      outputs:["references","contact_sheet","reference_prompt","manifest","dialogue_prompt","talent_a","talent_b"].map(name=>({name,links:[]}))},
    {id:45,type:"Osmo360SelectView",pos:[500,900],inputs:[{name:"references",link:1}],outputs:[{name:"reference_image",links:[3]}],widgets_values:[0],properties:{osmo360Result:{images:[{filename:"kept.png"}]}}},
    {id:10,type:"ByteDance2ReferenceNodeV2",pos:[1000,0],inputs:[{name:"model.prompt",link:4},{name:"model.reference_images.image_6",link:3},{name:"model.reference_images.image_7",link:2}],outputs:[],
      widgets_values:["Seedance 2.5",""],properties:{osmo360Bindings:{"model.prompt":{node:30,slot:4},"model.reference_images.image_6":{node:45,slot:0},"model.reference_images.image_7":{node:30,slot:6}}}}
  ],links:[[1,30,5,45,0,"IMAGE"],[2,30,6,10,2,"IMAGE"],[3,45,0,10,1,"IMAGE"],[4,30,4,10,0,"STRING"]],groups:[],last_node_id:45};
  migrateLocationWorkflow(graph);
  const pack=graph.nodes.find(n=>n.id===30), a=graph.nodes.find(n=>n.id===45), video=graph.nodes.find(n=>n.id===10);
  assert.equal(pack.widgets_values[3],105);
  assert.equal(pack.outputs.length,4);
  assert.equal(pack.widgets_values.length,22);
  assert.equal(a.type,"LocationReferenceImage");
  assert.equal(a.widgets_values[0],"cast/A.png");
  assert.equal(a.properties.osmo360Result.images[0].filename,"kept.png");
  const b=graph.nodes.find(n=>n.type==="LocationReferenceImage" && n.id!==45);
  assert.equal(b.widgets_values[0],"cast/B.png");
  assert.equal(video.properties.osmo360Bindings["model.reference_images.image_7"].node,b.id);
  assert.equal(video.inputs[0].link,null);
  assert.ok(video.widgets_values[1].includes("four shots"));
  assert.ok(!graph.links.some(l=>l[1]===30 && l[2]>=4));
  const once=JSON.stringify(graph);
  migrateLocationWorkflow(graph);
  assert.equal(JSON.stringify(graph),once);
  return {checks:13,status:"passed"};
}

export const result = verifyMigration();
