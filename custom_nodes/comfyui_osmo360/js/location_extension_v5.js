import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { mountExtractor } from "./extractor_ui_v3.js";

import { migrateLocationWorkflow } from "./location_workflow_v2.mjs";
import { installComparisonControls } from "./comparison_controls_v1.mjs";

async function restoreOsmoBindings(){
    const graph=app.graph;
    for(let pass=0;pass<3;pass++){
      let pending=false;
      for(const node of graph._nodes){
        for(const [name,binding] of Object.entries(node.properties?.osmo360Bindings||{})){
          const index=node.inputs?.findIndex(input=>input.name===name);
          if(index<0){pending=true;continue;}
          if(node.inputs[index].link!=null)continue;
          const source=graph.getNodeById(Number(binding.node))||graph.getNodeById(binding.node);
          if(source)source.connect(binding.slot,node,index);
        }
      }
      if(!pending)break;
      await new Promise(resolve=>requestAnimationFrame(resolve));
    }
    graph.setDirtyCanvas(true,true);
}

app.registerExtension({
  name:"alvin.osmo360.reference-extractor",
  beforeConfigureGraph:migrateLocationWorkflow,
  afterConfigureGraph:restoreOsmoBindings,
  async afterLoadGraph(){
    await restoreOsmoBindings();
    const restored={};
    for(const node of app.graph._nodes){
      const result=node.properties?.osmo360Result;
      if(result){restored[String(node.id)]=result;node.onExecuted?.(result);}
    }
    if(Object.keys(restored).length)app.nodeOutputs={...app.nodeOutputs,...restored};
    installComparisonControls(app);
    app.graph.setDirtyCanvas(true,true);
  },
  async beforeRegisterNodeDef(nodeType,nodeData){
    if(nodeData.name==="SaveVideo"){
      const created=nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated=function(){
        created?.apply(this,arguments);
        const executed=this.onExecuted, started=this.onExecutionStart;
        this.onExecuted=function(result){
          if(result?.images?.some(item=>item.metadata?.kind==="video" || /\.(mp4|webm|mov|mkv)$/i.test(item.filename||""))){
            this.properties ||= {};
            this.properties.osmo360Result=result;
          }
          return executed?.apply(this,arguments);
        };
        this.onExecutionStart=function(){
          const result=this.properties?.osmo360Result;
          const returned=started?.apply(this,arguments);
          // A partial run must not blank the other model's completed player.
          if(this.graph?.extra?.location_comparison && result){
            app.nodeOutputs={...app.nodeOutputs,[String(this.id)]:result};
            this.onExecuted(result);
          }
          return returned;
        };
      };
      return;
    }
    if(["Osmo360SelectView","Osmo360PanoramaInput"].includes(nodeData.name)){
      const created=nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated=function(){created?.apply(this,arguments);this.setSize(nodeData.name==="Osmo360PanoramaInput"?[450,360]:[320,270]);};
      return;
    }
    if(nodeData.name!=="Osmo360ReferencePack")return;
    const previous=nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated=function(){
      previous?.apply(this,arguments);
      const node=this;
      node.properties ||= {};
      function sourceWidget(){
        const input=node.inputs?.find(input=>input.name==="panorama");
        const link=node.graph?.links.get(input?.link);
        const source=link&&node.graph.getNodeById(link.origin_id);
        return source?.type==="Osmo360PanoramaInput"?source.widgets?.find(widget=>widget.name==="image"):null;
      }
      const adapter={
        get(){const values=Object.fromEntries((node.widgets||[]).filter(w=>w.name!=="osmo360_panel").map(w=>[w.name,w.value]));const source=sourceWidget();if(source)values.panorama=source.value;return values;},
        set(values){for(const [key,value]of Object.entries(values)){const widget=node.widgets?.find(w=>w.name===key);if(widget)widget.value=value;if(key==="panorama"&&sourceWidget())sourceWidget().value=value;}app.graph?.setDirtyCanvas(true,true);},
        getQueue(){let queue=[];try{queue=JSON.parse(node.widgets?.find(w=>w.name==="queue_json")?.value||"[]");}catch{}const source=sourceWidget();if(source&&!queue.some(item=>item.path===source.value))queue.unshift({path:source.value,display_name:source.value.split("/").pop(),profile:"Panorama",yaw_zero:0});return queue;},
        setQueue(queue){const widget=node.widgets?.find(w=>w.name==="queue_json");if(widget)widget.value=JSON.stringify(queue);},
        fetch(path,options){return api.fetchApi(path,options);}
      };
      let panel=null,ui=null;
      function open(){
        if(panel){panel.focus();return;}
        panel=document.createElement("dialog");panel.setAttribute("aria-label","360 Location Extractor");
        Object.assign(panel.style,{width:"96vw",height:"92vh",maxWidth:"1700px",maxHeight:"none",padding:"0",border:"1px solid #53657b",borderRadius:"14px",background:"#17191d",color:"#edf3fa",overflow:"hidden"});
        const close=document.createElement("button");close.textContent="Close extractor";Object.assign(close.style,{position:"absolute",right:"16px",top:"12px",zIndex:"10",background:"#343d4b",color:"white",padding:"8px",borderRadius:"6px",border:"0",cursor:"pointer"});
        const host=document.createElement("div");host.style.height="100%";panel.append(host,close);document.body.append(panel);
        ui=mountExtractor(host,adapter);
        function dispose(){ui?.dispose();panel?.remove();panel=null;ui=null;}
        close.onclick=()=>panel.close();panel.addEventListener("close",dispose,{once:true});panel.showModal();
      }
      const summary=document.createElement("div");summary.style.padding="12px";
      const button=document.createElement("button");button.textContent="Open 360 Reference Extractor";Object.assign(button.style,{width:"100%",padding:"12px",background:"#087af5",color:"white",border:"none",borderRadius:"7px",cursor:"pointer"});button.onclick=open;summary.append(button);
      const refresh=document.createElement("button");refresh.textContent="Refresh image previews";refresh.style.cssText="width:100%;padding:10px;margin-top:8px;background:#293d4c;color:white;border:1px solid #4f7187;border-radius:7px;cursor:pointer";
      refresh.onclick=async()=>{
        refresh.disabled=true;
        try{
          const graph=node.graph;
          const targets=graph._nodes.filter(item=>item.type==="Osmo360SelectView"&&item.inputs?.some(input=>{const link=graph.links.get(input.link);return link?.origin_id===node.id;})).map(item=>String(item.id));
          await app.queuePrompt(0,1,{queueNodeIds:[String(node.id),...targets]});
        }finally{refresh.disabled=false;}
      };
      summary.append(refresh);
      const hint=document.createElement("div");hint.textContent="360 panorama → location reference tiles · image processing only";hint.style.cssText="font:12px system-ui;color:#a7bed7;padding:8px 0";summary.append(hint);
      node.addDOMWidget("osmo360_panel","osmo360",summary,{serialize:false});
      node.setSize([Math.max(node.size[0],400),Math.max(node.size[1],780)]);
      const oldRemoved=node.onRemoved;node.onRemoved=function(){ui?.dispose();panel?.remove();oldRemoved?.apply(this,arguments);};
    };
  }
});
