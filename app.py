from crypt import methods
import imp
from ossaudiodev import control_names
import shutil
from urllib.parse import urljoin, urlparse
from flask import Flask, flash, render_template, request
from flask import redirect, send_from_directory, url_for, send_file
from werkzeug.utils import secure_filename
import layoutparser as lp
import cv2
import os
from glob import glob
from io import BytesIO
from zipfile import ZipFile
import base64
import json
import re
from run import img_cap
import easyocr
import copy
import pandas as pd

# Data Structure
image_path = [] # input
images = []

result_cv = [] # output
result_en = []
result_meta = []

page_name = [] # intermediate variables
page_uri = []
download_name = []
meta_data = []
json_conv = []
det_co = {}
man_co = {}
global manual_coor
session = 0


def clear_lists(): # to reset the session
    image_path.clear()
    images.clear()
    
    result_cv.clear()
    result_en.clear()
    result_meta.clear()
    
    page_name.clear()
    download_name.clear()
    meta_data.clear()
    json_conv.clear()
    page_uri.clear() 

def img_to_cv():
    images.clear()
    for i in range(len(image_path)):
        images.append(cv2.imread(image_path[i]))
        man_co[i] = []

def ocrPage(page): # to ocr a single page
    reader = easyocr.Reader(['ar'])
    result = reader.readtext(page, detail = 0)
    return result

def get_page_metadata():
    for page in page_name:
        curr_dict_meta = {}
        curr_metadata = re.split("[- |_ | |.]", page)
        # we need one that generalizes if it is not the same as the ones that we have
        curr_dict_meta['name'] = curr_metadata[0] + '_' + curr_metadata[1]
        count = 0

        for i in curr_metadata: 
            if(len(i) == 4 and i.isnumeric()):
                curr_dict_meta['issue_date'] = i
            if( (len(i) < 4) and i.isnumeric() and count != len(curr_metadata) - 2):
                curr_dict_meta['issue'] = i
            if("iss" in i):
                curr_dict_meta['issue'] = i[3:]
            if(count == len(curr_metadata) - 2):
                curr_dict_meta['page'] = i
            count += 1
        meta_data.append(curr_dict_meta) 
        
def get_whole_pages_detections(model):
    """
    take the model and the pages as input
    and returns the detections that are made by the model
    on each page (each page has one element in the detections list)
    """
    detections = []
    img_to_cv()
    for i in range(len(images)):
        layout = model.detect(images[i])
        detections.append(layout)
    return detections

def get_detections_coor(detections):
    # coordinates is the coordinates of each image detection in a page
    # page detections is the number of detections for each page
    coordinates = []
    page_detections = []
    for i in range(len(detections)):
        # number is to keep track of the detections in the current page
        number = 0
        for j in range(len(detections[i])):
            # we should be now in the index of a certain text block
            curr_block = detections[i][j].block
            curr_img_coordinates = {}
        
            curr_img_coordinates['x_1'] = int(curr_block.x_1)
            curr_img_coordinates['x_2'] = int(curr_block.x_2)
            curr_img_coordinates['y_1'] = int(curr_block.y_1)
            curr_img_coordinates['y_2'] = int(curr_block.y_2)
        
            coordinates.append(curr_img_coordinates)
            number += 1
        page_detections.append(number)
    return coordinates, page_detections

