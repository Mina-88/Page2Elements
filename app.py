from crypt import methods
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
    for i in range(len(image_path)):
        images.append(cv2.imread(image_path[i]))
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
    det_co[pages_pointer] = []
    for i in range(len(coordinates)):
        if(page_detections_pointer == no_page_detections[pages_pointer]):
            pages_pointer += 1
            page_detections_pointer = 0
            det_co[pages_pointer] = []
                    
        # extracting the image
        x_1 = coordinates[i]['x_1']
        x_2 = coordinates[i]['x_2']
        y_1 = coordinates[i]['y_1']
        y_2 = coordinates[i]['y_2']
        
        det_co[pages_pointer].append(coordinates[i])
        curr_crop_img = images[pages_pointer][y_1:y_2, x_1:x_2]
        result_cv.append({"page": pages_pointer, "obj":curr_crop_img, "index":page_detections_pointer})
        temp_meta = copy.deepcopy(meta_data[pages_pointer])
        result_meta.append({"page": pages_pointer, "obj":temp_meta, "index":page_detections_pointer})
        download_name.append({"page": pages_pointer, "obj":page_name[pages_pointer], "index":page_detections_pointer})
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

def save_ndImages():
    count = 0
    for i in range(len(result_cv)):
        os.chdir(download_folder) # changing currrent directory to the download folder[variable]
        if(i != 0 and download_name[i]['obj'] != download_name[i-1]['obj']): # all images from same page are taken
            count = 0
        split_name = download_name[i]['obj'].split('.') # splitting the name and the extension
        result_name = split_name[0] + '_' + str(count) + '.' + split_name[1] # creating duplicate names
        cv2.imwrite(result_name, result_cv[i]['obj']) # saving the image
        count += 1

def getImgCap(image):
    imgCapRes = img_cap(image)
    for i in range(len(imgCapRes)):
        imgCapRes[i] = imgCapRes[i].replace(" <end>", "")
    return imgCapRes
    # 3 captions for each image are created
    # They are in the form of a list

def reset_server():
    os.chdir(UPLOAD_FOLDER)
    for i in page_name:
        if os.path.exists(i):
            os.remove(i)
    os.chdir(download_folder)
    for j in download_name: 
        if os.path.exists(j):
            os.remove(j)

# Flask app configuration
app = Flask(__name__, static_folder="static")
app.secret_key = "super secret key"
ALLOWED_EXTENSIONS = {'jpg', 'png', 'jpeg'}
UPLOAD_FOLDER = "/home/ahmed_fathi/P2E/Page2Elements/static"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
download_folder = "/home/ahmed_fathi/P2E/Page2Elements/download"

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
                page_uri.append(url_for('static', filename=file_name))
                up_count += 1
        if up_count == len(files): # all images are uploaded
            get_page_metadata()
            return redirect(url_for('metadata'))
        if 0 < up_count < len(files):
            return redirect(request.url)
    return render_template('upload.html')

@app.route('/metadata', methods=['POST', 'GET']) # metadata preview
def metadata():
    index_meta = 0 # keep track of current page
    if request.method == 'POST':
        meta_request = request.get_json() # getting request data
        index_meta = int(meta_request[0]['index']) # passed index
        if (int(meta_request[0]['write']) == 1): # parameter to check for modifications
            # modifying current metadata
            meta_data[index_meta]['name'] = meta_request[0]['name'] 
            meta_data[index_meta]['issue_date'] = meta_request[0]['issue_date'] 
            meta_data[index_meta]['issue'] = meta_request[0]['issue'] 
            meta_data[index_meta]['page'] = meta_request[0]['page']
    return render_template('meta_data.html', page_uri=page_uri, rng_img = range(len(page_name)), index_meta = index_meta, meta_data=meta_data)


