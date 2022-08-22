// Metadata Page
function next_page_meta(pages)
{
  var input = document.getElementById("pg_ind_meta");
  var index = parseInt(input.value);
  var rng = input.dataset.range;
  index += 1;
  var img = document.getElementById("meta_img");
  if (index > rng - 1) {
    img.src = pages[0];
    document.getElementById("pg_ind_meta").value = 0;
  }
  else {
    img.src = pages[index];
    document.getElementById("pg_ind_meta").value = index;
  }
  send_meta('navigate', );
}

function prev_page_meta(pages)
{
  var input = document.getElementById("pg_ind_meta");
  var index = parseInt(input.value);
  var rng = input.dataset.range;
  index -= 1;
  var img = document.getElementById("meta_img");
  if (index < 0) {
    img.src = pages[rng - 1];
    document.getElementById("pg_ind_meta").value = (rng - 1);
  }
  else {
    img.src = pages[index];
    document.getElementById("pg_ind_meta").value = index;
  }
  send_meta();
}

function send_meta(operation, index_meta) {
  if (operation === 'navigate') {
    var temp_json = {"index": index_meta};
  }
  else if (operation === 'write') {
    data = $('#meta_input').serializeArray().reduce(function(obj, item) { obj[item.name] = item.value; return obj}, {}); // Form data to a key-value form
    var temp_json = {"name":data['p_name'], "issue_date":data['p_iss_date'], "issue":data['p_iss'], "page":data['p_num'], "index":index_meta, "operation":'write'};
  }
  else if (operation === 'ocr') {
    var temp_json = {"index": index_meta, "operation": 'ocr'};
  }
  $.ajax({
    url:"/metadata",
    type:"POST",
    contentType: "application/json",
    data: JSON.stringify(temp_json),
    success:function(response){ document.write(response); document.close();}});
}  

function insert_meta() {
  reset_meta();
  var input = document.getElementById("meta_input");
  input.setAttribute("hidden", "false");
  input.removeAttribute("hidden");
}

function reset_meta() {
  var input = document.getElementById("meta_input");
  input.reset();
  input.setAttribute("hidden", "true");
}

// Detections Page
function remove_image(index) {
  send_det_data('remove_image', index);
  hide_input(index);
}

function remove_caption(index) {
  send_det_data('remove_caption', index);
  hide_input(index);
}

function generate_caption(index) {
  send_det_data('generate_caption', index);
  hide_input(index);
}

function reset_input(index) {
  var input = document.getElementById("cap_in_" + index);
  input.value = "";
}

function view_input(index) {
  var input = document.getElementById("cap_in_div_" + index);
  input.setAttribute("hidden", "false");
  input.removeAttribute("hidden");
  reset_input(index);
}

function hide_input(index) {
  var input = document.getElementById("cap_in_div_" + index);
  input.setAttribute("hidden", "true")
  reset_input(index);
}

function manual_caption(index) {
  send_det_data('manual_caption', index);
}

function ocr_detection(index) {
  send_det_data('ocr', index);
}

function send_det_data(operation, index) {
  var temp_json = {};
  if (operation !== 'manual_caption') {
    temp_json = {"operation": operation, "index": index};
    $.ajax({
      url:"/detections",
      type:"POST",
      contentType: "application/json",
      data: JSON.stringify(temp_json), 
      success:function(response){ document.write(response); document.close();}});
  }
  else {
    var input = document.getElementById("cap_in_" + index).value;
    temp_json = {"operation": operation, "index": index, "caption": input};
    $.ajax({
      url:"/detections",
      type:"POST",
      contentType: "application/json",
      data: JSON.stringify(temp_json), 
      success:function(response){ document.write(response); document.close();}});
  }
}


// Manual Detections Page
function getSelectionRectNode() {
    return document.getElementById("crop-rect");
}

function showSelectionRectangle(selection) {
    var rect = getSelectionRectNode();
    var img = document.getElementById("img_man")
    var reference = document.getElementById("manual_detection_div").getBoundingClientRect()
    var ref_top = parseInt(parseFloat(reference.top));
    var ref_left = parseInt(parseFloat(reference.left));
    rect.style.left = `${selection.left -ref_left}px`;
    rect.style.top = `${selection.top - ref_top}px`;
    rect.style.width = `${(selection.right - selection.left)}px`;
    rect.style.height = `${(selection.bottom - selection.top)}px`;
    rect.style.position = "absolute";
    rect.style.opacity = 0.5;
}

function appendSelectionRectangle(selection) {
    var rect_div = document.createElement("div");
    var reference = document.getElementById("manual_detection_div").getBoundingClientRect()
    var ref_top = parseInt(parseFloat(reference.top));
    var ref_left = parseInt(parseFloat(reference.left));
    rect_div.className = "div_sel"
    rect_div.style.top = `${selection.top + window.scrollY - ref_top}px`;
    rect_div.style.width = `${selection.right - selection.left}px`;
    rect_div.style.height = `${selection.bottom - selection.top}px`;
    rect_div.style.left = `${selection.left + window.scrollX - ref_left}px`;
    rect_div.style.right = `${selection.right + window.scrollX - ref_left}px`;  
    rect_div.style.bottom = `${selection.bottom + window.scrollY - ref_top}px`;  
    rect_div.style.borderStyle = "solid";
    rect_div.style.borderColor = "black";
    rect_div.style.position = "absolute";
    document.querySelector("#manual_detection_div").appendChild(rect_div);
}