def get_detections_images(coordinates, no_page_detections):
    # showing the images
    pages_pointer = 0
    page_detections_pointer = 0
    for i in range(len(page_name)):
        det_co[i] = []
    # det_co[pages_pointer] = []
    for i in range(len(coordinates)):
        if(page_detections_pointer == no_page_detections[pages_pointer]):
            pages_pointer += 1
            page_detections_pointer = 0
            # det_co[pages_pointer] = []
                    
        # extracting the image
        x_1 = coordinates[i]['x_1']
        x_2 = coordinates[i]['x_2']
        y_1 = coordinates[i]['y_1']
        y_2 = coordinates[i]['y_2']
        
        det_co[pages_pointer].append(coordinates[i])
        curr_crop_img = images[pages_pointer][y_1:y_2, x_1:x_2]
        result_cv.append({"page": pages_pointer, "obj":curr_crop_img, "index":page_detections_pointer})
        temp_meta = copy.deepcopy(meta_data[pages_pointer])
        temp_meta.pop('ocr', None)
        temp_name = copy.deepcopy(page_name[pages_pointer])
        result_meta.append({"page": pages_pointer, "obj":temp_meta, "index":page_detections_pointer})
        download_name.append({"page": pages_pointer, "obj":temp_name, "index":page_detections_pointer})
        page_detections_pointer += 1

def create_detections():  
    model = lp.Detectron2LayoutModel("lp://NewspaperNavigator/faster_rcnn_R_50_FPN_3x/config",
                                label_map={0: "Photograph", 1: "Illustration", 2: "Map",
                                            3: "Comics/Cartoon", 4: "Editorial Cartoon", 5: "Headline",
                                            6: "Advertisement"}) 
    detections = get_whole_pages_detections(model)
    coordinates, page_detections = get_detections_coor(detections)
    get_detections_images(coordinates, page_detections)
    # now we have the results in result_cv

def ndarray_to_b64(ndarray):
    result_en.clear() # eleminate redundancy
    for i in ndarray:
        _, buffer = cv2.imencode('.png', i['obj']) # encoding ndarray
        im_en = base64.b64encode(buffer).decode('utf-8') # encoding to b64 to be displayed in html
        result_en.append({"page": i['page'], "obj":im_en, "index":i['index']}) # objects to be passed to html using jinja2

def generate_download_name():
    for i in range(len(result_cv)):
        split_name = download_name[i]['obj'].split('.') # splitting the name and the extension
        download_name[i]['obj'] = split_name[0] + '_' + str(download_name[i]['index']) + '.' + split_name[1] # creating duplicate names

def save_ndImages():
    generate_download_name()
    os.chdir(download_folder) # changing currrent directory to the download folder[variable]
    for i in range(len(download_name)):
        cv2.imwrite(download_name[i]['obj'], result_cv[i]['obj']) # saving the image

def getImgCap(image):
    imgCapRes = img_cap(image)
    for i in range(len(imgCapRes)):
        imgCapRes[i] = imgCapRes[i].replace(" <end>", "")
    return imgCapRes
    # 3 captions for each image are created
    # They are in the form of a list

def reset_server():
    if os.path.exists(UPLOAD_FOLDER):
        shutil.rmtree(UPLOAD_FOLDER)
    if os.path.exists(download_folder):
        shutil.rmtree(download_folder)
    os.makedirs(UPLOAD_FOLDER)
    os.makedirs(download_folder)
    
def download_images():
    save_ndImages()
    csv_exp = []
    for i in range(len(result_cv)):
        tmp_csv = {"image_name": download_name[i]['obj']}
        tmp_csv = {**tmp_csv, **result_meta[i]['obj']}
        csv_exp.append(tmp_csv)
    data_frame = pd.DataFrame.from_dict(csv_exp)
    data_frame.to_csv(r'page_2_elements_csv.csv', index=False, header=True)
    stream = BytesIO()
    with ZipFile(stream, 'w') as zf: # create a compressed file with all images
        for page in page_name:
            search_name = "%s*.%s" % (page.split('.')[0], page.split('.')[1]) # use wild card tokens to get all images of current session
            for file in glob(os.path.join(download_folder, search_name)):
                zf.write(file, os.path.basename(file))
            zf.write('page_2_elements_csv.csv', os.path.basename('page_2_elements_csv.csv'))
    stream.seek(0)
    return send_file(
        stream, 
        as_attachment=True,
        attachment_filename='P2E_images_csv.zip'
    ) # sending the file to be downloaded

