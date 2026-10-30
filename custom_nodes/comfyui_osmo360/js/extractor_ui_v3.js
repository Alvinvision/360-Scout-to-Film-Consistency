export const PRESETS = {
  "Seedance Landscape": [5,72,100,2048,1152],
  "Compact Landscape": [4,90,110,2048,1152],
  "Detailed Landscape": [6,60,90,2048,1152],
  "Spatial Square": [6,60,90,2048,2048],
  "Custom": [5,72,100,2048,1152]
};

export function mountExtractor(host, adapter) {
  const style = document.createElement("style");
  style.textContent = ".osmo360{height:100%;min-height:600px;display:grid;grid-template-columns:230px minmax(0,1fr);background:#17191d;color:#e9edf3;font:14px system-ui;box-sizing:border-box}.osmo360 *{box-sizing:border-box}.osmo360 aside{padding:20px 12px;background:#202328;border-right:1px solid #3a3f48;overflow:auto}.osmo360 main{padding:24px;overflow:auto}.osmo360 h2{font-size:20px;margin:0}.osmo360 h3{font-size:14px;margin:0 0 14px}.osmo360 p{color:#a7b1bf;line-height:1.5}.osmo360 section{border:1px solid #353b45;border-radius:12px;padding:18px;margin:16px 0;background:#1c1f25}.osmo360 button,.osmo360 select,.osmo360 input,.osmo360 textarea{font:inherit;color:inherit;background:#292e37;border:1px solid #454e5b;border-radius:6px;padding:8px}.osmo360 button{cursor:pointer}.osmo360 button:hover{background:#384658}.osmo360 button.primary{background:#087af5;border-color:#087af5}.osmo360 button:disabled{opacity:.45;cursor:default}.osmo360 .row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:10px 0}.osmo360 .field{display:flex;flex-direction:column;gap:6px;flex:1;min-width:150px;color:#b5c1cf}.osmo360 input[type=number]{width:90px}.osmo360 input[type=range]{flex:1;min-width:140px;padding:0;accent-color:#228dff}.osmo360 input[type=checkbox]{accent-color:#228dff}.osmo360 .source{display:block;width:100%;text-align:left;margin:8px 0;word-break:break-word}.osmo360 .selected{border-color:#268dff;background:#164778}.osmo360 small{display:block;color:#9eafc3;margin-top:5px}.osmo360 .grid{display:flex;flex-wrap:wrap;gap:14px;justify-content:center}.osmo360 .tile{flex:0 1 calc(33.333% - 14px);min-width:160px;cursor:pointer}.osmo360 .picture{position:relative;overflow:hidden;background:#11161d;border-radius:6px}.osmo360 img{display:block;width:100%;object-fit:contain}.osmo360 .band{position:absolute;top:0;bottom:0;background:#6cbeff2e;pointer-events:none;border-color:#87c9ff88;border-style:solid;border-width:0 1px}.osmo360 .front{cursor:ew-resize;touch-action:none;max-width:900px;margin:auto}.osmo360 .front img{max-height:330px;user-select:none;pointer-events:none}.osmo360 .badge{background:#294563;color:#b9dcff;border-radius:12px;padding:4px 10px;font-size:12px}.osmo360 .muted{color:#9eafc3}.osmo360 .status{min-height:24px;color:#a8d4ff;white-space:pre-wrap}.osmo360 textarea{width:100%;min-height:160px;resize:vertical;line-height:1.5}.osmo360 .drop{border:1px dashed #5c6a7f;text-align:center;padding:18px;border-radius:10px}.osmo360 .downloads a{color:#8ecaff;margin-right:16px}.osmo360 details{margin:12px 0}.osmo360 summary{cursor:pointer;color:#b9c9dc}.osmo360 .toolbar{display:flex;align-items:center;justify-content:space-between;gap:14px}.osmo360 .enlarged{position:fixed;inset:6vh 5vw;background:#12171ff5;border:1px solid #5a6b80;border-radius:12px;z-index:10002;padding:18px;display:flex;flex-direction:column;overflow:auto}.osmo360 .enlarged img{flex:1;min-height:0;object-fit:contain}.osmo360 .enlarged button{align-self:flex-end}.osmo360 label.check{display:flex;gap:8px;align-items:center;margin:12px 0}.osmo360 .error{color:#ffb1a5}@media(max-width:800px){.osmo360{grid-template-columns:170px minmax(0,1fr)}.osmo360 main{padding:12px}.osmo360 .tile{flex-basis:calc(50% - 14px)}}";
  host.append(style);
  const root = document.createElement("div"); root.className="osmo360"; host.append(root);
  root.innerHTML = '<aside><h3>360 LOCATION</h3><div class="queue"></div><button class="add">Add panoramas</button><button class="folder">Add folder</button><p class="muted">The uploaded source copies remain unchanged.</p></aside><main><div class="toolbar"><div><h2>360 Location Extractor</h2><small>Perspective references from a 2:1 lat-long panorama</small></div><span class="badge">Location reference studio</span></div><div class="drop">Drop panoramas here or use Add panoramas.<small>JPEG · PNG · TIFF · HEIC with the decoder installed</small></div><div class="status" role="status"></div><section class="extraction"><h3>Extraction</h3><div class="fields"></div></section><section><div class="toolbar"><h3>Front direction</h3><button class="zero">Set as 000°</button></div><div class="front picture"><img alt="Front-direction panorama preview" draggable="false"></div><small class="front-label">Drag horizontally to choose the front.</small></section><section><div class="toolbar"><h3>Reference view preview</h3><button class="reset">Reset to preset</button></div><div class="summary muted"></div><label class="check"><input class="overlap" type="checkbox">Show overlap</label><div class="grid"></div><div class="camera-controls"></div></section><section class="location-prompt"><h3>Location and lens reference</h3><textarea class="prompt" aria-label="Location and lens reference prompt" readonly></textarea><button class="copy-reference">Copy location prompt</button></section><section><div class="row"><button class="export primary">Export references</button><button class="cancel" disabled>Cancel export</button></div><div class="progress" role="status"></div><div class="downloads"></div></section></main>';
  const $ = selector => root.querySelector(selector);
  let queue = adapter.getQueue() || [], selected = adapter.get().panorama || queue[0]?.path || "";
  let previews=[], prompt="", pending, timer, generation=0, exportJob=null, disposed=false;
  const controls = new Map();
  const abort = new AbortController();
  const on = (element, event, callback) => element.addEventListener(event,callback,{signal:abort.signal});
  function status(text, error=false) { $(".status").textContent=text; $(".status").classList.toggle("error",error); }
  function storeQueue() { adapter.setQueue(queue); adapter.set({queue_json:JSON.stringify(queue)}); renderQueue(); }
  function change(key,value) {
    adapter.set({[key]:value});
    if(key==="yaw_zero") { const source=queue.find(x=>x.path===selected); if(source)source.yaw_zero=value; storeQueue(); }
    schedule();
  }
  function field(parent,label,key,type,options) {
    const wrap=document.createElement("label");wrap.className="field";wrap.append(document.createTextNode(label));
    let input=document.createElement(type==="select"?"select":"input");
    if(type==="select") for(const value of options){const option=document.createElement("option");option.value=value;option.textContent=value;input.append(option);}
    else input.type=type;
    input.setAttribute("aria-label",label);input.value=adapter.get()[key] ?? "";
    on(input,"change",()=>change(key,type==="number"?Number(input.value):input.value));
    controls.set(key,input);wrap.append(input);parent.append(wrap);return input;
  }
  function check(parent,label,key) {
    const wrap=document.createElement("label");wrap.className="check";const input=document.createElement("input");input.type="checkbox";input.checked=!!adapter.get()[key];
    on(input,"change",()=>change(key,input.checked));wrap.append(input,document.createTextNode(label));parent.append(wrap);controls.set(key,input);
  }
  function slider(parent,label,key,min,max,step=1) {
    const section=document.createElement("div");section.className="row";
    const title=document.createElement("span");title.textContent=label;section.append(title);
    const range=document.createElement("input");range.type="range";Object.assign(range,{min,max,step,value:adapter.get()[key]});
    const numeric=document.createElement("input");numeric.type="number";numeric.value=range.value;numeric.step=step;numeric.setAttribute("aria-label",label);
    function apply(value){range.value=value;numeric.value=value;change(key,Number(value));}
    on(range,"input",()=>apply(range.value));on(numeric,"input",()=>apply(numeric.value));on(numeric,"change",()=>apply(numeric.value));
    section.append(range,numeric);parent.append(section);controls.set(key,{set value(v){range.value=v;numeric.value=v;}});
  }
  function refreshControls() { const state=adapter.get(); for(const [key,input] of controls) { if(input.type==="checkbox")input.checked=!!state[key];else input.value=state[key]??""; } }
  function renderQueue() {
    const list=$(".queue");list.replaceChildren();
    for(const source of queue){
      const button=document.createElement("button");button.className="source"+(source.path===selected?" selected":"");
      button.textContent=source.display_name || source.filename;const note=document.createElement("small");note.textContent=(source.profile||"Panorama")+" / front "+Math.round(source.yaw_zero||0)+"°";button.append(note);
      on(button,"click",()=>{selected=source.path;adapter.set({panorama:selected,yaw_zero:source.yaw_zero||0});refreshControls();renderQueue();schedule();});
      const remove=document.createElement("button");remove.textContent="Remove";remove.title="Remove from queue; keep uploaded file";
      on(remove,"click",()=>{queue=queue.filter(x=>x!==source);if(selected===source.path){selected=queue[0]?.path||"";adapter.set({panorama:selected,yaw_zero:queue[0]?.yaw_zero||0});}storeQueue();refreshControls();schedule();});
      list.append(button,remove);
    }
    $(".export").disabled=!selected;
  }
  const fields=$(".fields");const first=document.createElement("div");first.className="row";fields.append(first);
  field(first,"Location name","location","text");field(first,"Source profile","profile","select",["Auto Detect","120MP DETAIL","30MP PANORAMA","30MP HDR","360 PANORAMA"]);
  const preset=field(first,"Reference pack","preset","select",Object.keys(PRESETS));
  on(preset,"change",()=>{
    const name=preset.value;if(name!=="Custom"){const p=PRESETS[name];adapter.set({preset:name,view_count:p[0],spacing:p[1],fov:p[2],width:p[3],height:p[4],pitch:0});refreshControls();schedule();}
  });
  check(fields,"Include the original 360 panorama in the pack","include_original");
  check(fields,"Process every panorama in the queue","process_all");
  const advanced=document.createElement("details");advanced.innerHTML="<summary>Advanced settings and paired captures</summary>";fields.append(advanced);
  const adv=document.createElement("div");adv.className="row";advanced.append(adv);
  for(const [label,key] of [["View count","view_count"],["Yaw spacing","spacing"],["Starting yaw","starting_yaw"],["Roll","roll"],["Output width","width"],["Output height","height"]])field(adv,label,key,"number");
  const resolution=field(adv,"Output resolution","resolution_mode","select",["AI Reference","Maximum Extract","Custom"]);
  on(resolution,"change",()=>{if(resolution.value!=="Custom"){const p=PRESETS[adapter.get().preset];const scale=resolution.value==="Maximum Extract"?2:1;adapter.set({width:p[3]*scale,height:p[4]*scale});refreshControls();schedule();}});
  check(advanced,"Allow output above the profile-safe cap","upscale");
  field(adv,"Secondary panorama path from the queue","pair_secondary","text");
  const pairSelect=document.createElement("select");const none=document.createElement("option");none.value="";none.textContent="Choose secondary capture from queue";pairSelect.append(none);advanced.append(pairSelect);
  on(pairSelect,"focus",()=>{pairSelect.replaceChildren(none);for(const item of queue)if(item.path!==selected){const option=document.createElement("option");option.value=item.path;option.textContent=item.display_name||item.filename;pairSelect.append(option);}});
  on(pairSelect,"change",()=>{change("pair_secondary",pairSelect.value);refreshControls();});
  check(advanced,"Both paired captures were taken at the same physical position","pair_same_position");
  check(advanced,"I confirm the 30MP capture is HDR","hdr_capture");
  const camera=$(".camera-controls");
  slider(camera,"Horizontal field of view","fov",90,120);
  const quick=document.createElement("div");quick.className="row";camera.append(quick);
  for(const value of [90,100,105,110,115,120]){const button=document.createElement("button");button.textContent=value+"°";on(button,"click",()=>{change("fov",value);refreshControls();});quick.append(button);}
  slider(camera,"Pitch","pitch",-20,20);const pitchReset=document.createElement("button");pitchReset.textContent="Reset pitch to 0°";on(pitchReset,"click",()=>{change("pitch",0);refreshControls();});camera.append(pitchReset);
  const projection=document.createElement("div");projection.className="row";camera.append(projection);
  field(projection,"Projection style","projection","select",["Rectilinear","Natural Wide"]);
  slider(camera,"Natural Wide edge-stretch reduction","strength",0,100);
  on($(".reset"),"click",()=>{const p=PRESETS[adapter.get().preset];adapter.set({fov:p[2],pitch:0});refreshControls();schedule();});
  let drag=null;
  on($(".front"),"pointerdown",e=>{drag={x:e.clientX,yaw:Number(adapter.get().yaw_zero)||0};$(".front").setPointerCapture(e.pointerId);e.preventDefault();});
  on($(".front"),"pointermove",e=>{if(drag){const span=$(".front").clientWidth;const yaw=(drag.yaw+(drag.x-e.clientX)/span*Number(adapter.get().fov)+360)%360;change("yaw_zero",Math.round(yaw*10)/10);}});
  on($(".front"),"pointerup",()=>{drag=null;});on($(".front"),"pointercancel",()=>{drag=null;});
  on($(".zero"),"click",()=>{change("yaw_zero",((Number(adapter.get().yaw_zero)%360)+360)%360);status("Front direction confirmed for this panorama.");});
  on($(".overlap"),"change",()=>renderPreviews());
  const files=document.createElement("input");files.type="file";files.multiple=true;files.accept=".jpg,.jpeg,.png,.tif,.tiff,.heic,.heif";files.hidden=true;root.append(files);
  const folder=document.createElement("input");folder.type="file";folder.multiple=true;folder.setAttribute("webkitdirectory","");folder.hidden=true;root.append(folder);
  async function upload(file) {
    const body=new FormData();body.append("file",file);const response=await adapter.fetch("/osmo360/upload",{method:"POST",body});const result=await response.json();if(!response.ok)throw new Error(result.error||"Upload failed.");return result;
  }
  async function importFiles(items) {
    let errors=[];status("Importing panoramas…");
    for(const file of items){if(!/\.(jpe?g|png|tiff?|heic|heif)$/i.test(file.name))continue;try{const source=await upload(file);source.yaw_zero=0;queue.push(source);if(!selected){selected=source.path;adapter.set({panorama:selected});}}catch(error){errors.push(file.name+": "+error.message);}}
    storeQueue();status(errors.length?errors.join("\n"):"Panoramas imported.",!!errors.length);schedule();
  }
  on(files,"change",()=>importFiles(files.files));on(folder,"change",()=>importFiles(folder.files));
  on($(".add"),"click",()=>files.click());on($(".folder"),"click",()=>folder.click());
  on($(".drop"),"dragover",event=>{event.preventDefault();});on($(".drop"),"drop",event=>{event.preventDefault();importFiles(event.dataTransfer.files);});
  async function copy(text){try{await navigator.clipboard.writeText(text);status("Prompt copied.");}catch{const area=$(".prompt");area.focus();area.select();status("Select and copy the highlighted prompt.");}}
  on($(".copy-reference"),"click",()=>copy(prompt));
  function renderPreviews(){
    const grid=$(".grid");grid.replaceChildren();const overlays=$(".overlap").checked;
    const columns=previews.length===4?2:Math.min(6,Math.ceil(Math.sqrt(previews.length)));
    for(const view of previews){const tile=document.createElement("div");tile.className="tile";tile.style.flexBasis="calc("+(100/columns)+"% - 14px)";const frame=document.createElement("div");frame.className="picture";const img=document.createElement("img");img.src=view.image;img.alt="Reference view "+(view.index+1)+", relative yaw "+view.relativeYaw+" degrees";frame.append(img);
      if(overlays)for(const side of ["Left","Right"]){const band=document.createElement("div");band.className="band";band.style.width=(view["band"+side]*100)+"%";band.style[side.toLowerCase()]="0";frame.append(band);}
      const label=document.createElement("small");label.textContent="View "+(view.index+1)+" / "+Math.round(view.relativeYaw)+"° / "+view.horizontalFOV+"° FOV";
      tile.append(frame,label);on(tile,"click",()=>inspect(view));grid.append(tile);
    }
    if(previews[0])$(".front img").src=previews[0].image;
  }
  function inspect(view){const panel=document.createElement("div");panel.className="enlarged";const close=document.createElement("button");close.textContent="Close preview";const img=document.createElement("img");img.src=view.image;img.alt="Enlarged reference view "+(view.index+1);const text=document.createElement("p");text.textContent="Yaw "+view.relativeYaw+"° / FOV "+view.horizontalFOV+"° / pitch "+view.pitch+"°";panel.append(close,img,text);root.append(panel);close.onclick=()=>panel.remove();}
  function schedule(){clearTimeout(timer);timer=setTimeout(preview,100);}
  async function preview(){
    if(!selected){previews=[];renderPreviews();return;}
    const token=++generation;if(pending)pending.abort();pending=new AbortController();
    try{
      const response=await adapter.fetch("/osmo360/preview",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({...adapter.get(),panorama:selected}),signal:pending.signal});
      const data=await response.json();if(token!==generation||disposed)return;if(!response.ok)throw new Error(data.error||"Preview failed.");
      previews=data.previews;prompt=data.prompt;$(".prompt").value=prompt;renderPreviews();
      const c=data.camera,p=PRESETS[c.preset],custom=Math.abs(c.fov-p[2])>.001||Math.abs(c.pitch)>.001;
      $(".summary").textContent="Views "+previews.length+" / H FOV "+c.fov+"° / V FOV "+data.previews[0].verticalFOV.toFixed(1)+"° / pitch "+c.pitch+"° / "+c.projection+" / output "+c.width+" × "+c.height+(custom?" / CUSTOMIZED":"");
      $(".front-label").textContent="Front: "+Number(c.yaw_zero).toFixed(1)+"° / saved continuously; 000° is relative, not north.";
      status(c.fov>110&&c.projection==="Rectilinear"?"Wide rectilinear frames stretch objects near the edges. Natural Wide is available.":"Reference previews updated.");
    }catch(error){if(error.name!=="AbortError")status(error.message,true);}
  }
  on($(".export"),"click",async()=>{try{const response=await adapter.fetch("/osmo360/export",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({...adapter.get(),panorama:selected,queue})});const data=await response.json();if(!response.ok)throw new Error(data.error||"Export failed.");exportJob=data.id;$(".cancel").disabled=false;$(".export").disabled=true;pollExport();}catch(error){status(error.message,true);}});
  on($(".cancel"),"click",async()=>{if(exportJob)await adapter.fetch("/osmo360/jobs/"+exportJob+"/cancel",{method:"POST"});});
  async function pollExport(){
    if(!exportJob||disposed)return;
    try{const response=await adapter.fetch("/osmo360/jobs/"+exportJob);const data=await response.json();if(!response.ok)throw new Error(data.error||"Cannot read export status.");
      $(".progress").textContent=data.status+" / "+data.completed_views+" of "+data.total_views+" views rendered";
      if(["completed","failed","cancelled"].includes(data.status)){exportJob=null;$(".cancel").disabled=true;$(".export").disabled=false;
        if(data.error)status(data.error,true);
        const links=$(".downloads");links.replaceChildren();for(const pack of data.packs){const link=document.createElement("a");link.href=pack.url;link.textContent="Download "+pack.name;link.download="";links.append(link);}
      }else setTimeout(pollExport,700);
    }catch(error){status(error.message,true);exportJob=null;$(".cancel").disabled=true;$(".export").disabled=false;}
  }
  renderQueue();refreshControls();schedule();
  return {dispose(){disposed=true;abort.abort();pending?.abort();clearTimeout(timer);host.replaceChildren();},refresh(){refreshControls();schedule();}};
}