function resetSelectionRectangle() {
    var rect = getSelectionRectNode();
    rect.style.left = 0;
    rect.style.top = 0;
    rect.style.width = 0;
    rect.style.height = 0;
    rect.style.opacity = 0;
}

function initEventHandlers() {
    var isMouseDown = false;
    var selectionRectangle = {
      top: 0,
      left: 0,
      right: 0,
      bottom: 0
    };
    
    var save_co = 0;
    function onMouseDown(e) {
      isMouseDown = true;
      selectionRectangle.left = e.clientX;
      selectionRectangle.top = e.clientY;
      save_co_X = e.clientX;
      save_co_Y = e.clientY;        
    }
    function onMouseMove(e) {
      if (!isMouseDown) {
        return;
      }
      if (e.clientX < save_co_X) {
        if (e.clientY < save_co_Y) {
            selectionRectangle.top = e.clientY;
            selectionRectangle.bottom = save_co_Y;
        }
        else {
            selectionRectangle.bottom = e.clientY;
        }
        selectionRectangle.left = e.clientX;
        selectionRectangle.right = save_co_X;
      }
      else {
        if (e.clientY < save_co_Y) {
            selectionRectangle.top = e.clientY;
            selectionRectangle.bottom = save_co_Y;
        }
        else {
            selectionRectangle.bottom = e.clientY;
        }
        selectionRectangle.right = e.clientX;
      }
      showSelectionRectangle(selectionRectangle);
    }
  
    function onMouseUp(e) {
      isMouseDown = false;
      appendSelectionRectangle(selectionRectangle);
      resetSelectionRectangle();
      document.getElementById("manual_detection_div").removeEventListener("mousemove", onMouseMove);
      document.getElementById("manual_detection_div").removeEventListener("mousedown", onMouseDown);
      document.getElementById("manual_detection_div").removeEventListener("mouseup", onMouseUp);
    }
  
    document.getElementById("manual_detection_div").addEventListener("mousedown", onMouseDown);
    document.getElementById("manual_detection_div").addEventListener("mousemove", onMouseMove);
    document.getElementById("manual_detection_div").addEventListener("mouseup", onMouseUp);
}

function init() 
{
    initEventHandlers();
}
  
function next_page_man(pages)
{
  var div_sel = document.querySelectorAll(".div_sel");
  div_sel.forEach(sel => { sel.remove()  });
  var input = document.getElementById("pg_ind");
  var index = parseInt(input.value);
  var rng = input.dataset.range;
  index += 1;
  var img = document.getElementById("img_man");
  if (index > rng - 1) {
    img.src = pages[0];
    document.getElementById("pg_ind").value = 0;
  }
  else {
    img.src = pages[index];
    document.getElementById("pg_ind").value = index;
  }
  send_man_data();
}

function prev_page_man(pages)
{
  var div_sel = document.querySelectorAll(".div_sel");
  div_sel.forEach(sel => { sel.remove()  });
  var input = document.getElementById("pg_ind");
  var index = parseInt(input.value);
  var rng = input.dataset.range;
  index -= 1;
  var img = document.getElementById("img_man");
  if (index < 0) {
    img.src = pages[rng - 1];
    document.getElementById("pg_ind").value = (rng - 1);
  }
  else {
    img.src = pages[index];
    document.getElementById("pg_ind").value = index;
  }
  send_man_data();
}

function reset_man()
{
  var div_sel = document.querySelectorAll(".div_sel");
  div_sel.forEach(sel => { sel.remove()  });
}

function confirm_man() 
{
  send_man_data();
}

function send_man_data() {
  var test = document.querySelectorAll(".div_sel");
  var index_hid = document.getElementById("pg_ind").getAttribute("value");
  if (test.length != 0) {
    var js_sel = [];
    var temp_json = {};
    var img = document.getElementById("img_man")
    var width_ratio = img.clientWidth / img.naturalWidth;
    var height_ratio = img.clientHeight / img.naturalHeight;
    test.forEach(t => { temp_json = {"top":t.style.top, "left":t.style.left, "right":t.style.right, "bottom":t.style.bottom, "index":index_hid, "sel":1, "ratio_w": width_ratio, "ratio_h": height_ratio};
                        js_sel.push(temp_json); })
    $.ajax({
      url:"/manual_detections",
      type:"POST",
      contentType: "application/json",
      data: JSON.stringify(js_sel)});
    } 
  else {
    var js_sel = [];
    var temp_json = {"top":0, "left":0, "right":0, "bottom":0, "index":index_hid, "sel":0};
    js_sel.push(temp_json);
    $.ajax({
      url:"/manual_detections",
      type:"POST",
      contentType: "application/json",
      data: JSON.stringify(js_sel),
      success:function(response){ document.write(response); document.close();}});
  }
  // location.reload();
}   

function rst_det_prev() {
  rst_det = document.querySelectorAll(".det_rect");
  rst_det.forEach(det => {det.remove();});
}

// General Functions
function down_red() {
  window.location.href = "/download";
}

function man_red() {
  window.location.href = "/manual_detections"
}

function det_red() {
  window.location.href = "/detections";
}