def download_json():
    for i in range(len(result_cv)):
        tmp_dict = {} # create a dictionary similar to json
        tmp_dict["image"] = result_en[i]['obj']
        tmp_dict["name"] = result_meta[i]['obj']["name"]
        tmp_dict["issue"] = result_meta[i]['obj']["issue"]
        tmp_dict["issue_date"] = result_meta[i]['obj']["issue_date"]
        tmp_dict["page"] = result_meta[i]['obj']["page"]
        if "caption" in result_meta[i]['obj']:
            tmp_dict["caption"] = result_meta[i]['obj']["caption"]                    
        json_conv.append(tmp_dict)
    download_json = json.dumps(json_conv) # from dictionary to json
    os.chdir(download_folder)
    json_download_name = "P2E_json.json" #naming the file
    with open(json_download_name, "w") as outfile:
        outfile.write(download_json) # saving json
    return send_from_directory(download_folder, json_download_name, as_attachment=True) # send file to downloads

def remove_image(image_index):
    del det_co[result_en[image_index]['page']][result_en[image_index]['index']]
    del result_en[image_index]
    del result_meta[image_index]
    del result_cv[image_index]
    for i in range(image_index, len(result_en)):
        result_cv[i]["index"] -= 1
        result_en[i]["index"] -= 1
        result_meta[i]["index"] -= 1

# Flask app configuration
app = Flask(__name__, static_folder="server/static", template_folder="server")
app.secret_key = "super secret key"
ALLOWED_EXTENSIONS = {'jpg', 'png', 'jpeg'}
UPLOAD_FOLDER = os.path.join(os.getcwd(), "server", "static", "uploads")
download_folder = os.path.join(os.getcwd(), "server", "static", "downloads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename): # to avoid unallowed extensions
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST']) # home page, upload
def upload_image():
    global session
    session = 0 # resetting the session
    reset_server()
    if request.method == 'POST':
        if 'file' not in request.files: # no files are uploaded in the request
            flash('No file part')
            return redirect(request.url)
        files = request.files.getlist("file")
        up_count = 0 # to ensure all files are loaded
        clear_lists()
        for f in files:
            if f.filename == '': 
                flash('No selected file')
                return redirect(request.url)
            if allowed_file(f.filename):
                file_name = secure_filename(f.filename)
                cv_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name) # path to save images
                f.save(cv_path)
                image_path.append(cv_path)
                page_name.append(file_name)
                page_uri.append(url_for('static', filename=('uploads/' + file_name)))
                up_count += 1
        if up_count == len(files): # all images are uploaded
            get_page_metadata()
            return redirect(url_for('metadata'))
        if 0 < up_count < len(files):
            # add a warning that there is an issue with the files
            # some of the files chosen might not be of the supported fromat
            # jpeg, png, etc
            return redirect(request.url)

    return render_template('upload.html')

@app.route('/metadata', methods=['POST', 'GET']) # metadata preview
def metadata():
    img_to_cv()
    index_meta = 0 # keep track of current page

    if request.method == 'POST':
        meta_request = request.get_json() # getting request data
        index_meta = int(meta_request['index']) # passed index
        if (meta_request['operation'] == 'write'): # parameter to check for modifications
            # modifying current metadata
            meta_data[index_meta]['name'] = meta_request['name'] 
            meta_data[index_meta]['issue_date'] = meta_request['issue_date'] 
            meta_data[index_meta]['issue'] = meta_request['issue'] 
            meta_data[index_meta]['page'] = meta_request['page']
        elif (meta_request['operation'] == 'ocr'):
            meta_data[index_meta]['ocr'] = ocrPage(images[index_meta])


    return render_template('meta_data.html', page_uri=page_uri, rng_img = range(len(page_name)), index_meta = index_meta, meta_data=meta_data, length = len(page_name))


