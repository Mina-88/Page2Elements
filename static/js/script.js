function getSelectionRectNode() {
    return document.querySelector(".crop-rect");
}

function showSelectionRectangle(selection) {
    var rect = getSelectionRectNode();
    rect.style.left = `${selection.left + window.scrollX}px`;
    rect.style.top = `${selection.top + window.scrollY}px`;
    rect.style.width = `${selection.right - selection.left}px`;
    rect.style.height = `${selection.bottom - selection.top}px`;
    rect.style.opacity = 0.5;
}

function appendSelectionRectangle(selection) {
    var rect_div = document.createElement("div");
    rect_div.className = "div_sel"
    rect_div.style.top = `${selection.top + window.scrollY}px`;
    rect_div.style.width = `${selection.right - selection.left}px`;
    rect_div.style.height = `${selection.bottom - selection.top}px`;
    rect_div.style.left = `${selection.left + window.scrollX}px`;
    rect_div.style.right = `${selection.right + window.scrollX}px`;  
    rect_div.style.bottom = `${selection.bottom + window.scrollY}px`;  
    rect_div.style.borderStyle = "solid";
    rect_div.style.borderColor = "black";
    rect_div.style.position = "absolute";
    document.querySelector("#form_man").appendChild(rect_div);
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
      console.log(selectionRectangle);
      appendSelectionRectangle(selectionRectangle);
      resetSelectionRectangle();
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    }
  
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
}

function init() 
{
    initEventHandlers();
}
  
function next_page(pages)
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

function prev_page(pages)
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

function reset_btn()
{
  var div_sel = document.querySelectorAll(".div_sel");
  div_sel.forEach(sel => { sel.remove()  });
}

function confirm_btn() 
{
  send_man_data();
}

function down_red() {
  window.location.href = "/download";
}

function det_red() {
  window.location.href = "/detections";
}

function send_man_data() {
  var test = document.querySelectorAll(".div_sel");
  var index_hid = document.getElementById("pg_ind").getAttribute("value");
  if (test.length != 0) {
    var js_sel = [];
    var temp_json = {};
    test.forEach(t => { temp_json = {"top":t.style.top, "left":t.style.left, "right":t.style.right, "bottom":t.style.bottom, "index":index_hid, "sel":1};
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