@app.route('/detections', methods=['GET', 'POST']) # detections preview
def detections():
    global session
    if session == 0: # to avoid redundancy, only at start of session
        create_detections()
        session = 1
    # ocr_page = ocrPage(images)
    ndarray_to_b64(result_cv) # encoding images to be passed to html
    if request.method == 'POST':
        request_data = request.get_json()
        operation = request_data['operation']
        image_index = int(request_data['index'])
        if operation == 'remove_image':
            del det_co[result_en[image_index]['page']][result_en[image_index]['index']]
            del result_en[image_index]
            del result_meta[image_index]
            del result_cv[image_index]
            for i in range(image_index, len(result_en)):
                result_cv[i]["index"] -= 1
                result_en[i]["index"] -= 1
                result_meta[i]["index"] -= 1
        elif operation == 'remove_caption':
            result_meta[image_index]['obj']['caption'] = ""
        elif operation == 'generate_caption':
            result_meta[image_index]['obj']['caption'] = getImgCap(result_cv[image_index]['obj'])
        elif operation == 'manual_caption':
            result_meta[image_index]['obj']['caption'] = request_data['caption']           
    return render_template('detections.html', pass_files=result_en, pass_meta=result_meta, pass_range = range(len(result_en)))


@app.route('/download', methods=['GET', 'POST']) # downloads page
def download():
    if request.method == 'POST':
        if request.form['download'] == 'Images':
            save_ndImages() # save all detections in the downloads directory
            stream = BytesIO()
            with ZipFile(stream, 'w') as zf: # create a compressed file with all images
                for page in page_name:
                    search_name = "%s*.%s" % (page.split('.')[0], page.split('.')[1]) # use wild card tokens to get all images of current session
                    for file in glob(os.path.join(download_folder, search_name)):
                        zf.write(file, os.path.basename(file))
            stream.seek(0)
            return send_file(
                stream, 
                as_attachment=True,
                attachment_filename='lib_bot_download_images.zip'
            ) # sending the file to be downloaded

        elif request.form['download'] == 'JSON':
            for i in range(len(result_cv)):
                tmp_dict = {} # create a dictionary similar to json
                tmp_dict["image"] = result_en[i]['obj']
                tmp_dict["name"] = result_meta[i]['obj']["name"]
                tmp_dict["issue"] = result_meta[i]['obj']["issue"]
                tmp_dict["issue_date"] = result_meta[i]['obj']["issue_date"]
                tmp_dict["page"] = result_meta[i]['obj']["page"]
                json_conv.append(tmp_dict)
            download_json = json.dumps(json_conv) # from dictionary to json
            os.chdir(download_folder)
            json_download_name = "lib_bot_download_json.json" #naming the file
            with open(json_download_name, "w") as outfile:
                outfile.write(download_json) # saving json
            return send_from_directory(download_folder, json_download_name, as_attachment=True) # send file to downloads
        elif request.form['download'] == "Start New":
            return redirect('/')
        else:
            return render_template('download.html')
    return render_template('download.html')

@app.route('/manual_detections', methods=['POST', 'GET']) # manual detections page
def manual():
    index_manual = 0 # track current displayed page
    if request.method == 'POST':
        manual_coor = request.get_json()
        if (int(manual_coor[0]['sel']) == 1): # if the user added selections
            for i in manual_coor:
                #extracting the image
                x_1 = int(float(i['left'][:len(i['left']) - 2])  / i['ratio_w'])
                x_2 = int(float(i['right'][:len(i['right']) - 2])/ i['ratio_w'])
                y_1 = int(float(i['top'][:len(i['top']) - 2]) / i['ratio_h'])
                y_2 = int(float(i['bottom'][:len(i['bottom']) - 2]) / i['ratio_h'])
                index_manual = int(i['index'])
                curr_crop_img = images[index_manual][y_1:y_2, x_1:x_2]
                
                result_cv.append({"page": index_manual, "obj":curr_crop_img, "index":((result_cv[len(result_cv) - 1]['index']) + 1)})
                result_meta.append({"page": index_manual, "obj":meta_data[index_manual], "index":((result_cv[len(result_cv) - 1]['index']) + 1)})
                download_name.append({"page": index_manual, "obj":page_name[index_manual], "index":((result_cv[len(result_cv) - 1]['index']) + 1)})
            return render_template('manual.html', img_src=page_uri, rng_img = range(len(page_name)), det_co = det_co[index_manual], sv_ind = index_manual)
        else: # the user is navigatting pages
            index_manual = int(manual_coor[0]['index']) # get new index
            return render_template('manual.html', img_src=page_uri, rng_img = range(len(page_name)), det_co = det_co[index_manual], sv_ind = index_manual)
    return render_template('manual.html', img_src=page_uri, rng_img = range(len(page_name)), det_co = det_co[index_manual], sv_ind = index_manual)

if __name__ == "__main__":
    app.run(debug=True)