@app.route('/detections', methods=['GET', 'POST']) # detections preview
def detections():
    global session
    #if session == 0: # to avoid redundancy, only at start of session
    create_detections()
        #session = 1 #indicate session is already running
    ndarray_to_b64(result_cv) # encoding images to be passed to html
    if request.method == 'POST':
        request_data = request.get_json()
        operation = request_data['operation']
        image_index = int(request_data['index'])
        if operation == 'remove_image':
            remove_image(image_index)
        elif operation == 'remove_caption':
            result_meta[image_index]['obj']['caption'] = ""
        elif operation == 'generate_caption':
            result_meta[image_index]['obj']['caption'] = getImgCap(result_cv[image_index]['obj'])
        elif operation == 'manual_caption':
            result_meta[image_index]['obj']['caption'] = request_data['caption']     
        elif operation == 'ocr':
            result_meta[image_index]['obj']['ocr'] = ocrPage(result_cv[image_index]['obj'])

    return render_template('detections.html', pass_files=result_en, pass_meta=result_meta, pass_range = range(len(result_en)))


@app.route('/download', methods=['GET', 'POST']) # downloads page
def download():
    if request.method == 'POST':
        if request.form['download'] == 'Images & CSV':
            return download_images()
        elif request.form['download'] == 'JSON':
            return download_json()            
        elif request.form['download'] == "Go to Uploads":
            return redirect('/')
    return render_template('download.html')

@app.route('/manual_detections', methods=['POST', 'GET']) # manual detections page
def manual():
    index_manual = 0 # track current displayed page
    if request.method == 'POST':
        manual_req = request.get_json()
        index_manual = int(manual_req[0]['index']) # get new index
        if (manual_req[0]['empty'] == '0'):
            curr_index = int(manual_req[0]['curr_index'])
            # Capturing Coordinates
            for i in range(len(manual_req)):
                del manual_req[i]['empty']
                manual_req[i]['x_1'] = int(float(manual_req[i]['x_1'][:len(manual_req[i]['x_1']) - 2])  / manual_req[i]['ratio_w'])
                manual_req[i]['x_2'] = int(float(manual_req[i]['x_2'][:len(manual_req[i]['x_2']) - 2])/ manual_req[i]['ratio_w'])
                manual_req[i]['y_1'] = int(float(manual_req[i]['y_1'][:len(manual_req[i]['y_1']) - 2]) / manual_req[i]['ratio_h'])
                manual_req[i]['y_2'] = int(float(manual_req[i]['y_2'][:len(manual_req[i]['y_2']) - 2]) / manual_req[i]['ratio_h'])
                manual_req[i]['crop'] = 0
                man_co[curr_index].append(manual_req[i])
            # Cropping the image
            for i in range(len(man_co[curr_index])):
                if man_co[curr_index][i]['crop'] == 0:
                    man_co[curr_index][i]['crop'] = 1
                    curr_crop_img = images[curr_index][man_co[curr_index][i]['y_1']:man_co[curr_index][i]['y_2'], man_co[curr_index][i]['x_1']:man_co[curr_index][i]['x_2']]
                    result_cv.append({"page": curr_index, "obj":curr_crop_img, "index":((result_cv[len(result_cv) - 1]['index']) + 1)})
                    temp_meta = copy.deepcopy(meta_data[curr_index])
                    temp_meta.pop('ocr', None)
                    temp_name = copy.deepcopy(page_name[curr_index])
                    result_meta.append({"page": curr_index, "obj":temp_meta, "index":((result_cv[len(result_cv) - 1]['index']) + 1)})
                    download_name.append({"page": curr_index, "obj":temp_name, "index":((result_cv[len(result_cv) - 1]['index']) + 1)})
    return render_template('manual.html', img_src=page_uri, rng_img = range(len(page_name)), det_co = det_co[index_manual], sv_ind = index_manual, man_co = man_co[index_manual], length = len(page_name))


if __name__ == "__main__":
    app.run(debug=True)
